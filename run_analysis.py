import os
import io
import tempfile
import concurrent.futures
import shutil
import subprocess
import contextlib
from azure.identity import (
    EnvironmentCredential,
    AzureCliCredential,
    DefaultAzureCredential,
    InteractiveBrowserCredential,
)
from azure.storage.filedatalake import DataLakeServiceClient


def load_env():
    p = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(p):
        with open(p, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_credential():
    def try_get_token(cred_obj, name, timeout=15):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(lambda: cred_obj.get_token('https://storage.azure.com/.default'))
                fut.result(timeout=timeout)
            print(f'Authenticated with {name}')
            return True
        except concurrent.futures.TimeoutError:
            print(f'{name} token request timed out ({timeout}s)')
            return False
        except Exception as ex:
            msg = str(ex).splitlines()[0]
            print(f'{name} not usable: {ex.__class__.__name__}: {msg}')
            return False

    client_id = os.environ.get('AZURE_CLIENT_ID')
    tenant_id = os.environ.get('AZURE_TENANT_ID')
    client_secret = os.environ.get('AZURE_CLIENT_SECRET')
    if client_id and tenant_id and client_secret:
        cred = EnvironmentCredential()
        if try_get_token(cred, 'EnvironmentCredential'):
            return cred

    az_path = shutil.which('az')
    if az_path and os.path.exists(az_path):
        # quick probe to ensure 'az' is responsive and logged in; avoid long hangs
        try:
            probe = subprocess.run([
                az_path, 'account', 'get-access-token', '--output', 'json',
                '--resource', 'https://storage.azure.com'
            ], capture_output=True, text=True, timeout=5)
            if probe.returncode == 0:
                cred = AzureCliCredential(process_timeout=30)
                if try_get_token(cred, 'AzureCliCredential', timeout=30):
                    return cred
            else:
                print('az CLI present but not returning tokens quickly; skipping AzureCliCredential')
        except subprocess.TimeoutExpired:
            print('az CLI probe timed out; skipping AzureCliCredential')
        except FileNotFoundError:
            # defensive: if the path disappears between which() and run(), just skip quietly
            pass
        except Exception:
            print('az CLI probe failed; skipping AzureCliCredential')

    # interactive browser fallback for local dev (no secrets)
    try:
        ib = InteractiveBrowserCredential()
        if try_get_token(ib, 'InteractiveBrowserCredential', timeout=60):
            return ib
    except Exception as ex:
        msg = str(ex).splitlines()[0]
        print(f'InteractiveBrowserCredential failed: {ex.__class__.__name__}: {msg}')

    # Try DefaultAzureCredential (silent) with a short timeout to avoid long hangs
    try:
        cred = DefaultAzureCredential()
        if try_get_token(cred, 'DefaultAzureCredential', timeout=5):
            return cred
    except Exception as ex:
        msg = str(ex).splitlines()[0]
        print(f'DefaultAzureCredential init failed: {ex.__class__.__name__}: {msg}')

    raise RuntimeError('No usable Azure credential available')


def _download_and_read(file_client):
    tmp = None
    try:
        downloader = file_client.download_file()
        tmp = tempfile.NamedTemporaryFile(delete=False)
        with open(tmp.name, 'wb') as fh:
            try:
                for chunk in downloader.chunks():
                    fh.write(chunk)
            except AttributeError:
                fh.write(downloader.readall())

        try:
            import pyarrow.parquet as pq
            df = pq.read_table(tmp.name).to_pandas()
        except Exception:
            import pandas as pd
            df = pd.read_csv(tmp.name)
        return df
    finally:
        if tmp is not None:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass


def pull_first_file(svc, workspace, artifact_id=None, rel_path=None):
    fs = svc.get_file_system_client(workspace)

    explicit = os.environ.get('ONE_LAKE_FILE_PATH')
    if explicit:
        file_client = fs.get_file_client(explicit)
        return _download_and_read(file_client)

    prefix = '/'.join([p for p in (artifact_id, (rel_path or '').lstrip('/')) if p])

    max_entries = int(os.environ.get('LISTING_MAX_ENTRIES', '50'))
    chosen = None
    count = 0
    for entry in fs.get_paths(path=prefix or None):
        if count >= max_entries:
            break
        count += 1
        if not getattr(entry, 'is_directory', False):
            chosen = entry.name
            break

    if not chosen:
        raise RuntimeError('No files found for prefix: ' + (prefix or '<root>'))

    print('Listing prefix:', prefix)
    print('Chosen path:', chosen)
    file_client = fs.get_file_client(chosen)
    return _download_and_read(file_client)


def main():
    load_env()
    cred = get_credential()
    endpoint = os.environ.get('ONE_LAKE_ENDPOINT', 'https://onelake.dfs.fabric.microsoft.com')
    workspace = os.environ.get('ONE_LAKE_WORKSPACE')
    if not workspace:
        raise RuntimeError('ONE_LAKE_WORKSPACE must be set')
    svc = DataLakeServiceClient(account_url=endpoint.rstrip('/'), credential=cred)
    df = pull_first_file(svc, workspace, artifact_id=os.environ.get('ARTIFACT_ID'), rel_path=os.environ.get('RELATIVE_PATH'))
    try:
        print(df.head(10).to_string(index=False))
    except Exception:
        print('Loaded rows:', len(df))


if __name__ == '__main__':
    main()
