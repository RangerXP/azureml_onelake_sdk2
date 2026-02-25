azureml_onelake_sdk — Quick Reference
=====================================

Purpose
-------
Small utility and example that authenticates to Azure, reads a file from OneLake (Data Lake), and returns a pandas.DataFrame for analysis. The script prefers Parquet (pyarrow) and falls back to CSV.

Quick start (3 commands)
------------------------
1. Bootstrap (creates `.venv` and installs deps):

```powershell
python .\sample_installer.py
```

2. Activate the venv:

```powershell
.\.venv\Scripts\Activate.ps1
```

3. Configure environment and run:

```powershell
copy ".env - sample" .env
# edit .env -> set ONE_LAKE_WORKSPACE and (optionally) ONE_LAKE_FILE_PATH or ARTIFACT_ID
python .\run_analysis.py
```

What `run_analysis.py` does (service-layer summary)
--------------------------------------------------
- Auth: tries environment creds, Azure CLI (if present), interactive browser login, then DefaultAzureCredential (short timeout). Designed for quick local interactive use and CI (env creds).
- Data access: uses `azure.storage.filedatalake.DataLakeServiceClient` to list/download files from `ONE_LAKE_WORKSPACE` (or download exact `ONE_LAKE_FILE_PATH`).
- Formats: attempts Parquet via `pyarrow` (preferred), falls back to CSV via `pandas.read_csv`.
- Output: a `pandas.DataFrame` (script prints `df.head(10)`); large files are downloaded to a temp file then read.

Core requirement: OneLake datapipeline for sample data (NYC_TAXI)
----------------------------------------------------------------
This repository assumes your OneLake workspace contains sample data (Parquet/Delta) to test the flow. Unless you replace with your own OneLake delta/parquet table, provide a pipeline that stages the NYC_TAXI dataset into OneLake.

Recommended pipeline options (pick one):
- Azure Data Factory / Synapse Copy Activity: copy source CSV -> write Parquet/Delta to OneLake path.
- Databricks job (PySpark): read CSV, write Parquet/Delta to OneLake (requires `pyspark`, `delta`, optionally `pyarrow` for local testing).

Path and naming convention (recommended)
- Workspace: `<ONE_LAKE_WORKSPACE>`
- Example dataset target path: `NYC_TAXI/puYear=2008/puMonth=12/*.parquet` or a Delta table under `/delta/NYC_TAXI/…`

Why this is required
- The analyzer expects Parquet/Delta artifacts in OneLake; using Parquet preserves schema and allows `pyarrow` to efficiently produce a `pandas.DataFrame`. If you do not stage sample data, set `ONE_LAKE_FILE_PATH` to a path you control or use your own dataset.

Dependencies
------------
- runtime (installed by `sample_installer.py`):
  - python 3.8+
  - pandas
  - pyarrow
  - azure-identity
  - azure-storage-file-datalake

- pipeline-side (choose based on pipeline):
  - Azure Data Factory / Synapse: no extra packages on the service; configure source and sink connectors.
  - Databricks (if used to stage data): `pyspark`, `delta-spark` (or the platform-managed runtime), optional `pyarrow` for local tests.

Environment variables (important)
- `ONE_LAKE_WORKSPACE` (required)
- `ONE_LAKE_ENDPOINT` (optional, defaults to https://onelake.dfs.fabric.microsoft.com)
- `ONE_LAKE_FILE_PATH` (optional exact file), `ARTIFACT_ID`, `RELATIVE_PATH` (optional listing prefix)
- For non-interactive CI: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`

Security note
-------------
- Do NOT commit `.env` with secrets. Use `.env - sample` for documentation and add `.env` to `.gitignore`.

Troubleshooting
---------------
- If VS Code auto-activates a different venv, run `deactivate` and then activate `.venv`.
- If `az` is missing or slow, install Azure CLI (`winget install --id Microsoft.AzureCLI`) or rely on env creds/interactive login.

Files of interest
-----------------
- `sample_installer.py` — creates `.venv`, installs deps, writes VS Code settings.
- `run_analysis.py` — main auth + OneLake read logic; returns `pandas.DataFrame`.
- `requirements.txt` — runtime dependencies.

If you want, I can add: (a) a short ADF/Databricks pipeline example to stage NYC_TAXI into OneLake, or (b) a small CI workflow to run `python -m py_compile` and a lightweight smoke test. Tell me which.
