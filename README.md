# AzureML Sample Package (sanitized)

This repository contains a sanitized sample AzureML project demonstrating basic OneLake integration, local testing, a minimal training script, and a forecast example.

Quick steps to open in VS Code and run the examples

1. Extract the sanitized package to your system TEMP folder (example PowerShell):

   Expand-Archive -Path azureml_sample_project_sanitized.zip -DestinationPath $env:TEMP\aml_package_<yourname>_TIMESTAMP

2. Open the sample in VS Code:

   code $env:TEMP\aml_package_<yourname>_TIMESTAMP\azureml_sample_project

3. Create a Python virtual environment and install dependencies (run from repo root):

   python -m venv .venv
   .\.venv\Scripts\pip install -r azureml_sample_project\requirements.txt

4. Run the example analysis (local test mode):

   .\.venv\Scripts\python azureml_sample_project\run_analysis.py

Notes
- The package is sanitized and contains placeholders for Azure subscription/workspace IDs.
- Some scripts can optionally read from OneLake and will prompt for interactive login when required.
- See `EXTRACTION_INSTRUCTIONS.txt` in the extracted folder for the same commands.

If you want a different location for extraction or a more detailed walkthrough, tell me and I will add it.

