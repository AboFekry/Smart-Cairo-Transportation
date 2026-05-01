"""
Export the provided Cairo traffic dataset to a CSV file that the
standalone training script (`train_model.py`) consumes.

Usage:
    python export_traffic_csv.py            # writes data/traffic_data.csv
    python export_traffic_csv.py --out X.csv
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

from data import EXISTING_ROADS, NEIGHBORHOODS, FACILITIES, TRAFFIC_FLOW, road_key

PERIOD_HOURS = {"morning": 8, "afternoon": 14, "evening": 18, "night": 2}

# Build the same population lookup the model uses
_NODE_POP: dict[str, int] = {n["id"]: n["population"] for n in NEIGHBORHOODS}
for f in FACILITIES:
    _NODE_POP[f["id"]] = {"Airport": 80000, "Transit Hub": 120000}.get(f["type"], 30000)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/traffic_data.csv",
                        help="Output CSV path (default: data/traffic_data.csv)")
    args = parser.parse_args(argv)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    rows = 0
    with open(args.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "road_id", "from_node", "to_node", "period", "hour",
            "distance_km", "capacity", "mean_endpoint_population",
            "is_existing", "vehicles_per_hour",
        ])
        for a, b, dist, cap, _cond in EXISTING_ROADS:
            flow = TRAFFIC_FLOW.get(road_key(a, b))
            if flow is None:
                continue
            mean_pop = (_NODE_POP.get(a, 30000) + _NODE_POP.get(b, 30000)) / 2.0
            for period, vph in zip(
                ["morning", "afternoon", "evening", "night"], flow
            ):
                w.writerow([
                    f"{a}-{b}", a, b, period, PERIOD_HOURS[period],
                    dist, cap, int(mean_pop), 1, vph,
                ])
                rows += 1

    print(f"Wrote {rows} rows to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
