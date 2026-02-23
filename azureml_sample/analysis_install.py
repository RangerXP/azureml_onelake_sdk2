"""Installation helper for the `azureml_sample` package.

Creates a local virtual environment (`.venv`), installs `requirements.txt`,
and optionally runs a SMOKE_TEST to validate the local CSV sample.
"""
import os
import sys
import subprocess
from pathlib import Path


def create_venv(venv_path: Path):
    if venv_path.exists():
        print(f"Virtualenv already exists at {venv_path}")
        return
    print(f"Creating virtualenv at {venv_path}...")
    subprocess.check_call([sys.executable, "-m", "venv", str(venv_path)])


def install_requirements(python_exe: str, req_file: Path):
    print(f"Installing requirements from {req_file} using {python_exe}...")
    subprocess.check_call([python_exe, "-m", "pip", "install", "-r", str(req_file)])


def smoke_test(python_exe: str):
    print("Running SMOKE_TEST to validate local CSV read...")
    env = os.environ.copy()
    env["SMOKE_TEST"] = "1"
    subprocess.check_call([python_exe, str(Path(__file__).parent / "run_analysis.py")], env=env)


def main():
    root = Path(__file__).parent
    venv_dir = root / ".venv"
    req = root / "requirements.txt"

    # create venv if missing
    create_venv(venv_dir)

    python_exe = str(venv_dir / "Scripts" / "python.exe")
    if not Path(python_exe).exists():
        raise SystemExit(f"Python not found in venv at {python_exe}")

    install_requirements(python_exe, req)

    # run smoke test
    smoke_test(python_exe)


if __name__ == '__main__':
    main()
