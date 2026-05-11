"""
Comprehensive tests for algorithms.py using a small deterministic test graph.
"""
import pytest
from collections import defaultdict

from algorithms import (
    kruskal_mst,
    dijkstra,
    a_star,
    dp_transit_schedule,
    dp_road_maintenance,
)
from data import EXISTING_ROADS, SYNTHETIC_EDGES, POTENTIAL_ROADS, TRAFFIC_FLOW, METRO_LINES, BUS_ROUTES, node_index


class TestKruskalMST:
    def test_valid_spanning_tree(self, monkeypatch, small_roads):
        """Verify MST has V-1 edges, connects all nodes, no cycles."""
        # Patch algorithms module
        monkeypatch.setattr("algorithms.EXISTING_ROADS", small_roads)
        monkeypatch.setattr("algorithms.SYNTHETIC_EDGES", [])
        monkeypatch.setattr("algorithms.POTENTIAL_ROADS", [])
        monkeypatch.setattr("algorithms.node_index", lambda: {
            "A": {"population": 100},
            "B": {"population": 200},
            "C": {"population": 150},
            "D": {"population": 100},
        })

        result = kruskal_mst(prioritize_population=False, ensure_critical_connectivity=False)
        assert result["node_count"] == 4
        assert result["edge_count"] == 3  # V-1
        assert result["connected"] is True
        assert len(result["isolated_nodes"]) == 0
        # Total weight should be minimal: edges A-B:1, B-C:2, C-D:1 = 4
        assert result["total_distance_km"] == 4.0


class TestDijkstra:
    def test_shortest_distances(self, monkeypatch, small_roads):
        """Verify shortest distances match hand-computed values."""
        monkeypatch.setattr("algorithms.EXISTING_ROADS", small_roads)
        monkeypatch.setattr("algorithms.SYNTHETIC_EDGES", [])
        monkeypatch.setattr("algorithms.POTENTIAL_ROADS", [])

        result = dijkstra("A")
        expected_distances = {
            "A": 0,
            "B": 1,
            "C": 3,  # A-B-C: 1+2=3, A-C:4
            "D": 4,  # A-B-C-D:1+2+1=4
        }
        for node, dist in expected_distances.items():
            assert result["distances"][node] == dist

    def test_no_path(self, monkeypatch, small_roads):
        """Verify no path returns inf."""
        monkeypatch.setattr("algorithms.EXISTING_ROADS", small_roads)
        monkeypatch.setattr("algorithms.SYNTHETIC_EDGES", [])
        monkeypatch.setattr("algorithms.POTENTIAL_ROADS", [])

        result = dijkstra("A", "Z")  # Non-existent node
        assert result["cost"] == float("inf")


class TestAStar:
    def test_same_path_as_dijkstra(self, monkeypatch, small_roads, small_nodes):
        """Verify A* returns same path as Dijkstra with consistent heuristic."""
        monkeypatch.setattr("algorithms.EXISTING_ROADS", small_roads)
        monkeypatch.setattr("algorithms.SYNTHETIC_EDGES", [])
        monkeypatch.setattr("algorithms.POTENTIAL_ROADS", [])
        monkeypatch.setattr("algorithms.node_index", lambda: small_nodes)

        dijkstra_result = dijkstra("A", "D")
        a_star_result = a_star("A", "D")

        assert a_star_result["path"] == dijkstra_result["path"]
        assert a_star_result["cost"] == dijkstra_result["cost"]
        # A* should explore fewer or equal nodes
        assert a_star_result["expanded"] <= len(dijkstra_result["prev"])


class TestDPRoadMaintenance:
    def test_budget_constraint_and_max_benefit(self, monkeypatch, small_roads, small_traffic_flow):
        """Verify knapsack respects budget and maximizes benefit."""
        monkeypatch.setattr("data.EXISTING_ROADS", small_roads)
        monkeypatch.setattr("data.TRAFFIC_FLOW", small_traffic_flow)
        monkeypatch.setattr("algorithms.road_key", lambda a, b: f"{min(a,b)}-{max(a,b)}")

        budget = 10
        result = dp_road_maintenance(budget)

        assert result["total_cost_million_egp"] <= budget
        # With small data, check specific values
        # Roads: A-B cost=1*(11-7)*2=8, benefit=800*(11-7)=3200
        # B-C: 2*(11-6)*2=10, benefit=900*5=4500
        # C-D: 1*(11-8)*2=6, benefit=1000*3=3000
        # Optimal: A-B and C-D: cost=8+6=14>10, so B-C:10<=10, benefit=4500
        assert result["total_benefit"] == 4500
        assert result["total_benefit"] == 4500
        assert result["total_cost_million_egp"] == 10


class TestDPTransitSchedule:
    def test_vehicle_allocation_and_coverage(self, monkeypatch, small_metro_lines, small_nodes):
        """Verify allocation does not exceed vehicles and improves coverage."""
        monkeypatch.setattr("data.METRO_LINES", small_metro_lines)
        monkeypatch.setattr("data.node_index", lambda: small_nodes)

        total_vehicles = 2
        result = dp_transit_schedule(total_vehicles)

        assert result["total_vehicles_used"] <= total_vehicles
        # With small data, check coverage improvement
        # Lines: L1 covers A,B,C; L2 covers C,D
        # With 2 vehicles, can cover both, coverage 100%
        assert result["coverage_percentage"] == 100.0
        assert result["total_vehicles_used"] == 2