"""Clean repo-root installer for azureml_DataLakeServiceClient.

Creates the target project folder (if missing), a `.venv` inside it, and
installs packages from `requirements.txt` one-by-one while printing status.
"""
import os
import sys
import subprocess
import venv
import argparse
import shutil
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
# Install target should be created off the workspace root (parent of this script)
# so the created `azureml_DataLakeServiceClient` folder is sibling to the repo root
WORKSPACE_ROOT = HERE.parent
PROJECT_DIR = WORKSPACE_ROOT / "azureml_DataLakeServiceClient"
VENV_DIR = PROJECT_DIR / ".venv"
VSCODE_DIR = PROJECT_DIR / ".vscode"

# Packages required to run analysis scripts in this repo
SUPPORTED_ANALYSIS_PACKAGES = [
    "pandas",
    "pyarrow",
    "azure-identity",
    "azure-storage-file-datalake",
]


def create_target_dirs():
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    VSCODE_DIR.mkdir(parents=True, exist_ok=True)


def copy_files_from_src(src_dir: Path):
    # copy core files from src_dir into PROJECT_DIR when running from a different folder
    if src_dir.resolve() == PROJECT_DIR.resolve():
        return
    items = [
        "README.md",
        "requirements.txt",
        ".env.sample",
        "pyproject.toml",
        "setup.cfg",
        "LICENSE",
        ".gitignore",
        "azureml_datalake_service_client",
    ]
    for it in items:
        s = src_dir / it
        d = PROJECT_DIR / it
        if s.exists():
            if s.is_dir():
                if d.exists():
                    shutil.rmtree(d)
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)


def create_venv():
    python_exe = VENV_DIR / ("Scripts\python.exe" if os.name == "nt" else "bin/python")
    if VENV_DIR.exists():
        if python_exe.exists():
            print(f"Virtualenv already exists at {VENV_DIR}")
            return
        # venv dir exists but python not present: recreate venv to ensure interpreter is installed
        print(f"Virtualenv directory exists but interpreter missing; recreating {VENV_DIR}...")
        try:
            shutil.rmtree(VENV_DIR)
        except Exception:
            pass
    print(f"Creating virtual environment at {VENV_DIR}...")
    venv.create(VENV_DIR, with_pip=True)
    # verify interpreter created
    if not python_exe.exists():
        # Last-resort: copy current interpreter into venv scripts (best-effort on Windows)
        try:
            dst = python_exe
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(sys.executable), dst)
            print(f"Copied python executable to {dst}")
        except Exception:
            print("Warning: failed to create or copy python into venv; venv may be invalid")
    print("Created virtual environment")


def venv_python():
    if os.name == "nt":
        return str(VENV_DIR / "Scripts" / "python.exe")
    return str(VENV_DIR / "bin" / "python")


def install_requirements_one_by_one():
    req = PROJECT_DIR / "requirements.txt"
    if not req.exists():
        print("No requirements.txt found; skipping install")
        return
    py = venv_python()
    print("Upgrading pip in venv...")
    subprocess.check_call([py, "-m", "pip", "install", "-U", "pip"])

    pkgs = []
    with req.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pkgs.append(line)

    # Ensure analysis/runtime packages are present
    for sp in SUPPORTED_ANALYSIS_PACKAGES:
        if sp not in pkgs:
            pkgs.append(sp)
            print(f"Added required package to install: {sp}")

    print(f"Installing {len(pkgs)} packages into .venv (one-by-one)...")
    for pkg in pkgs:
        print(f"Installing: {pkg} ...", end=" ")
        try:
            subprocess.check_call([py, "-m", "pip", "install", pkg])
            print("OK")
        except subprocess.CalledProcessError as e:
            print("FAILED")
            print(f"  pip failed for {pkg}: {e}")


def write_vscode_settings():
    settings = {
        "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
        "python.terminal.activateEnvironment": True
    }
    (VSCODE_DIR / "settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print(f"Wrote VS Code settings -> {VSCODE_DIR / 'settings.json'}")


def write_workspace_file():
    # Remove any old workspace files that point to nested copies (e.g. *_sdk2.code-workspace)
    for p in HERE.glob("*.code-workspace"):
        # keep azureml_onelake_sdk.code-workspace if present (we will overwrite)
        try:
            p.unlink()
        except Exception:
            pass

    workspace_path = HERE / "azureml_onelake_sdk.code-workspace"
    rel = os.path.relpath(PROJECT_DIR, start=HERE).replace("\\", "/")
    data = {
        "folders": [
            {"path": rel}
        ],
        "settings": {
            "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe"
        }
    }
    workspace_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote workspace file -> {workspace_path}")


def main(args):
    src = Path(__file__).resolve().parent
    create_target_dirs()
    copy_files_from_src(src)
    create_venv()
    install_requirements_one_by_one()
    write_vscode_settings()
    write_workspace_file()
    print("Installer finished. Open the workspace file to start.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="Non-interactive")
    parser.add_argument("--target", help="Target folder (ignored when running from repo root)", default=None)
    args = parser.parse_args()
    main(args)
import os
import sys
import shutil
import subprocess
import venv
from pathlib import Path

try:
    from importlib import metadata as importlib_metadata
except Exception:
    import importlib_metadata


TARGET_DIR = Path(__file__).resolve().parent.parent / "azureml_DataLakeServiceClient"
VENV_DIR = TARGET_DIR / ".venv"
VSCODE_DIR = TARGET_DIR / ".vscode"


def create_target_dirs():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    VSCODE_DIR.mkdir(parents=True, exist_ok=True)


def copy_files_from_src(src_dir: Path):
    # If this installer is already running from the target folder, skip copying
    if src_dir.resolve() == TARGET_DIR.resolve():
        print("Installer running in target folder; skipping file copy.")
        return

    files_to_copy = [
        "README.md",
        "requirements.txt",
        ".env.sample",
        "pyproject.toml",
        "setup.cfg",
        "LICENSE",
        ".gitignore",
        "azureml_DataLakeServiceClient.code-workspace",
        "open_workspace.ps1",
        "open_workspace.sh",
    ]
    package_dir = src_dir / "azureml_datalake_service_client"
    for fname in files_to_copy:
        src = src_dir / fname
        if src.exists():
            shutil.copy2(src, TARGET_DIR / fname)
            print(f"Copied {src} -> {TARGET_DIR / fname}")
        else:
            print(f"Warning: {src} not found; skipping")

    # copy package directory
    dst_pkg = TARGET_DIR / "azureml_datalake_service_client"
    if dst_pkg.exists():
        shutil.rmtree(dst_pkg)
    shutil.copytree(package_dir, dst_pkg)
    print(f"Copied package dir -> {dst_pkg}")


def create_venv():
    python_exe = VENV_DIR / ("Scripts\python.exe" if os.name == "nt" else "bin/python")
    if VENV_DIR.exists():
        if python_exe.exists():
            print(f"Virtualenv already exists at {VENV_DIR}")
            return
        print(f"Virtualenv directory exists but interpreter missing; recreating {VENV_DIR}...")
        try:
            shutil.rmtree(VENV_DIR)
        except Exception:
            pass
    print("Creating virtual environment...")
    venv.create(VENV_DIR, with_pip=True)
    if not python_exe.exists():
        try:
            dst = python_exe
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(sys.executable), dst)
            print(f"Copied python executable to {dst}")
        except Exception:
            print("Warning: failed to create or copy python into venv; venv may be invalid")
    print(f"Created venv at {VENV_DIR}")


def venv_python():
    if os.name == "nt":
        return str(VENV_DIR / "Scripts" / "python.exe")
    return str(VENV_DIR / "bin" / "python")


def install_requirements():
    req = TARGET_DIR / "requirements.txt"
    if not req.exists():
        print("No requirements.txt found; skipping install")
        return
    py = venv_python()
    print("Upgrading pip in venv...")
    subprocess.check_call([py, "-m", "pip", "install", "-U", "pip"])

    # Install packages one-by-one and show status
    pkgs = []
    with req.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pkgs.append(line)

    # Ensure analysis/runtime packages are present
    for sp in SUPPORTED_ANALYSIS_PACKAGES:
        if sp not in pkgs:
            pkgs.append(sp)
            print(f"Added required package to install: {sp}")

    if not pkgs:
        print("No packages listed in requirements.txt; nothing to install")
        return

    print(f"Installing {len(pkgs)} packages into .venv (one-by-one)...")
    for pkg in pkgs:
        print(f"\nInstalling: {pkg} ...", end=" ")
        try:
            # run pip install with streaming output
            proc = subprocess.run([py, "-m", "pip", "install", pkg], check=True)
            print("OK")
        except subprocess.CalledProcessError as e:
            print("FAILED")
            print(f"  pip failed for {pkg}: {e}")
            # continue with next package rather than aborting
    print("Finished package installation (check output for any failures).")


def write_vscode_settings():
    settings_path = VSCODE_DIR / "settings.json"
    settings = {
        "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
        "python.terminal.activateEnvironment": True
    }
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print(f"Wrote VS Code settings -> {settings_path}")


def main():
    src_dir = Path(__file__).resolve().parent
    print(f"Deploying workspace to: {TARGET_DIR}")
    create_target_dirs()
    copy_files_from_src(src_dir)
    create_venv()
    try:
        install_requirements()
    except subprocess.CalledProcessError as e:
        print("ERROR: pip install failed:", e)
        sys.exit(2)
    write_vscode_settings()
    print("Deployment complete. Open the workspace:")
    print(f"code {TARGET_DIR / 'azureml_DataLakeServiceClient.code-workspace'}")


if __name__ == "__main__":
    main()
