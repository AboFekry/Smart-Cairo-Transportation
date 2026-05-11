"""
Flask web server — Cairo Smart Transportation System.

All routes return JSON.  Error responses have the shape:
    {"error": "<human-readable message>", "code": <http-status>}
"""
from __future__ import annotations

import logging
import math
import os
import time
from typing import Any

from flask import Flask, jsonify, render_template, request

import config
from data import (
    NEIGHBORHOODS,
    FACILITIES,
    EXISTING_ROADS,
    SYNTHETIC_EDGES,
    POTENTIAL_ROADS,
    TRAFFIC_FLOW,
    METRO_LINES,
    BUS_ROUTES,
    TRANSIT_DEMAND,
    all_nodes,
    road_key,
    critical_facility_ids,
    medical_facility_ids,
)
from algorithms import (
    kruskal_mst,
    dijkstra,
    a_star,
    dp_transit_schedule,
    dp_road_maintenance,
    greedy_signal_optimization,
    greedy_emergency_preemption,
    nearest_medical_route,
)
import ml_predictor

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format=config.LOG_FORMAT,
    datefmt=config.LOG_DATE_FORMAT,
)
logger = logging.getLogger("cairo_transport")

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _err(message: str, status: int = 400):
    """Structured error response."""
    logger.warning("API error %d: %s", status, message)
    return jsonify({"error": message, "code": status}), status


def _sanitize(obj: Any) -> Any:
    """Replace inf / NaN with None so jsonify produces valid JSON."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isinf(obj) or math.isnan(obj)):
        return None
    return obj


def _require_params(*names: str):
    """Return (values_dict, error_response_or_None)."""
    missing = [n for n in names if not request.args.get(n)]
    if missing:
        return None, _err(f"Missing required query parameter(s): {', '.join(missing)}")
    return {n: request.args.get(n) for n in names}, None


@app.after_request
def _no_cache(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp


@app.errorhandler(404)
def _not_found(exc):
    return _err("Endpoint not found", 404)


@app.errorhandler(405)
def _method_not_allowed(exc):
    return _err("Method not allowed", 405)


@app.errorhandler(500)
def _internal(exc):
    logger.exception("Unhandled server error")
    return _err("Internal server error", 500)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Network data
# ---------------------------------------------------------------------------
@app.route("/api/network")
def api_network():
    """Return all nodes + edges (existing & potential) for the map."""
    nodes = all_nodes()
    crit = critical_facility_ids()
    med  = medical_facility_ids()
    for n in nodes:
        n["critical"] = n["id"] in crit
        n["medical"]  = n["id"] in med

    edges = []
    for e in EXISTING_ROADS + SYNTHETIC_EDGES:
        key   = road_key(e["from"], e["to"])
        flows = TRAFFIC_FLOW.get(key)
        edges.append({
            "a": e["from"], "b": e["to"], "distance_km": e["distance_km"], "capacity": e["capacity"],
            "condition": e["condition"], "kind": "existing", "synthetic": e.get("synthetic", False),
            "morning":   flows[0] if flows else None,
            "afternoon": flows[1] if flows else None,
            "evening":   flows[2] if flows else None,
            "night":     flows[3] if flows else None,
        })
    for a, b, dist, cap, cost in POTENTIAL_ROADS:
        edges.append({
            "a": a, "b": b, "distance_km": dist, "capacity": cap,
            "cost_million_egp": cost, "kind": "potential",
        })

    logger.info("GET /api/network  nodes=%d edges=%d", len(nodes), len(edges))
    return jsonify({
        "nodes":          nodes,
        "edges":          edges,
        "metro_lines":    METRO_LINES,
        "bus_routes":     BUS_ROUTES,
        "transit_demand": [
            {"from": a, "to": b, "passengers": p} for a, b, p in TRANSIT_DEMAND
        ],
    })


# ---------------------------------------------------------------------------
# Algorithm endpoints
# ---------------------------------------------------------------------------
@app.route("/api/mst")
def api_mst():
    prioritize = request.args.get("prioritize_population", "true").lower() == "true"
    critical   = request.args.get("ensure_critical_connectivity", "true").lower() == "true"
    t0 = time.perf_counter()
    result = kruskal_mst(prioritize, critical)
    logger.info("MST  edges=%d components=%d  %.1f ms",
                len(result.get("edges", [])), result.get("components", 0),
                (time.perf_counter() - t0) * 1000)
    return jsonify(_sanitize(result))


@app.route("/api/route/dijkstra")
def api_dijkstra():
    params, err = _require_params("source", "target")
    if err:
        return err
    period = request.args.get("period") or None
    result = dijkstra(params["source"], params["target"], period=period)
    logger.info("Dijkstra %s->%s period=%s  path_len=%d  %.1f ms",
                params["source"], params["target"], period,
                len(result.get("path") or []), result.get("elapsed_ms", 0))
    return jsonify(_sanitize(result))


@app.route("/api/route/astar")
def api_astar():
    params, err = _require_params("source", "target")
    if err:
        return err
    period    = request.args.get("period") or None
    emergency = request.args.get("emergency", "false").lower() == "true"
    result = a_star(params["source"], params["target"],
                    period=period, emergency=emergency)
    logger.info("A*   %s->%s period=%s emergency=%s  expanded=%d  %.1f ms",
                params["source"], params["target"], period, emergency,
                result.get("expanded", 0), result.get("elapsed_ms", 0))
    return jsonify(_sanitize(result))


@app.route("/api/route/compare")
def api_compare():
    params, err = _require_params("source", "target")
    if err:
        return err
    period = request.args.get("period", "morning")
    src, dst = params["source"], params["target"]
    return jsonify(_sanitize({
        "dijkstra_distance": dijkstra(src, dst),
        "dijkstra_time":     dijkstra(src, dst, period=period),
        "astar_time":        a_star(src, dst, period=period),
    }))


@app.route("/api/route/race")
def api_race():
    """Both visited-node sequences for the side-by-side race animation."""
    params, err = _require_params("source", "target")
    if err:
        return err
    period = request.args.get("period", "morning")
    src, dst = params["source"], params["target"]
    d = dijkstra(src, dst, period=period)
    a = a_star(src, dst, period=period)
    logger.info("Race %s->%s  Dijkstra=%d nodes  A*=%d nodes",
                src, dst, d.get("expanded", 0), a.get("expanded", 0))
    return jsonify(_sanitize({
        "dijkstra": {
            "visited_order": d.get("visited_order", []),
            "path":          d.get("path", []),
            "cost":          d.get("cost"),
            "expanded":      d.get("expanded", 0),
            "elapsed_ms":    d.get("elapsed_ms", 0),
            "unit":          d.get("unit"),
            "prev":          d.get("prev", {}),
        },
        "astar": {
            "visited_order": a.get("visited_order", []),
            "path":          a.get("path", []),
            "cost":          a.get("cost"),
            "expanded":      a.get("expanded", 0),
            "elapsed_ms":    a.get("elapsed_ms", 0),
            "unit":          a.get("unit"),
            "prev":          a.get("prev", {}),
        },
    }))


@app.route("/api/emergency")
def api_emergency():
    """Route an emergency vehicle to the nearest medical facility (or target)."""
    params, err = _require_params("source")
    if err:
        return err
    src    = params["source"]
    dst    = request.args.get("target")
    period = request.args.get("period", "morning")

    if dst:
        result = greedy_emergency_preemption(src, dst, period=period)
        result["facility_id"] = dst
    else:
        nearest = nearest_medical_route(src, period=period)
        if not nearest.get("path"):
            return jsonify(_sanitize(nearest))
        target_id = nearest.get("dispatch_target") or nearest["facility_id"]
        result = greedy_emergency_preemption(src, target_id, period=period)
        result["facility_id"]     = nearest["facility_id"]
        result["dispatch_target"] = target_id
        if nearest.get("note"):
            result["note"] = nearest["note"]

    logger.info("Emergency %s->%s  signals=%d preempted  %.1f ms",
                src, result.get("facility_id"), len(result.get("preempted_signals", [])),
                result.get("elapsed_ms", 0))
    return jsonify(_sanitize(result))


@app.route("/api/transit/schedule")
def api_transit_schedule():
    try:
        total = int(request.args.get("total_vehicles", config.DEFAULT_TOTAL_VEHICLES))
        if total < 0:
            raise ValueError
    except ValueError:
        return _err("total_vehicles must be a non-negative integer")
    result = dp_transit_schedule(total_vehicles=total)
    logger.info("Transit schedule  vehicles=%d  utility=%.0f  %.1f ms",
                total, result.get("total_utility", 0), result.get("elapsed_ms", 0))
    return jsonify(_sanitize(result))


@app.route("/api/maintenance")
def api_maintenance():
    try:
        budget = int(request.args.get("budget", config.DEFAULT_MAINTENANCE_BUDGET_MEPP))
        if budget < 0:
            raise ValueError
    except ValueError:
        return _err("budget must be a non-negative integer (million EGP)")
    result = dp_road_maintenance(budget_million_egp=budget)
    logger.info("Maintenance  budget=%dM EGP  roads=%d selected  %.1f ms",
                budget, len(result.get("selected_roads", [])),
                result.get("elapsed_ms", 0))
    return jsonify(_sanitize(result))


@app.route("/api/signals")
def api_signals():
    period = request.args.get("period", "morning")
    if period not in config.PERIOD_HOURS:
        return _err(f"period must be one of: {', '.join(config.PERIOD_HOURS)}")
    result = greedy_signal_optimization(period=period)
    return jsonify(_sanitize(result))


# ---------------------------------------------------------------------------
# ML — traffic forecasting
# ---------------------------------------------------------------------------
@app.route("/api/ml/train")
def api_ml_train():
    """Load or (re)train the traffic-prediction model."""
    force = request.args.get("force", "false").lower() == "true"
    result = ml_predictor.train(force=force)
    logger.info("ML train  force=%s  R²=%.4f  MAE=%.1f veh/h",
                force, result.get("test_r2", 0),
                result.get("test_mae_vehicles_per_hour", 0))
    return jsonify(_sanitize(result))


@app.route("/api/ml/predict")
def api_ml_predict():
    """Predict vehicles/hour + V/C for every road at the given hour."""
    try:
        hour = float(request.args.get("hour", "8"))
    except (TypeError, ValueError):
        return _err("hour must be a number 0–23")
    if not (0 <= hour <= 23):
        return _err("hour must be between 0 and 23")
    return jsonify(_sanitize(ml_predictor.predict_for_hour(hour)))


@app.route("/api/ml/profile")
def api_ml_profile():
    """24-hour predicted volume profile for a single road."""
    params, err = _require_params("a", "b")
    if err:
        return err
    return jsonify(_sanitize(ml_predictor.hourly_profile(params["a"], params["b"])))


@app.route("/api/ml/predict_custom")
def api_ml_predict_custom():
    """Predict traffic for custom user-provided features."""
    params, err = _require_params("hour", "distance", "capacity", "pop", "existing")
    if err:
        return err
    try:
        hour = float(params["hour"])
        distance = float(params["distance"])
        capacity = float(params["capacity"])
        pop = float(params["pop"])
        existing = int(params["existing"])
    except ValueError:
        return _err("Parameters must be numeric.")
    
    if not (0 <= hour <= 23):
        return _err("hour must be between 0 and 23")
        
    result = ml_predictor.predict_custom(hour, distance, capacity, pop, existing)
    return jsonify(_sanitize(result))


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.route("/api/healthz")
def healthz():
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting Cairo Smart Transportation server on port %d", config.PORT)
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
