"""
ML-based traffic prediction (CSE112 Bonus — AI Tools & Technologies).

Trains a RandomForestRegressor on the provided temporal traffic data
(morning/afternoon/evening/night vehicles-per-hour for 28 roads) to forecast
the volume on every road for any hour of the day.

Features per (road, hour) sample:
    - hour_sin, hour_cos      # cyclic encoding of the 24-hour clock
    - distance_km             # length of the road
    - capacity                # vehicles/hour design capacity
    - is_existing             # 1 for existing road, 0 for potential
    - mean_endpoint_pop       # avg population of the two endpoints
    - is_weekend (always 0)   # placeholder; weekday only in dataset

Target: vehicles per hour observed on the road.

Provided slots: morning=8h, afternoon=14h, evening=18h, night=2h.
"""

from __future__ import annotations

import math
import os
import time
from typing import Dict, List

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from data import (
    EXISTING_ROADS,
    NEIGHBORHOODS,
    FACILITIES,
    POTENTIAL_ROADS,
    TRAFFIC_FLOW,
    road_key,
)

# If the standalone trainer (train_model.py) has saved a model bundle, the
# Flask app will load it from here on first prediction and skip in-process
# training entirely.
DEFAULT_MODEL_PATH = os.environ.get(
    "TRAFFIC_MODEL_PATH",
    os.path.join(os.path.dirname(__file__), "models", "traffic_rf.joblib"),
)

# Hour each provided traffic slot represents
PERIOD_HOURS = {"morning": 8, "afternoon": 14, "evening": 18, "night": 2}

# Build a fast lookup of node metadata
_NODE_META: Dict[str, Dict] = {}
for n in NEIGHBORHOODS:
    _NODE_META[n["id"]] = {"pop": n["population"], "type": n["type"]}
for f in FACILITIES:
    # Facilities don't have populations; use a representative weighting
    pop = {"Airport": 80000, "Transit Hub": 120000}.get(f["type"], 30000)
    _NODE_META[f["id"]] = {"pop": pop, "type": f["type"]}


def _hour_features(hour: float) -> tuple[float, float]:
    angle = 2 * math.pi * (hour % 24) / 24.0
    return math.sin(angle), math.cos(angle)


def _road_static_features(road: dict) -> tuple[float, float, float]:
    """(distance_km, capacity, mean_endpoint_population)."""
    a, b = road["a"], road["b"]
    pop_a = _NODE_META.get(a, {}).get("pop", 30000)
    pop_b = _NODE_META.get(b, {}).get("pop", 30000)
    return road["distance_km"], road["capacity"], (pop_a + pop_b) / 2.0


def _all_roads() -> List[dict]:
    out = []
    for r in EXISTING_ROADS:
        out.append({
            "a": r[0], "b": r[1],
            "distance_km": r[2], "capacity": r[3],
            "condition": r[4], "is_existing": 1,
        })
    for r in POTENTIAL_ROADS:
        out.append({
            "a": r[0], "b": r[1],
            "distance_km": r[2], "capacity": r[3],
            "construction_cost": r[4], "is_existing": 0,
        })
    return out


def _build_dataset() -> tuple[np.ndarray, np.ndarray, list[dict]]:
    """Returns (X, y, sample_meta) using only existing roads with traffic data."""
    X, y, meta = [], [], []
    for r in EXISTING_ROADS:
        a, b, dist, cap, _cond = r
        flow = TRAFFIC_FLOW.get(road_key(a, b))
        if flow is None:
            continue
        dist_km, capacity, mean_pop = _road_static_features({
            "a": a, "b": b, "distance_km": dist, "capacity": cap,
        })
        for period, vehicles in zip(
            ["morning", "afternoon", "evening", "night"], flow
        ):
            hour = PERIOD_HOURS[period]
            hs, hc = _hour_features(hour)
            X.append([hs, hc, dist_km, capacity, 1, mean_pop])
            y.append(vehicles)
            meta.append({"road": f"{a}-{b}", "period": period, "hour": hour})
    return np.array(X, dtype=float), np.array(y, dtype=float), meta


_MODEL: RandomForestRegressor | None = None
_METRICS: dict | None = None


def _try_load_persisted_model() -> bool:
    """Load a model previously saved by train_model.py if present on disk."""
    global _MODEL, _METRICS
    if not os.path.exists(DEFAULT_MODEL_PATH):
        return False
    try:
        bundle = joblib.load(DEFAULT_MODEL_PATH)
        _MODEL = bundle["model"]
        m = dict(bundle.get("metrics", {}))
        m["loaded_from_disk"] = DEFAULT_MODEL_PATH
        m["trained_at"] = bundle.get("trained_at")
        _METRICS = m
        return True
    except Exception:
        return False


def train(force: bool = False) -> dict:
    """Train (or retrain) the model and cache metrics.

    Behaviour:
      1. If a model bundle saved by train_model.py exists on disk and we
         haven't loaded it yet, load it (no retraining).
      2. Otherwise, train an in-process model from data.py.
      3. ``force=True`` always retrains in-process even if a disk model exists.
    """
    global _MODEL, _METRICS
    if _MODEL is not None and not force:
        return _METRICS  # type: ignore[return-value]
    if not force and _try_load_persisted_model():
        return _METRICS  # type: ignore[return-value]

    X, y, _meta = _build_dataset()
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    t0 = time.perf_counter()
    model = RandomForestRegressor(
        n_estimators=200, max_depth=8, random_state=42, n_jobs=-1
    )
    model.fit(X_tr, y_tr)
    train_ms = (time.perf_counter() - t0) * 1000

    y_pred = model.predict(X_te)
    mae = float(mean_absolute_error(y_te, y_pred))
    r2 = float(r2_score(y_te, y_pred))

    # Feature importances
    feat_names = [
        "hour_sin", "hour_cos", "distance_km",
        "capacity", "is_existing", "mean_endpoint_pop",
    ]
    importances = sorted(
        zip(feat_names, [float(v) for v in model.feature_importances_]),
        key=lambda kv: -kv[1],
    )

    _MODEL = model
    _METRICS = {
        "model": "RandomForestRegressor (200 trees, depth 8)",
        "samples_total": int(len(X)),
        "samples_train": int(len(X_tr)),
        "samples_test": int(len(X_te)),
        "test_mae_vehicles_per_hour": round(mae, 1),
        "test_r2": round(r2, 3),
        "train_ms": round(train_ms, 2),
        "feature_importances": [
            {"feature": k, "importance": round(v, 3)} for k, v in importances
        ],
    }
    return _METRICS


def predict_for_hour(hour: float) -> dict:
    """Predict vehicles/hour and V/C ratio for every road at the given hour."""
    if _MODEL is None:
        train()
    assert _MODEL is not None

    hs, hc = _hour_features(hour)
    roads = _all_roads()
    rows = []
    for r in roads:
        dist_km, capacity, mean_pop = _road_static_features(r)
        feats = np.array([[hs, hc, dist_km, capacity,
                           r["is_existing"], mean_pop]])
        veh = float(_MODEL.predict(feats)[0])
        veh = max(0.0, veh)
        vc = veh / capacity if capacity else 0.0
        rows.append({
            "a": r["a"],
            "b": r["b"],
            "predicted_vehicles_per_hour": round(veh, 0),
            "capacity": capacity,
            "vc_ratio": round(vc, 3),
            "is_existing": bool(r["is_existing"]),
        })
    rows.sort(key=lambda d: -d["vc_ratio"])
    return {
        "hour": hour,
        "metrics": _METRICS,
        "roads": rows,
        "top_congested": rows[:5],
    }


def hourly_profile(road_a: str, road_b: str) -> dict:
    """Return predicted vehicles/hour across all 24 hours for one road."""
    if _MODEL is None:
        train()
    assert _MODEL is not None

    target = None
    for r in _all_roads():
        if (r["a"] == road_a and r["b"] == road_b) or \
           (r["a"] == road_b and r["b"] == road_a):
            target = r
            break
    if target is None:
        return {"error": f"road {road_a}-{road_b} not found"}

    dist_km, capacity, mean_pop = _road_static_features(target)
    hours = list(range(24))
    preds = []
    for h in hours:
        hs, hc = _hour_features(h)
        feats = np.array([[hs, hc, dist_km, capacity,
                           target["is_existing"], mean_pop]])
        v = float(_MODEL.predict(feats)[0])
        preds.append({"hour": h, "vehicles_per_hour": round(max(0.0, v), 0)})
    return {
        "road": f"{road_a}-{road_b}",
        "capacity": capacity,
        "hourly": preds,
    }


def predict_custom(hour: float, distance_km: float, capacity: float, mean_pop: float, is_existing: int) -> dict:
    """Predict vehicles/hour and V/C ratio for a custom hypothetical road feature set."""
    if _MODEL is None:
        train()
    assert _MODEL is not None

    hs, hc = _hour_features(hour)
    feats = np.array([[hs, hc, distance_km, capacity, is_existing, mean_pop]])
    veh = float(_MODEL.predict(feats)[0])
    veh = max(0.0, veh)
    vc = veh / capacity if capacity else 0.0

    return {
        "predicted_vehicles_per_hour": round(veh, 0),
        "capacity": capacity,
        "vc_ratio": round(vc, 3)
    }
