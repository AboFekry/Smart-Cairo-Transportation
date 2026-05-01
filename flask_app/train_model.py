"""
Standalone training script for the Cairo traffic-prediction model.

Reads a CSV file, trains a RandomForestRegressor, evaluates it on a held-out
test split, prints metrics, and persists the trained pipeline to disk so the
Flask app can load it without retraining.

Examples
--------
Train with the bundled CSV and default hyper-parameters::

    python train_model.py

Train on a custom CSV and save under a different name::

    python train_model.py --data data/my_traffic.csv --output models/v2.joblib

Override hyper-parameters and the test split::

    python train_model.py --n-estimators 400 --max-depth 12 --test-size 0.25

CSV schema (header row required)
--------------------------------
road_id, from_node, to_node, period, hour, distance_km, capacity,
mean_endpoint_population, is_existing, vehicles_per_hour

Only the numeric feature columns and the target are used:
  Features:  hour, distance_km, capacity, mean_endpoint_population, is_existing
  Target  :  vehicles_per_hour

The script applies a cyclic encoding to the `hour` feature internally
(hour_sin, hour_cos) so the model can learn the diurnal pattern.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


REQUIRED_COLUMNS = [
    "hour", "distance_km", "capacity",
    "mean_endpoint_population", "is_existing", "vehicles_per_hour",
]

FEATURE_NAMES = [
    "hour_sin", "hour_cos", "distance_km",
    "capacity", "is_existing", "mean_endpoint_population",
]


def _hour_features(hour: float) -> tuple[float, float]:
    angle = 2 * math.pi * (hour % 24) / 24.0
    return math.sin(angle), math.cos(angle)


def build_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Turn a raw dataframe into the X / y arrays the model trains on."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"CSV is missing required columns: {missing}. "
            f"Required schema: {REQUIRED_COLUMNS}"
        )
    df = df.dropna(subset=REQUIRED_COLUMNS).copy()
    df["hour_sin"] = df["hour"].apply(lambda h: math.sin(2 * math.pi * (h % 24) / 24.0))
    df["hour_cos"] = df["hour"].apply(lambda h: math.cos(2 * math.pi * (h % 24) / 24.0))
    X = df[FEATURE_NAMES].to_numpy(dtype=float)
    y = df["vehicles_per_hour"].to_numpy(dtype=float)
    return X, y


def train_and_evaluate(
    csv_path: str,
    output_path: str,
    test_size: float = 0.2,
    n_estimators: int = 200,
    max_depth: int = 8,
    random_state: int = 42,
    verbose: bool = True,
) -> dict[str, Any]:
    """End-to-end pipeline: load CSV -> features -> fit -> evaluate -> save."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    if verbose:
        print(f"Loading dataset: {csv_path}")
    df = pd.read_csv(csv_path)
    if verbose:
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {list(df.columns)}")

    X, y = build_features(df)
    if len(X) < 8:
        raise ValueError(f"Need at least 8 rows to train; got {len(X)}.")

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    if verbose:
        print(f"\nTraining RandomForestRegressor "
              f"(n_estimators={n_estimators}, max_depth={max_depth})")
        print(f"  Train samples: {len(X_tr)}")
        print(f"  Test  samples: {len(X_te)}")

    model = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        n_jobs=-1,
    )
    t0 = time.perf_counter()
    model.fit(X_tr, y_tr)
    train_ms = (time.perf_counter() - t0) * 1000.0

    y_pred_te = model.predict(X_te)
    y_pred_tr = model.predict(X_tr)

    metrics: dict[str, Any] = {
        "model": "RandomForestRegressor",
        "n_estimators": n_estimators,
        "max_depth": max_depth,
        "samples_total": int(len(X)),
        "samples_train": int(len(X_tr)),
        "samples_test": int(len(X_te)),
        "test_mae_vehicles_per_hour": round(float(mean_absolute_error(y_te, y_pred_te)), 2),
        "test_rmse_vehicles_per_hour": round(float(math.sqrt(mean_squared_error(y_te, y_pred_te))), 2),
        "test_r2": round(float(r2_score(y_te, y_pred_te)), 4),
        "train_mae_vehicles_per_hour": round(float(mean_absolute_error(y_tr, y_pred_tr)), 2),
        "train_r2": round(float(r2_score(y_tr, y_pred_tr)), 4),
        "train_time_ms": round(train_ms, 2),
        "feature_importances": [
            {"feature": k, "importance": round(float(v), 4)}
            for k, v in sorted(
                zip(FEATURE_NAMES, model.feature_importances_),
                key=lambda kv: -kv[1],
            )
        ],
    }

    if verbose:
        print("\n=== Evaluation ===")
        print(f"  Test  R²   : {metrics['test_r2']}")
        print(f"  Test  MAE  : {metrics['test_mae_vehicles_per_hour']} veh/h")
        print(f"  Test  RMSE : {metrics['test_rmse_vehicles_per_hour']} veh/h")
        print(f"  Train R²   : {metrics['train_r2']}")
        print(f"  Train MAE  : {metrics['train_mae_vehicles_per_hour']} veh/h")
        print(f"  Train time : {metrics['train_time_ms']} ms")
        print("\n  Feature importances:")
        for fi in metrics["feature_importances"]:
            bar = "█" * int(round(fi["importance"] * 30))
            print(f"    {fi['feature']:<28} {fi['importance']:.3f}  {bar}")

    # Persist the model
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    bundle = {
        "model": model,
        "feature_names": FEATURE_NAMES,
        "metrics": metrics,
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source_csv": os.path.abspath(csv_path),
    }
    joblib.dump(bundle, output_path)
    if verbose:
        size_kb = os.path.getsize(output_path) / 1024
        print(f"\nSaved model bundle to {output_path} ({size_kb:.1f} KB)")

    # Also save a sidecar metrics.json for easy inspection
    metrics_path = os.path.splitext(output_path)[0] + ".metrics.json"
    with open(metrics_path, "w") as fh:
        json.dump(metrics, fh, indent=2)
    if verbose:
        print(f"Saved metrics report to {metrics_path}")

    return metrics


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Train the Cairo traffic-prediction model from a CSV file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--data", default="data/traffic_data.csv",
                        help="Path to the training CSV (default: data/traffic_data.csv).")
    parser.add_argument("--output", default="models/traffic_rf.joblib",
                        help="Where to write the trained model bundle "
                             "(default: models/traffic_rf.joblib).")
    parser.add_argument("--test-size", type=float, default=0.2,
                        help="Test split fraction (default: 0.2).")
    parser.add_argument("--n-estimators", type=int, default=200,
                        help="Number of trees in the forest (default: 200).")
    parser.add_argument("--max-depth", type=int, default=8,
                        help="Maximum tree depth (default: 8).")
    parser.add_argument("--random-state", type=int, default=42,
                        help="Random seed (default: 42).")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress progress output.")
    args = parser.parse_args(argv)

    try:
        train_and_evaluate(
            csv_path=args.data,
            output_path=args.output,
            test_size=args.test_size,
            n_estimators=args.n_estimators,
            max_depth=args.max_depth,
            random_state=args.random_state,
            verbose=not args.quiet,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
