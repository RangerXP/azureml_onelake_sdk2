"""Minimal AzureML sample: register OneLake datastore and analyze nyc_taxi data.

This file is a direct copy of the working sample used in the install workspace.
"""

import os
import sys
import subprocess
import pathlib


def _install_requirements():
    # Install requirements from the package folder requirements.txt
    req_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if not os.path.exists(req_path):
        return
    try:
        print("Ensuring required packages are installed (this may take a minute)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_path])
    except subprocess.CalledProcessError:
        print("Warning: failed to install requirements automatically. Please install manually:")
        print(f"{sys.executable} -m pip install -r {req_path}")


def _import_deps():
    # Import heavy deps after optional auto-install.
    global io, requests, pd, MLClient, OneLakeDatastore, DefaultAzureCredential, InteractiveBrowserCredential
    import io
    import requests
    import pandas as pd
    from azure.ai.ml import MLClient
    from azure.ai.ml.entities import OneLakeDatastore
    from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential


def load_dotenv_if_present():
    """Load simple KEY=VALUE pairs from a .env file into os.environ if not already set.

    Searches for a `.env` in the package folder and the repository root.
    """
    candidates = []
    pkg_dir = os.path.dirname(__file__)
    # package-level .env
    candidates.append(os.path.join(pkg_dir, ".env"))
    # repo root .env (one level up)
    candidates.append(os.path.abspath(os.path.join(pkg_dir, os.pardir, ".env")))
    # cwd .env
    candidates.append(os.path.join(os.getcwd(), ".env"))

    for p in candidates:
        if not p:
            continue
        try:
            if os.path.exists(p):
                with open(p, encoding="utf-8") as fh:
                    for raw in fh:
                        line = raw.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        # don't overwrite already-set env vars
                        os.environ.setdefault(k, v)
                print(f"Loaded environment variables from {p}")
                return
        except Exception:
            # non-fatal; ignore parse errors
            continue



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
    # Load .env (if present). Support a lightweight SMOKE_TEST mode that
    # avoids heavy Azure SDK imports so we can validate pandas/IO quickly.
    load_dotenv_if_present()
    if os.environ.get("SMOKE_TEST"):
        import pandas as pd
        sample = os.path.join(os.path.dirname(__file__), "synthetic_multi_year.csv")
        print("SMOKE_TEST mode: loading local sample ->", sample)
        df = pd.read_csv(sample)
        print("Rows:", len(df))
        print(df.head())
        return

    # ensure dependencies are installed, then import them
    _install_requirements()
    _import_deps()

    # Pre-fill with environment values or sensible placeholders
    subscription_id = os.environ.get("AZ_SUBSCRIPTION_ID", "")
    resource_group = os.environ.get("AZ_RESOURCE_GROUP", "")
    workspace = os.environ.get("AZ_WORKSPACE_NAME", "")
    one_lake_workspace_name = os.environ.get("ONE_LAKE_WORKSPACE", "")
    artifact_name = os.environ.get("ARTIFACT_NAME", "Files/nyc_taxi")

    # Use environment variables only (no interactive prompts).
    # Values can come from a .env file (loaded earlier) or the environment.
    print("Using environment variables for Azure/OneLake configuration")
    print(f"AZ_SUBSCRIPTION_ID={'set' if subscription_id else 'NOT SET'}")
    print(f"AZ_RESOURCE_GROUP={'set' if resource_group else 'NOT SET'}")
    print(f"AZ_WORKSPACE_NAME={'set' if workspace else 'NOT SET'}")
    print(f"ONE_LAKE_WORKSPACE={'set' if one_lake_workspace_name else 'NOT SET'}")
    print(f"ARTIFACT_NAME={artifact_name}")

    cred = get_credential()
    ml_client = MLClient(cred, subscription_id=subscription_id, resource_group_name=resource_group, workspace_name=workspace)

    ds = register_datastore(ml_client, artifact_name, one_lake_workspace_name)

    # Minimal OneLake-only flow: list the artifact root and download the first file.
    if not artifact_name:
        print("ERROR: ARTIFACT_NAME is not set. Set ARTIFACT_NAME to the OneLake artifact (e.g. Files/nyc_taxi).")
        return

    print("DATA SOURCE: OneLake artifact ->", artifact_name)
    # pass an empty folder path to `download_first_file_from_folder` to indicate artifact root
    chosen, resp = download_first_file_from_folder(cred, ds, artifact_name, "")
    df = load_response_into_dataframe(chosen, resp)

    print("Loaded dataframe rows:", len(df))
    print(df.head())
    if "trip_distance" in df.columns:
        print("Mean trip_distance:", df["trip_distance"].astype(float).mean())


if __name__ == "__main__":
    main()
