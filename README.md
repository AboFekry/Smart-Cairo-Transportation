# Cairo Smart Transportation Network

> **CSE112 Algorithms Project** — interactive Flask web app that designs and
> optimizes a smart transportation network for Greater Cairo using graph
> algorithms, dynamic programming, greedy heuristics, and machine learning.

![Stack](https://img.shields.io/badge/python-3.11-blue)
![Flask](https://img.shields.io/badge/flask-3.x-black)
![ML](https://img.shields.io/badge/ML-scikit--learn-orange)
![Docker](https://img.shields.io/badge/docker-ready-blue)

## Overview

An end-to-end demo running over the provided Cairo dataset
(15 neighborhoods, 10 critical facilities, 28 existing roads, 15 potential
roads, 4 traffic time-slots, 3 metro lines, 10 bus routes, 17 transit demand
pairs).

Every required deliverable is implemented and exposed through both a JSON API
and a Leaflet-based dark UI:

| # | Deliverable | Algorithm | UI tab |
|---|---|---|---|
| A | Infrastructure network design | **Kruskal MST** with population priority + critical-facility lifting | **Network Design** |
| B | Shortest-path routing | **Dijkstra** (km), **time-dependent Dijkstra** (BPR), **A\*** (Haversine) | **Routing** |
| C | Emergency response | **A\*** + greedy **signal preemption** | **Emergency** |
| D | Public transit optimization | Bounded-knapsack **DP** with diminishing returns | **Transit** |
| D | Road maintenance | 0/1 knapsack **DP** | **Maintenance** |
| E | Traffic signals | **Greedy** proportional green-time allocation | **Signals** |

### Bonus features

| # | Bonus | What it adds |
|---|---|---|
| 1 | **AI Tools & Technologies** | A `RandomForestRegressor` trained on the temporal traffic dataset forecasts vehicles/hour for any of the 24 hours and recolors the map by predicted V/C ratio. |
| 2 | **Enhanced Visualization** | Side-by-side **Dijkstra-vs-A\* race animation** that pulses every node expansion and reveals the final routes. |
| 3 | **Deployment & Engineering** | First-class **Dockerfile** and `requirements.txt` so the app runs identically on any machine. |
| 4 | **README + GitHub-ready** | This file. |

## Quick start

### Local (Python)

```bash
cd flask_app
pip install -r requirements.txt
python app.py
# open http://localhost:5000
```

### Train the ML model from a CSV (standalone)

The traffic forecaster ships as a self-contained CLI you can run **without**
starting Flask. Provide any CSV that follows the schema below and it will
train a `RandomForestRegressor`, print full metrics, and persist the bundle
to `flask_app/models/traffic_rf.joblib`. The Flask app then loads it from
disk on first prediction (no in-process training needed).

```bash
cd flask_app
# 1. (optional) regenerate the bundled CSV from data.py
python export_traffic_csv.py

# 2. train with defaults
python train_model.py

# 3. or override hyper-parameters / paths
python train_model.py \
    --data    data/traffic_data.csv \
    --output  models/traffic_rf.joblib \
    --n-estimators 400 \
    --max-depth 12 \
    --test-size 0.25
```

**CSV schema** (header row required):

```
road_id, from_node, to_node, period, hour, distance_km, capacity,
mean_endpoint_population, is_existing, vehicles_per_hour
```

The script writes a sidecar `…metrics.json` next to the model bundle so the
training run is auditable.

### Docker

```bash
docker build -t cairo-transport .
docker run --rm -p 5000:5000 cairo-transport
# open http://localhost:5000
```

## Project layout

```
.
├── Dockerfile                  # Container build
├── .dockerignore
├── README.md
└── flask_app/
    ├── app.py                  # Flask routes (REST API)
    ├── algorithms.py           # MST, Dijkstra, A*, DP, Greedy
    ├── ml_predictor.py         # Random Forest traffic forecaster (Bonus)
    ├── train_model.py          # Standalone CLI: trains model from any CSV
    ├── export_traffic_csv.py   # Helper: dumps data.py into the expected CSV
    ├── data.py                 # Provided Cairo dataset
    ├── data/
    │   └── traffic_data.csv    # Default training set
    ├── models/
    │   ├── traffic_rf.joblib   # Saved model bundle (loaded at runtime)
    │   └── traffic_rf.metrics.json
    ├── requirements.txt
    ├── templates/index.html    # UI shell
    └── static/
        ├── css/style.css
        └── js/app.js           # Map + tabs + race animation + ML
```

## REST API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/network` | Nodes, edges, metro lines, bus routes |
| GET | `/api/mst` | Kruskal MST |
| GET | `/api/route/dijkstra?source=&target=&period=` | Dijkstra (km or time) |
| GET | `/api/route/astar?source=&target=&period=&emergency=` | A\* search |
| GET | `/api/route/compare?source=&target=&period=` | All three side-by-side |
| GET | `/api/route/race?source=&target=&period=` | Visited-node sequences for the race animation |
| GET | `/api/emergency?source=&period=&target?` | Emergency dispatch with signal preemption |
| GET | `/api/transit/schedule?total_vehicles=` | DP transit allocation |
| GET | `/api/maintenance?budget=` | DP road maintenance |
| GET | `/api/signals?period=` | Greedy signal optimization |
| GET | `/api/ml/train` | Train the Random Forest forecaster |
| GET | `/api/ml/predict?hour=` | Predict per-road congestion at a given hour |
| GET | `/api/ml/profile?a=&b=` | 24-hour profile for a single road |
| GET | `/api/healthz` | Liveness probe |

## Algorithms — complexity reference

| Function | Time | Space |
|---|---|---|
| `kruskal_mst` | `O(E log E)` | `O(V)` |
| `dijkstra` | `O((V+E) log V)` | `O(V)` |
| `a_star` | `O((V+E) log V)` (with admissible heuristic) | `O(V)` |
| `dp_transit_schedule` | `O(L · V)` (lines × vehicles) | `O(V)` |
| `dp_road_maintenance` | `O(R · B)` (roads × budget) | `O(B)` |
| `greedy_signal_optimization` | `O(E)` | `O(V)` |
| `greedy_emergency_preemption` | `O((V+E) log V)` for A\* + `O(P)` sweep | `O(V)` |
| ML forecast (RF, 200 trees, depth 8) | `O(T · n · log n)` train, `O(T · log n)` infer | `O(T · n)` |

## Data caveats

- The provided road list contains no roads to facilities **F3** (Cairo
  University), **F4** (Al-Azhar University), **F5** (Egyptian Museum),
  **F6** (Cairo International Stadium), **F9** (Qasr El Aini Hospital), or
  **F10** (Maadi Military Hospital). The MST therefore reports 7 connected
  components, and the emergency router falls back to the road-connected node
  closest to a hospital with a clear UI note.
- All travel times use the BPR formula `t = t₀·(1 + 0.15·(V/C)⁴)` with a
  free-flow speed of 60 km/h.

