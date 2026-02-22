"""Train a minimal linear regression model on nyc_taxi sample.

This script is intentionally minimal for demonstration. It:
- Loads a CSV (use LOCAL_TEST_FILE for local testing)
- Extracts simple features (passenger_count, pickup hour, vendor_id dummies)
- Trains sklearn LinearRegression
- Prints MSE and model coefficients
- Saves model to `model.joblib`
"""

import os
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
import joblib


def load_data(path):
    df = pd.read_csv(path)
    # basic parsing
    if "pickup_datetime" in df.columns:
        df["pickup_datetime"] = pd.to_datetime(df["pickup_datetime"]) 
        df["hour"] = df["pickup_datetime"].dt.hour
    else:
        df["hour"] = 0

    # ensure numeric target
    df = df.dropna(subset=["trip_distance"]) 
    df["trip_distance"] = pd.to_numeric(df["trip_distance"], errors="coerce").fillna(0.0)
    return df


def build_features(df):
    features = ["passenger_count", "hour"]
    X = df[features].copy()
    if "vendor_id" in df.columns:
        dummies = pd.get_dummies(df["vendor_id"].astype(str), prefix="vendor")
        X = pd.concat([X, dummies], axis=1)
    return X


def main():
    local = os.environ.get("LOCAL_TEST_FILE")
    if not local:
        # For quick local tests we require a CSV via LOCAL_TEST_FILE. In a full
        # demo against OneLake you would replace this with code to download the
        # dataset from the lakehouse (use MLClient + OneLakeDatastore registration
        # + acquiring a storage token to call the OneLake DFS endpoints). Keeping
        # a local-only branch makes the sample easy to run without Azure access.
        print("For a quick test set LOCAL_TEST_FILE to your CSV path and re-run.")
        return

    df = load_data(local)
    X = build_features(df)
    y = df["trip_distance"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

    model = LinearRegression()
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mse = mean_squared_error(y_test, preds)
    print(f"Trained LinearRegression â€” test MSE: {mse:.4f}")
    print("Coefficients:")
    for name, coef in zip(X.columns, model.coef_):
        print(f"  {name}: {coef:.4f}")

    out_path = os.path.join(os.getcwd(), "model.joblib")
    joblib.dump(model, out_path)
    print("Saved model to", out_path)


if __name__ == "__main__":
    main()

