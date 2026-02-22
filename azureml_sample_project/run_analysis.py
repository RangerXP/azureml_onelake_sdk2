"""Minimal AzureML sample: register OneLake datastore and analyze nyc_taxi data.

Usage:
 - For a quick local test set `LOCAL_TEST_FILE` to a CSV/Parquet file and run.
 - To connect to Azure ML set env vars `AZ_SUBSCRIPTION_ID`, `AZ_RESOURCE_GROUP`,
   `AZ_WORKSPACE_NAME` (or edit defaults below). Optionally set `DATA_FILE_PATH`
   to point to the file under the lakehouse artifact (e.g. nyc_taxi/puYear=2020/file.parquet).

This script performs a minimal register of a OneLake datastore (no private imports)
and does a best-effort download of a file from the Files/nyc_taxi/puYear=2020/ folder
then loads it into pandas and prints basic stats.
"""

import os
import io
import requests
import pandas as pd
from azure.ai.ml import MLClient
from azure.ai.ml.entities import OneLakeDatastore
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential


def get_credential():
    try:
        cred = DefaultAzureCredential()
        cred.get_token("https://management.azure.com/.default")
        print("Authenticated with DefaultAzureCredential")
        return cred
    except Exception:
        ibc = InteractiveBrowserCredential()
        ibc.get_token("https://management.azure.com/.default")
        print("Authenticated with InteractiveBrowserCredential")
        return ibc


def register_datastore(ml_client, artifact_name, one_lake_workspace_name):
    artifact = {"name": artifact_name, "type": "lake_house"}
    ds = OneLakeDatastore(
        name="fabric_onelake_ds",
        description="OneLake (Fabric) Lakehouse datastore for Azure ML",
        endpoint="onelake.dfs.fabric.microsoft.com",
        artifact=artifact,
        one_lake_workspace_name=one_lake_workspace_name,
    )
    ml_client.datastores.create_or_update(ds)
    print("Registered datastore:", ds.name)
    return ds


def download_first_file_from_folder(cred, ds, artifact_name, folder_path):
    token = cred.get_token("https://storage.azure.com/.default").token
    headers = {"Authorization": f"Bearer {token}"}
    base_host = f"{ds.one_lake_workspace_name}.dfs.fabric.microsoft.com"
    artifact_path = artifact_name.rstrip("/")
    folder_path = folder_path.lstrip("/")
    folder_url = f"https://{base_host}/{artifact_path}/{folder_path}"

    resp = requests.get(folder_url, headers=headers, timeout=30)
    resp.raise_for_status()

    files = []
    ct = resp.headers.get("Content-Type", "")
    if "json" in ct:
        body = resp.json()
        for key in ("value", "children", "files", "items"):
            if key in body and isinstance(body[key], list):
                for it in body[key]:
                    if isinstance(it, dict):
                        name = it.get("name") or it.get("path")
                        if name:
                            files.append(name)
    else:
        # HTML listing fallback
        import re

        hrefs = re.findall(r'href=["\']([^"\']+)["\']', resp.text)
        for h in hrefs:
            if h.endswith((".csv", ".parquet", ".txt")):
                files.append(h.split("/")[-1])

    if not files:
        raise RuntimeError("No files found in folder")

    chosen = files[0]
    file_path = folder_path.rstrip("/") + "/" + chosen
    download_url = f"https://{base_host}/{artifact_path}/{file_path}"
    print("Downloading:", download_url)

    resp2 = requests.get(download_url, headers=headers, timeout=60)
    resp2.raise_for_status()
    return chosen, resp2


def load_response_into_dataframe(file_name, response):
    ext = os.path.splitext(file_name)[1].lower()
    if ext == ".csv":
        return pd.read_csv(io.StringIO(response.text))
    if ext in (".parquet", ".pq"):
        return pd.read_parquet(io.BytesIO(response.content))
    # fallback: try CSV
    try:
        return pd.read_csv(io.StringIO(response.text))
    except Exception:
        # save locally for inspection
        local_name = os.path.basename(file_name)
        with open(local_name, "wb") as fh:
            fh.write(response.content)
        raise


def main():
    # allow overrides via env
    subscription_id = os.environ.get("AZ_SUBSCRIPTION_ID", "{{AZ_SUBSCRIPTION_ID}}")
    resource_group = os.environ.get("AZ_RESOURCE_GROUP", "{{AZ_RESOURCE_GROUP}}")
    workspace = os.environ.get("AZ_WORKSPACE_NAME", "{{AZ_WORKSPACE_NAME}}")
    one_lake_workspace_name = os.environ.get("ONE_LAKE_WORKSPACE", "{{ONE_LAKE_WORKSPACE}}")
    artifact_name = os.environ.get("ARTIFACT_NAME", "{{ARTIFACT_NAME}}")
    target_folder = os.environ.get("DATA_FOLDER", "nyc_taxi/puYear=2020/")

    # Local quick test mode
    local_test = os.environ.get("LOCAL_TEST_FILE")
    if local_test:
        # LOCAL_TEST_FILE is set â€” load a local CSV/Parquet for quick testing.
        # NOTE: In a production or demo against OneLake, replace this branch
        # with the OneLake download flow below (use the MLClient / OneLakeDatastore
        # + storage bearer token to list/download files). This local branch is
        # intentionally simple so external recipients can run the package offline.
        print("LOCAL_TEST_FILE set â€” loading local file", local_test)
        df = pd.read_csv(local_test) if local_test.endswith(".csv") else pd.read_parquet(local_test)
        print("Rows:", len(df))
        print(df.head())
        return

    cred = get_credential()
    ml_client = MLClient(cred, subscription_id=subscription_id, resource_group_name=resource_group, workspace_name=workspace)

    ds = register_datastore(ml_client, artifact_name, one_lake_workspace_name)

    # optional: allow user to specify exact file path
    data_file_path = os.environ.get("DATA_FILE_PATH")
    if data_file_path:
        # build direct download
        chosen = os.path.basename(data_file_path)
        base_host = f"{one_lake_workspace_name}.dfs.fabric.microsoft.com"
        download_url = f"https://{base_host}/{artifact_name.rstrip('/')}/{data_file_path.lstrip('/') }"
        token = cred.get_token("https://storage.azure.com/.default").token
        resp = requests.get(download_url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
        resp.raise_for_status()
        df = load_response_into_dataframe(chosen, resp)
    else:
        chosen, resp = download_first_file_from_folder(cred, ds, artifact_name, target_folder)
        df = load_response_into_dataframe(chosen, resp)

    print("Loaded dataframe rows:", len(df))
    print(df.head())
    # sample analysis: if trip_distance exists, print mean
    if "trip_distance" in df.columns:
        print("Mean trip_distance:", df["trip_distance"].astype(float).mean())


if __name__ == "__main__":
    main()

