"""Aggregate nyc_taxi trip distances by year (2008-2020), fit a linear trend,
and predict mean trip distance for 2023 and 2030.

Supports LOCAL_TEST_FILE (single CSV used for all years) or reading per-year
files from a local directory `LOCAL_DATA_DIR` with filenames containing
`puYear=YYYY`.

If `USE_ONELAKE=1`, the script will attempt to download per-year files from
the configured OneLake artifact (requires proper env vars and credentials).
"""

import os
import re
import io
import glob
import requests
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

from azure.ai.ml import MLClient
from azure.ai.ml.entities import OneLakeDatastore
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential


YEARS = list(range(2008, 2021))


def get_credential():
	try:
		cred = DefaultAzureCredential()
		cred.get_token("https://management.azure.com/.default")
		return cred
	except Exception:
		ibc = InteractiveBrowserCredential()
		ibc.get_token("https://management.azure.com/.default")
		return ibc


def read_local_file(path):
	if path.endswith('.csv'):
		return pd.read_csv(path)
	if path.endswith('.parquet'):
		return pd.read_parquet(path)
	# fallback try csv
	return pd.read_csv(path)


def collect_year_local(local_dir=None, local_file=None):
	results = {}
	if local_file:
		# Read the single file and, if it contains datetime info, split by year.
		# NOTE: This local-file branch is provided so the package runs offline.
		# In a OneLake-enabled demo you'd instead call the OneLake listing and
		# download logic (see `collect_year_onelake`) to fetch per-year files
		# from the lakehouse. Replace this branch with OneLake reads when
		# demonstrating the real connector.
		df_all = read_local_file(local_file)
		if "pickup_datetime" in df_all.columns:
			df_all["pickup_datetime"] = pd.to_datetime(df_all["pickup_datetime"], errors="coerce")
			df_all["_year"] = df_all["pickup_datetime"].dt.year
			for y in YEARS:
				sub = df_all[df_all["_year"] == y]
				results[y] = sub if not sub.empty else None
			return results
		else:
			# fallback: use same file for all years (no datetime info)
			for y in YEARS:
				df = read_local_file(local_file)
				results[y] = df
			return results

	if local_dir:
		# look for files containing puYear=YYYY
		for y in YEARS:
			pattern = os.path.join(local_dir, f"*puYear={y}*.*")
			matches = glob.glob(pattern)
			if matches:
				# take first match
				results[y] = read_local_file(matches[0])
			else:
				results[y] = None
		return results

	raise ValueError("Provide LOCAL_TEST_FILE or LOCAL_DATA_DIR for local collection")


def collect_year_onelake(cred, ds, artifact_name):
	# similar to run_analysis: attempt to list folder and download first file
	base_host = f"{ds.one_lake_workspace_name}.dfs.fabric.microsoft.com"
	artifact_path = artifact_name.rstrip('/')
	token = cred.get_token("https://storage.azure.com/.default").token
	headers = {"Authorization": f"Bearer {token}"}

	results = {}
	for y in YEARS:
		folder = f"nyc_taxi/puYear={y}/"
		folder_url = f"https://{base_host}/{artifact_path}/{folder.lstrip('/') }"
		try:
			resp = requests.get(folder_url, headers=headers, timeout=30)
			resp.raise_for_status()
			files = []
			ct = resp.headers.get('Content-Type','')
			if 'json' in ct:
				body = resp.json()
				for key in ('value','children','files','items'):
					if key in body and isinstance(body[key], list):
						for it in body[key]:
							if isinstance(it, dict):
								name = it.get('name') or it.get('path')
								if name:
									files.append(name)
			else:
				hrefs = re.findall(r'href=["\']([^"\']+)["\']', resp.text)
				for h in hrefs:
					if h.endswith(('.csv','.parquet')):
						files.append(h.split('/')[-1])
			if not files:
				results[y] = None
				continue
			# Download and concat all files discovered for the year
			year_dfs = []
			for fname in files:
				try:
					download_url = f"https://{base_host}/{artifact_path}/{folder.rstrip('/')}/{fname}"
					resp2 = requests.get(download_url, headers=headers, timeout=60)
					resp2.raise_for_status()
					ext = os.path.splitext(fname)[1].lower()
					if ext == '.csv' or 'text' in resp2.headers.get('Content-Type',''):
						df_part = pd.read_csv(io.StringIO(resp2.text))
					else:
						df_part = pd.read_parquet(io.BytesIO(resp2.content))
					year_dfs.append(df_part)
				except Exception:
					# skip problematic file but continue with others
					continue
			if year_dfs:
				results[y] = pd.concat(year_dfs, ignore_index=True)
			else:
				results[y] = None
		except Exception:
			results[y] = None
	return results


def aggregate_means(dfs_by_year):
	rows = []
	for y, df in dfs_by_year.items():
		if df is None:
			rows.append({'year': y, 'mean_trip_distance': np.nan, 'count': 0})
			continue
		if 'trip_distance' not in df.columns:
			rows.append({'year': y, 'mean_trip_distance': np.nan, 'count': len(df)})
			continue
		mean = pd.to_numeric(df['trip_distance'], errors='coerce').dropna().mean()
		rows.append({'year': y, 'mean_trip_distance': mean, 'count': len(df)})
	return pd.DataFrame(rows)


def fit_and_forecast(df_years):
	# use only years with non-null mean
	df = df_years.dropna(subset=['mean_trip_distance']).copy()
	X = df[['year']].values
	y = df['mean_trip_distance'].values
	model = LinearRegression()
	model.fit(X, y)
	# predict for 2030 only
	pred = model.predict(np.array([[2030]]))[0]
	print(f"Predicted mean trip_distance for 2030: {pred:.4f}")
	return model


def main():
	# config via env
	local_file = os.environ.get('LOCAL_TEST_FILE')
	local_dir = os.environ.get('LOCAL_DATA_DIR')
	use_onelake = os.environ.get('USE_ONELAKE')

	if local_file or local_dir:
		dfs = collect_year_local(local_dir, local_file)
	elif use_onelake:
		cred = get_credential()
		# minimal ml client to register datastore if needed
		subscription = os.environ.get('AZ_SUBSCRIPTION_ID', '')
		rg = os.environ.get('AZ_RESOURCE_GROUP', '')
		ws = os.environ.get('AZ_WORKSPACE_NAME', '')
		ml_client = MLClient(cred, subscription, rg, ws)
		artifact_name = os.environ.get('ARTIFACT_NAME', '{{ARTIFACT_NAME}}')
		ds = OneLakeDatastore(name='fabric_onelake_ds', endpoint='onelake.dfs.fabric.microsoft.com', artifact={'name': artifact_name, 'type': 'lake_house'}, one_lake_workspace_name=os.environ.get('ONE_LAKE_WORKSPACE'))
		dfs = collect_year_onelake(cred, ds, artifact_name)
	else:
		raise SystemExit('Set LOCAL_TEST_FILE or LOCAL_DATA_DIR or USE_ONELAKE=1')

	df_years = aggregate_means(dfs)
	print(df_years)

	# Fit and forecast
	model = fit_and_forecast(df_years)

	# Save results: per-year means and 2030 prediction to CSV
	pred_2030 = model.predict(np.array([[2030]]))[0]
	out = df_years.copy()
	out['predicted'] = False
	out = out[['year', 'mean_trip_distance', 'count', 'predicted']]
	out = out.sort_values('year')
	# append prediction row for 2030
	new_row = pd.DataFrame([{'year': 2030, 'mean_trip_distance': pred_2030, 'count': np.nan, 'predicted': True}])
	out = pd.concat([out, new_row], ignore_index=True)
	out_path = os.path.join(os.path.dirname(__file__), 'predicted_trip_distance_2030.csv')
	out.to_csv(out_path, index=False)
	print(f"Saved per-year means + 2030 prediction to: {out_path}")

	print("No 2023 comparison performed (data only through 2020).")


if __name__ == '__main__':
	main()
