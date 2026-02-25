# azureml_DataLakeServiceClient

This repository packages a small utility to load the first artifact file from OneLake into pandas and display it.

Quickstart

1. Open this folder `azureml_DataLakeServiceClient` in VS Code (use the provided workspace file).
2. Run the installer script to create a virtual environment and install dependencies:

```powershell
python sample_installer.py
```

3. Copy `.env.sample` to `.env` and fill in the required values (at minimum `ONE_LAKE_WORKSPACE`).
4. Open the workspace in VS Code using `open_workspace.ps1` or `azureml_DataLakeServiceClient.code-workspace`.
5. Run:

```powershell
.\.venv\Scripts\activate
python -m azureml_datalake_service_client.run_analysis
```

Notes
- Do not commit `.env` with secrets. Keep `.env.sample` for documentation only.
- To produce a proper pip-installable package, `pip install -e .` is supported from this folder.
