# AzureML OneLake sample (minimal)

This small sample shows how to register a OneLake datastore in AzureML and perform
a minimal analysis on the `Files/nyc_taxi` data.

Note: The NYC_TAXI data set is a built‑in Microsoft Fabric sample data source that is materialized on demand by the Fabric Data Factory Copy data assistant.

Files:
- `run_analysis.py` -- main script
- `requirements.txt` -- Python dependencies

Run against OneLake (interactive auth):

1. (Optional) set environment variables to override defaults:
   - `AZ_SUBSCRIPTION_ID`, `AZ_RESOURCE_GROUP`, `AZ_WORKSPACE_NAME`
   - `ONE_LAKE_WORKSPACE` -- the OneLake workspace GUID
   - `ARTIFACT_NAME` -- lakehouse id + `/Files` (defaults included in script)

2. Install requirements in your venv:
```powershell
python -m pip install -r azureml_sample_project/requirements.txt
```

3. Run the script:
```powershell
python run_analysis.py
```

If the OneLake listing/download fails, copy the error and I can help adjust the URL/auth scope.

**AzureML & OneLake Integration**

This project performs two kinds of Azure-related actions:

- **Azure ML service calls (AML API):**
   - `MLClient(...)` -- creates the Azure ML client used to operate on the workspace. See `run_analysis.py` and `forecast_trip_distance.py` where `MLClient` is instantiated.
   - `ml_client.datastores.create_or_update(ds)` -- registers/updates a `OneLakeDatastore` resource in the Azure ML workspace. See `run_analysis.py` and `auth.py`.

- **OneLake data connections (actual data reads):**
   - `OneLakeDatastore(...)` -- constructs the AML-side datastore entity referencing the lakehouse artifact (no immediate data transfer). See `run_analysis.py`, `auth.py`, and `forecast_trip_distance.py`.
   - REST listing/downloads to OneLake DFS using storage tokens:
      - Acquire storage token: `cred.get_token("https://storage.azure.com/.default").token` (used to authenticate DFS REST calls).
      - `requests.get(folder_url, headers=...)` -- attempts to list files in a OneLake folder (e.g., `nyc_taxi/puYear=YYYY/`).
      - `requests.get(download_url, headers=...)` -- downloads each discovered file (CSV/Parquet) and loads it into pandas.

Files referencing these calls:
- `auth.py`: MLClient, OneLakeDatastore registration, token acquisition, and example listing/download flow.
- `azureml_sample_project/run_analysis.py`: credential handling, `register_datastore()`, storage token acquisition, folder listing and file download logic.
- `azureml_sample_project/forecast_trip_distance.py`: credential handling, optional `OneLakeDatastore` creation for AML registration, per-year folder listing, and per-file downloads (it now aggregates all files per year).

Notes & recommendations:
- The only AML operations that modify workspace state are the `ml_client.datastores.create_or_update(...)` calls -- these register datastore metadata with the workspace.
- Actual file data is read client-side via authenticated HTTP requests to the OneLake DFS endpoint (`<one_lake_workspace>.dfs.fabric.microsoft.com`). If you prefer, we can replace the direct REST calls with SDK-based OneLake/DFS clients or use Azure ML Dataset APIs to simplify data access and improve error handling.

**Env Var Config**

- **AZ_SUBSCRIPTION_ID**: GUID — Azure subscription ID. Example: **12345678-1234-1234-1234-123456789abc**.
- **AZ_RESOURCE_GROUP**: Azure resource group name. Example: **my-aml-rg**.
- **AZ_WORKSPACE_NAME**: Azure ML workspace name. Example: **my-aml-workspace**.
- **ONE_LAKE_WORKSPACE**: OneLake workspace host or GUID; used to form the DFS host `{ONE_LAKE_WORKSPACE}.dfs.fabric.microsoft.com`. Examples: **9f8e7d6c-1234-4321-abcd-1234567890ab** or **my-onelake-host**.
- **ARTIFACT_NAME**: Lakehouse artifact path (lakehouse id + `/Files` or simple artifact path). Example: **Files/nyc_taxi**.

Notes:
- The script looks for a `.env` file (package folder, repo root, or current working directory) and loads KEY=VALUE pairs if present; environment variables take precedence.
- `ONE_LAKE_WORKSPACE` is used to construct URLs like `https://{ONE_LAKE_WORKSPACE}.dfs.fabric.microsoft.com/{ARTIFACT_NAME}/{path}`.
- `AZ_*` values are passed to `MLClient(...)`; missing values may cause `MLClient` to fail unless your credential context provides defaults.

OneLake-only note:
- This sample is intentionally OneLake-only. The program always reads from the specified `ARTIFACT_NAME` (artifact root) in OneLake; users bring their own data by uploading files into that OneLake artifact. The `LOCAL_TEST_FILE`, `DATA_FILE_PATH`, and `DATA_FOLDER` options have been removed to reduce configuration surface area.

**Install Summary & Logs**

- The project dependencies used for testing are installed into the test venv at: `azureml_sample_install/.venv`.
- Captured installer output: `azureml_sample_install/install_output.txt`.
- Captured installed package list (pip freeze): `azureml_sample_install/freeze.txt`.

Sample lines from `install_output.txt`:
```
Requirement already satisfied: azure-ai-ml in .\\azureml_sample_install\\.venv\\Lib\\site-packages (from -r azureml_sample_install\\azureml_sample_project\\requirements.txt (line 1)) (1.31.0)
Requirement already satisfied: pandas in .\\azureml_sample_install\\.venv\\Lib\\site-packages (from -r azureml_sample_install\\azureml_sample_project\\requirements.txt (line 3)) (3.0.1)
```

Top packages from `freeze.txt` (full file at path above):
```
azure-ai-ml==1.31.0
pandas==3.0.1
azure-identity==1.25.2
requests==2.32.5
pyarrow==23.0.1
```

You can archive the logs with: `docs/install_logs.zip` (created in repo by the maintainer for distribution).

Minimal install (OneLake-only runtime)

If you only need the OneLake auth + REST + pandas/parquet functionality (no AML registration or training), install the smaller set:

```powershell
python -m pip install -r azureml_sample_project/requirements-min.txt
```

Full install (includes Azure ML SDK and training deps)

```powershell
python -m pip install -r azureml_sample_project/requirements.txt
```

Notes:
- `requirements-min.txt` contains `azure-identity`, `requests`, `pandas`, and `pyarrow` and is suitable for the OneLake-only analysis flow.
- Use the full `requirements.txt` when you want `azure-ai-ml` (datastore registration) or training utilities such as `scikit-learn`.

**Version 1 (Primary) Project Location**

- The primary sample (v1) is `azureml_sample_project` — this folder contains `run_analysis.py`, `forecast_trip_distance.py`, `train_model.py`, `requirements.txt`, and sample CSVs.
- A root-level runner `run_analysis.py` was added to call into the package runner so you can run the project from the repository root.
- Temporary helper files created during edits: `scripts/check_imports.py`, `scripts/remove_bom.py`, and `azureml_sample_project/run_analysis_fixed.py` (copy). Remove them if you want a clean tree.




