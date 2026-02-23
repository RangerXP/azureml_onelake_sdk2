# azureml_sample

This package is a self-contained copy of the install/test workspace for the
AzureML → OneLake sample. It contains the analysis program and support files
so you can install and run the sample in isolation.

Contents
- `run_analysis.py` — main entry (delegates to `run_analysis_impl.py`).
- `run_analysis_impl.py` — analysis implementation (OneLake datastore registration and data read).
- `analysis_install.py` — helper to create a `.venv`, install requirements, and run a smoke test.
- `requirements.txt` — full runtime requirements (Azure ML + extras).
- `synthetic_multi_year.csv` — local sample used by `SMOKE_TEST`.
- `.env` — placeholders for Azure/OneLake configuration (edit before a full run).

Quick install & smoke test

1. From the package folder, create a venv and install requirements, then run a quick SMOKE_TEST:

```powershell
# from repository root
python -m venv azureml_sample\.venv
azureml_sample\.venv\Scripts\python.exe -m pip install -r azureml_sample\requirements.txt
# run smoke test
setx SMOKE_TEST 1
azureml_sample\.venv\Scripts\python.exe azureml_sample\run_analysis.py
```

Or use the helper script (creates venv if missing and runs smoke test):

```powershell
python azureml_sample\analysis_install.py
```

.env requirements
- `AZ_SUBSCRIPTION_ID` — Azure subscription id
- `AZ_RESOURCE_GROUP` — resource group containing the Azure ML workspace
- `AZ_WORKSPACE_NAME` — Azure ML workspace name
- `ONE_LAKE_WORKSPACE` — OneLake workspace id or host
- `ARTIFACT_NAME` — OneLake artifact path (e.g. `Files/nyc_taxi`)

For non-interactive runs, you can provide a service principal via env vars:

- `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`

Expected outputs
- During SMOKE_TEST the sample will load `synthetic_multi_year.csv` and print the dataframe head and row count.
- For a successful OneLake run the program will register the `OneLakeDatastore`, download the first file in the artifact root, print the dataframe head, and print `Mean trip_distance:`.

Post-evaluation
- After validating, merge any changes back into the main project as desired.
