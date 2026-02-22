param(
  [string]$Src = "$PSScriptRoot\azureml_sample_project",
  [string]$OutZip = "$PSScriptRoot\azureml_sample_project_sanitized.zip"
)

# If the expected source folder doesn't exist at the script root, try the nested
# path used in this workspace: ./azureml/azureml_sample_project
if (-not (Test-Path $Src)) {
  $alt = Join-Path $PSScriptRoot 'azureml\azureml_sample_project'
  if (Test-Path $alt) {
    Write-Host "Using alternate source path: $alt"
    $Src = $alt
  }
}

# 1) prepare temp folder (user-based for portability)
# Use username + timestamp so path is user-identifiable and portable across machines
$timestamp = (Get-Date -Format yyyyMMddHHmmss)
$user = $env:USERNAME
$TempDir = Join-Path $env:TEMP ("aml_package_{0}_{1}" -f $user, $timestamp)
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $TempDir
New-Item -ItemType Directory -Path $TempDir | Out-Null

# 2) files / patterns to exclude (venv, .git, sample data)
$excludePatterns = @('\.venv','\\venv\\','\\.git\\','sample_nyc.csv','synthetic_multi_year.csv')

# 3) copy files (preserve directory structure) excluding patterns
Get-ChildItem -Path $Src -Recurse -File | ForEach-Object {
  $full = $_.FullName
  $skip = $false
  foreach ($pat in $excludePatterns) { if ($full -match $pat) { $skip = $true; break } }
  if (-not $skip) {
    $rel = $full.Substring($Src.Length).TrimStart('\')
    $dst = Join-Path $TempDir $rel
    New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
    Copy-Item -Path $full -Destination $dst -Force
  }
}

# copy repo root README.md into the temp folder so it is included in the sanitized package
$rootReadme = Join-Path $PSScriptRoot 'README.md'
if (Test-Path $rootReadme) {
  Copy-Item -Path $rootReadme -Destination (Join-Path $TempDir 'README.md') -Force
}

# 4) replacements map: regex -> placeholder replacement
$replacements = @{
  'subscription_id\s*=\s*".*?"' = 'subscription_id="{{AZ_SUBSCRIPTION_ID}}"'
  'resource_group_name\s*=\s*".*?"' = 'resource_group_name="{{AZ_RESOURCE_GROUP}}"'
  'workspace_name\s*=\s*".*?"' = 'workspace_name="{{AZ_WORKSPACE_NAME}}"'
  'one_lake_workspace_name\s*=\s*".*?"' = 'one_lake_workspace_name="{{ONE_LAKE_WORKSPACE}}"'
  'artifact_name\s*=\s*".*?"' = 'artifact_name="{{ARTIFACT_NAME}}"'
}

# 5) apply replacements to text files in temp folder
Get-ChildItem -Path $TempDir -Recurse -File | Where-Object { $_.Extension -in '.py','.md','.txt','.yml' } | ForEach-Object {
  $text = Get-Content -Raw -Path $_.FullName
  foreach ($pattern in $replacements.Keys) {
    $text = [regex]::Replace($text, $pattern, $replacements[$pattern])
  }
  Set-Content -Path $_.FullName -Value $text
}

# 6) create .env.example in temp root
$envExample = @"
# Fill these values before running
AZ_SUBSCRIPTION_ID=
AZ_RESOURCE_GROUP=
AZ_WORKSPACE_NAME=
ONE_LAKE_WORKSPACE=
ARTIFACT_NAME=
DATA_FILE_PATH=
"@
Set-Content -Path (Join-Path $TempDir '.env.example') -Value $envExample

# Add a short extraction/instructions file into the temp folder so recipients know how to extract
$instrPath = Join-Path -Path $TempDir -ChildPath "EXTRACTION_INSTRUCTIONS.txt"
$instrContent = @(
  "Extraction & VS Code instructions",
  "",
  "1) Extract the zip contents to your system TEMP folder. Example (PowerShell):",
  "   Expand-Archive -Path azureml_sample_project_sanitized.zip -DestinationPath $env:TEMP\\aml_package_<yourname>_TIMESTAMP",
  "",
  "2) Open the extracted folder in VS Code:",
  "   code $env:TEMP\\aml_package_<yourname>_TIMESTAMP\\azureml_sample_project",
  "",
  "3) Create a virtual environment, install requirements and run the sample scripts (from repo root):",
  "   python -m venv .venv",
  "   .\\.venv\\Scripts\\pip install -r azureml_sample_project\\requirements.txt",
  "   .\\.venv\\Scripts\\python azureml_sample_project\\run_analysis.py",
  "",
  "Notes:",
  "- Replace <yourname> and TIMESTAMP above with any folder name you prefer.",
  "- The scripts optionally use OneLake and will prompt for interactive login if required.",
  ""
)
Set-Content -Path $instrPath -Value $instrContent -Encoding UTF8

# 7) create zip (include everything in temp folder)
if (Test-Path $OutZip) { Remove-Item $OutZip -Force }
Compress-Archive -Path (Join-Path $TempDir '*') -DestinationPath $OutZip -Force

Write-Host "Created sanitized package: $OutZip"
# Show both the resolved path and a portable %TEMP% reference for other users
$portableTemp = "%TEMP%\aml_package_$user`_$timestamp"
Write-Host "Temporary working folder (resolved): $TempDir"
Write-Host "Temporary working folder (portable reference): $portableTemp"