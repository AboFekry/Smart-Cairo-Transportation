"""
Integration tests for the Cairo Flask REST API.
Uses Flask's test client — no real server needed.

Run from flask_app/:
    pytest tests/ -v
"""
from __future__ import annotations

import sys
import os
import json

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app as flask_app_module


@pytest.fixture(scope="module")
def client():
    flask_app_module.app.config["TESTING"] = True
    with flask_app_module.app.test_client() as c:
        yield c


# ============================================================================
# Health
# ============================================================================
class TestHealth:
    def test_healthz_200(self, client):
        r = client.get("/api/healthz")
        assert r.status_code == 200

    def test_healthz_json(self, client):
        r = client.get("/api/healthz")
        data = r.get_json()
        assert data["status"] == "ok"


# ============================================================================
# Network
# ============================================================================
class TestNetwork:
    def test_200(self, client):
        assert client.get("/api/network").status_code == 200

    def test_has_nodes_and_edges(self, client):
        data = client.get("/api/network").get_json()
        assert len(data["nodes"]) == 25   # 15 neighbourhoods + 10 facilities
        assert len(data["edges"]) > 0

    def test_has_metro_and_bus(self, client):
        data = client.get("/api/network").get_json()
        assert "metro_lines" in data
        assert "bus_routes" in data

    def test_node_has_required_fields(self, client):
        nodes = client.get("/api/network").get_json()["nodes"]
        for node in nodes:
            assert "id" in node
            # coordinates stored as x (lon) and y (lat)
            assert "x" in node and "y" in node

    def test_index_page_renders(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert b"Cairo" in r.data


# ============================================================================
# MST
# ============================================================================
class TestMST:
    def test_200(self, client):
        assert client.get("/api/mst").status_code == 200

    def test_returns_edges(self, client):
        data = client.get("/api/mst").get_json()
        assert "edges" in data
        assert len(data["edges"]) > 0

    def test_complexity_field(self, client):
        data = client.get("/api/mst").get_json()
        assert "complexity" in data

    def test_components_field(self, client):
        data = client.get("/api/mst").get_json()
        assert "components" in data
        assert data["components"] >= 1


# ============================================================================
# Dijkstra
# ============================================================================
class TestDijkstraAPI:
    def test_missing_params_returns_400(self, client):
        r = client.get("/api/route/dijkstra")
        assert r.status_code == 400

    def test_valid_route(self, client):
        r = client.get("/api/route/dijkstra?source=1&target=3")
        assert r.status_code == 200
        data = r.get_json()
        assert data["path"][0] == "1"
        assert data["path"][-1] == "3"

    def test_period_morning(self, client):
        r = client.get("/api/route/dijkstra?source=1&target=8&period=morning")
        assert r.status_code == 200
        assert r.get_json()["path"]

    def test_unreachable_200_empty_path(self, client):
        r = client.get("/api/route/dijkstra?source=1&target=F3")
        assert r.status_code == 200
        assert not r.get_json().get("path")


# ============================================================================
# A*
# ============================================================================
class TestAStarAPI:
    def test_missing_params_returns_400(self, client):
        r = client.get("/api/route/astar")
        assert r.status_code == 400

    def test_valid_route(self, client):
        r = client.get("/api/route/astar?source=1&target=3")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("path")

    def test_emergency_mode(self, client):
        r = client.get("/api/route/astar?source=1&target=3&emergency=true")
        assert r.status_code == 200


# ============================================================================
# Compare / Race
# ============================================================================
class TestCompareRace:
    def test_compare_400_without_params(self, client):
        r = client.get("/api/route/compare")
        assert r.status_code == 400

    def test_compare_has_three_keys(self, client):
        r = client.get("/api/route/compare?source=1&target=8&period=morning")
        assert r.status_code == 200
        data = r.get_json()
        assert "dijkstra_distance" in data
        assert "dijkstra_time" in data
        assert "astar_time" in data

    def test_race_400_without_params(self, client):
        r = client.get("/api/route/race")
        assert r.status_code == 400

    def test_race_has_both_algorithms(self, client):
        r = client.get("/api/route/race?source=1&target=8&period=morning")
        assert r.status_code == 200
        data = r.get_json()
        assert "dijkstra" in data and "astar" in data

    def test_race_visited_order_non_empty(self, client):
        data = client.get(
            "/api/route/race?source=1&target=8&period=morning"
        ).get_json()
        assert len(data["dijkstra"]["visited_order"]) > 0
        assert len(data["astar"]["visited_order"]) > 0


# ============================================================================
# Emergency
# ============================================================================
class TestEmergencyAPI:
    def test_missing_source_returns_400(self, client):
        r = client.get("/api/emergency")
        assert r.status_code == 400

    def test_auto_dispatch_200(self, client):
        r = client.get("/api/emergency?source=1&period=morning")
        assert r.status_code == 200

    def test_explicit_target_200(self, client):
        r = client.get("/api/emergency?source=1&target=F1&period=morning")
        assert r.status_code == 200
        data = r.get_json()
        assert "path" in data
        assert "preempted_signals" in data


# ============================================================================
# Transit / Maintenance / Signals
# ============================================================================
class TestTransitMaintenanceSignals:
    def test_transit_200(self, client):
        r = client.get("/api/transit/schedule?total_vehicles=300")
        assert r.status_code == 200
        assert "plan" in r.get_json()

    def test_maintenance_200(self, client):
        r = client.get("/api/maintenance?budget=500")
        assert r.status_code == 200
        assert "chosen" in r.get_json()

    def test_signals_200(self, client):
        for period in ("morning", "afternoon", "evening", "night"):
            r = client.get(f"/api/signals?period={period}")
            assert r.status_code == 200


# ============================================================================
# ML endpoints
# ============================================================================
class TestMLEndpoints:
    def test_train_200(self, client):
        r = client.get("/api/ml/train")
        assert r.status_code == 200

    def test_train_has_r2(self, client):
        data = client.get("/api/ml/train").get_json()
        assert "test_r2" in data
        assert data["test_r2"] > 0.8, "R² below expected threshold"

    def test_predict_bad_hour_returns_400(self, client):
        r = client.get("/api/ml/predict?hour=999")
        assert r.status_code == 400

    def test_predict_valid_hour(self, client):
        r = client.get("/api/ml/predict?hour=8")
        assert r.status_code == 200
        data = r.get_json()
        assert "roads" in data
        assert len(data["roads"]) > 0

    def test_predict_road_has_vc_ratio(self, client):
        data = client.get("/api/ml/predict?hour=8").get_json()
        road = data["roads"][0]
        assert "vc_ratio" in road
        assert "predicted_vehicles_per_hour" in road

    def test_profile_missing_params_400(self, client):
        r = client.get("/api/ml/profile")
        assert r.status_code == 400

    def test_profile_valid(self, client):
        r = client.get("/api/ml/profile?a=1&b=3")
        assert r.status_code == 200
        data = r.get_json()
        assert "hourly" in data
        assert len(data["hourly"]) == 24
