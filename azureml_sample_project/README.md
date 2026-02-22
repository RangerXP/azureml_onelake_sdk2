# AzureML OneLake sample (minimal)

This small sample shows how to register a OneLake datastore in AzureML and perform
a minimal analysis on the `Files/nyc_taxi/puYear=2020/` data.

Files:
- `run_analysis.py` €” main script
- `requirements.txt` €” Python dependencies

Quick local test (no Azure):

PowerShell:
```powershell
$env:LOCAL_TEST_FILE='c:\\temp\\azureml_onelake_sdk\azureml\sample_nyc.csv'
C:/mslearn/dp-600/.venv/Scripts/python.exe c:\\temp\\azureml_onelake_sdk\azureml\azureml_sample_project\run_analysis.py
```

Run against OneLake (interactive auth):

1. (Optional) set environment variables to override defaults:
   - `AZ_SUBSCRIPTION_ID`, `AZ_RESOURCE_GROUP`, `AZ_WORKSPACE_NAME`
   - `ONE_LAKE_WORKSPACE` €” the OneLake workspace GUID
   - `ARTIFACT_NAME` €” lakehouse id + `/Files` (defaults included in script)
   - `DATA_FILE_PATH` €” optional exact path under the artifact

2. Install requirements in your venv:
```powershell
python -m pip install -r c:\\temp\\azureml_onelake_sdk\azureml\azureml_sample_project\requirements.txt
```

3. Run the script:
```powershell
C:/mslearn/dp-600/.venv/Scripts/python.exe c:\\temp\\azureml_onelake_sdk\azureml\azureml_sample_project\run_analysis.py
```

If the OneLake listing/download fails, copy the error and I can help adjust the URL/auth scope.

**AzureML & OneLake Integration**

This project performs two kinds of Azure-related actions:

- **Azure ML service calls (AML API):**
   - `MLClient(...)` €” creates the Azure ML client used to operate on the workspace. See `run_analysis.py` and `forecast_trip_distance.py` where `MLClient` is instantiated.
   - `ml_client.datastores.create_or_update(ds)` €” registers/updates a `OneLakeDatastore` resource in the Azure ML workspace. See `run_analysis.py` and `auth.py`.

- **OneLake data connections (actual data reads):**
   - `OneLakeDatastore(...)` €” constructs the AML-side datastore entity referencing the lakehouse artifact (no immediate data transfer). See `run_analysis.py`, `auth.py`, and `forecast_trip_distance.py`.
   - REST listing/downloads to OneLake DFS using storage tokens:
      - Acquire storage token: `cred.get_token("https://storage.azure.com/.default").token` (used to authenticate DFS REST calls).
      - `requests.get(folder_url, headers=...)` €” attempts to list files in a OneLake folder (e.g., `nyc_taxi/puYear=YYYY/`).
      - `requests.get(download_url, headers=...)` €” downloads each discovered file (CSV/Parquet) and loads it into pandas.

Files referencing these calls:
- `auth.py`: MLClient, OneLakeDatastore registration, token acquisition, and example listing/download flow.
- `azureml_sample_project/run_analysis.py`: credential handling, `register_datastore()`, storage token acquisition, folder listing and file download logic.
- `azureml_sample_project/forecast_trip_distance.py`: credential handling, optional `OneLakeDatastore` creation for AML registration, per-year folder listing, and per-file downloads (it now aggregates all files per year).

Notes & recommendations:
- The only AML operations that modify workspace state are the `ml_client.datastores.create_or_update(...)` calls €” these register datastore metadata with the workspace.
- Actual file data is read client-side via authenticated HTTP requests to the OneLake DFS endpoint (`<one_lake_workspace>.dfs.fabric.microsoft.com`). If you prefer, we can replace the direct REST calls with SDK-based OneLake/DFS clients or use Azure ML Dataset APIs to simplify data access and improve error handling.



