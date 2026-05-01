"""
Central configuration for the Cairo Smart Transportation System.
Import constants from here instead of scattering magic numbers across files.
"""
from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
PORT: int = int(os.environ.get("PORT", "5000"))
DEBUG: bool = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
HOST: str = "0.0.0.0"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR: str = os.path.dirname(__file__)
MODEL_PATH: str = os.environ.get(
    "TRAFFIC_MODEL_PATH",
    os.path.join(BASE_DIR, "models", "traffic_rf.joblib"),
)
DATA_DIR: str = os.path.join(BASE_DIR, "data")
DEFAULT_CSV: str = os.path.join(DATA_DIR, "traffic_data.csv")

# ---------------------------------------------------------------------------
# Graph / routing
# ---------------------------------------------------------------------------
FREE_FLOW_SPEED_KMH: float = 60.0          # used by BPR travel-time model
BPR_ALPHA: float = 0.15                    # Bureau of Public Roads: alpha
BPR_BETA: float = 4.0                      # Bureau of Public Roads: beta
KM_PER_DEG_LAT: float = 110.574           # km per degree latitude ~Cairo
KM_PER_DEG_LON: float = 96.486            # km per degree longitude at 30°N

# ---------------------------------------------------------------------------
# ML model defaults
# ---------------------------------------------------------------------------
ML_N_ESTIMATORS: int = 200
ML_MAX_DEPTH: int = 8
ML_TEST_SIZE: float = 0.2
ML_RANDOM_STATE: int = 42
PERIOD_HOURS: dict[str, int] = {
    "morning": 8,
    "afternoon": 14,
    "evening": 18,
    "night": 2,
}
ML_FEATURE_NAMES: list[str] = [
    "hour_sin", "hour_cos", "distance_km",
    "capacity", "is_existing", "mean_endpoint_population",
]

# ---------------------------------------------------------------------------
# DP / scheduling
# ---------------------------------------------------------------------------
DEFAULT_TOTAL_VEHICLES: int = 300
DEFAULT_MAINTENANCE_BUDGET_MEPP: int = 500   # million EGP

# ---------------------------------------------------------------------------
# Emergency
# ---------------------------------------------------------------------------
SIGNAL_PREEMPTION_RADIUS_KM: float = 2.0
AMBULANCE_SPEED_KMH: float = 80.0

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FORMAT: str = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
