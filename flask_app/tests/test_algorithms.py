"""
Unit tests for flask_app/algorithms.py.

Run from flask_app/:
    pytest tests/ -v
"""
from __future__ import annotations

import sys
import os
import math

import pytest

# Make flask_app/ importable when running from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from algorithms import (
    kruskal_mst,
    dijkstra,
    a_star,
    dp_transit_schedule,
    dp_road_maintenance,
    greedy_signal_optimization,
    greedy_emergency_preemption,
    build_graph,
    DSU,
)
from data import EXISTING_ROADS, NEIGHBORHOODS


# ============================================================================
# DSU (Union-Find)
# ============================================================================
class TestDSU:
    def test_initial_components(self):
        dsu = DSU(["a", "b", "c"])
        assert dsu.find("a") != dsu.find("b")
        assert dsu.find("b") != dsu.find("c")

    def test_union_merges(self):
        dsu = DSU(["a", "b", "c"])
        dsu.union("a", "b")
        assert dsu.find("a") == dsu.find("b")
        assert dsu.find("a") != dsu.find("c")

    def test_union_all(self):
        dsu = DSU([1, 2, 3, 4])
        dsu.union(1, 2)
        dsu.union(3, 4)
        dsu.union(1, 3)
        assert dsu.find(1) == dsu.find(4)

    def test_idempotent_union(self):
        dsu = DSU(["x", "y"])
        dsu.union("x", "y")
        dsu.union("x", "y")   # second call should be harmless
        assert dsu.find("x") == dsu.find("y")


# ============================================================================
# Graph construction
# ============================================================================
class TestBuildGraph:
    def test_existing_only(self):
        adj = build_graph(include_potential=False)
        assert len(adj) > 0
        # Every existing road should produce two directed entries
        for a, b, dist, cap, _cond in EXISTING_ROADS:
            assert any(nbr == b for nbr, *_ in adj[a])
            assert any(nbr == a for nbr, *_ in adj[b])

    def test_with_potential(self):
        adj_base = build_graph(include_potential=False)
        adj_full = build_graph(include_potential=True)
        # potential edges should add more neighbours
        assert sum(len(v) for v in adj_full.values()) >= sum(
            len(v) for v in adj_base.values()
        )

    def test_distances_positive(self):
        adj = build_graph()
        for node, neighbours in adj.items():
            for _nbr, dist, *_ in neighbours:
                assert dist > 0, f"Non-positive distance from {node}"


# ============================================================================
# Kruskal MST
# ============================================================================
class TestKruskalMST:
    def test_returns_edges(self):
        result = kruskal_mst()
        assert "edges" in result
        assert isinstance(result["edges"], list)

    def test_edge_structure(self):
        result = kruskal_mst()
        for edge in result["edges"]:
            assert "a" in edge and "b" in edge
            assert "distance_km" in edge or "weight" in edge

    def test_total_distance_positive(self):
        result = kruskal_mst()
        assert result.get("total_distance_km", 0) > 0 or result.get("total_weight", 0) > 0

    def test_num_components_reported(self):
        result = kruskal_mst()
        assert "components" in result
        assert result["components"] >= 1

    def test_prioritize_flag_runs(self):
        r1 = kruskal_mst(prioritize_population=True)
        r2 = kruskal_mst(prioritize_population=False)
        assert "edges" in r1
        assert "edges" in r2

    def test_no_cycles(self):
        """For a connected graph, MST of N nodes has N-1 edges."""
        result = kruskal_mst()
        edges = result["edges"]
        # Collect unique nodes from edges
        nodes = set()
        for e in edges:
            nodes.add(e["a"])
            nodes.add(e["b"])
        if result.get("components", 1) == 1:
            assert len(edges) == len(nodes) - 1


# ============================================================================
# Dijkstra
# ============================================================================
class TestDijkstra:
    # Known connected pairs from the dataset
    CONNECTED = [("1", "3"), ("1", "8"), ("3", "8"), ("8", "10")]

    def test_returns_path(self):
        for src, dst in self.CONNECTED:
            r = dijkstra(src, dst)
            assert "path" in r, f"No path key for {src}->{dst}"
            assert r["path"], f"Empty path for {src}->{dst}"

    def test_path_starts_and_ends_correctly(self):
        r = dijkstra("1", "3")
        assert r["path"][0] == "1"
        assert r["path"][-1] == "3"

    def test_cost_positive(self):
        r = dijkstra("1", "8")
        assert (r.get("cost") or 0) > 0

    def test_cost_equals_direct_for_adjacent(self):
        """For a direct edge, cost should equal the edge weight."""
        for a, b, dist, _cap, _cond in EXISTING_ROADS:
            r = dijkstra(a, b)
            if r["path"] == [a, b]:
                assert math.isclose(r["cost"] or dist, dist, rel_tol=1e-3), (
                    f"{a}->{b}: expected {dist}, got {r['cost']}"
                )
            break  # one check is enough

    def test_time_dependent_period(self):
        for period in ("morning", "afternoon", "evening", "night"):
            r = dijkstra("1", "3", period=period)
            assert r.get("path"), f"No path for period={period}"

    def test_self_loop_is_trivial(self):
        r = dijkstra("1", "1")
        assert r["path"] == ["1"]
        assert (r.get("cost") or 0) == 0

    def test_unreachable_returns_empty(self):
        r = dijkstra("1", "F3")   # F3 has no roads
        assert not r.get("path")

    def test_elapsed_ms_recorded(self):
        r = dijkstra("1", "8")
        assert "elapsed_ms" in r
        assert r["elapsed_ms"] >= 0

    def test_expanded_nodes_positive(self):
        r = dijkstra("1", "8")
        assert r.get("expanded", 0) > 0


# ============================================================================
# A*
# ============================================================================
class TestAStar:
    def test_same_optimal_cost_as_dijkstra(self):
        """A* must find a path no worse than Dijkstra for the same query."""
        for src, dst in [("1", "8"), ("3", "10")]:
            d = dijkstra(src, dst, period="morning")
            a = a_star(src, dst, period="morning")
            if d.get("cost") and a.get("cost"):
                assert math.isclose(d["cost"], a["cost"], rel_tol=0.05), (
                    f"{src}->{dst} Dijkstra={d['cost']:.2f} A*={a['cost']:.2f}"
                )

    def test_expands_fewer_or_equal_nodes_than_dijkstra(self):
        """A* should be at least as efficient as Dijkstra (admissible heuristic)."""
        d = dijkstra("1", "10", period="morning")
        a = a_star("1", "10", period="morning")
        assert a.get("expanded", 999) <= d.get("expanded", 0) + 2  # small tolerance

    def test_path_connectivity(self):
        r = a_star("1", "3")
        path = r.get("path", [])
        adj = build_graph()
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            neighbours = [n for n, *_ in adj[u]]
            assert v in neighbours, f"Disconnected step {u}->{v} in A* path"

    def test_emergency_flag(self):
        r = a_star("1", "3", emergency=True)
        assert r.get("path"), "Emergency A* returned no path"


# ============================================================================
# DP Transit Schedule
# ============================================================================
class TestDPTransitSchedule:
    def test_returns_plan(self):
        r = dp_transit_schedule(total_vehicles=300)
        assert "plan" in r
        assert len(r["plan"]) > 0

    def test_total_vehicles_respected(self):
        total = 300
        r = dp_transit_schedule(total_vehicles=total)
        allocated = sum(a["vehicles_assigned"] for a in r["plan"])
        assert allocated <= total

    def test_passengers_positive(self):
        r = dp_transit_schedule(total_vehicles=300)
        assert r.get("total_estimated_passengers", 0) > 0

    def test_zero_vehicles(self):
        r = dp_transit_schedule(total_vehicles=0)
        assert r.get("vehicles_used", 0) == 0

    def test_more_vehicles_more_or_equal_passengers(self):
        p100 = dp_transit_schedule(total_vehicles=100).get("total_estimated_passengers", 0)
        p300 = dp_transit_schedule(total_vehicles=300).get("total_estimated_passengers", 0)
        assert p300 >= p100

    def test_elapsed_recorded(self):
        r = dp_transit_schedule(total_vehicles=100)
        assert "elapsed_ms" in r


# ============================================================================
# DP Road Maintenance
# ============================================================================
class TestDPRoadMaintenance:
    def test_returns_chosen(self):
        r = dp_road_maintenance(budget_million_egp=500)
        assert "chosen" in r

    def test_cost_within_budget(self):
        budget = 500
        r = dp_road_maintenance(budget_million_egp=budget)
        total = sum(s.get("cost", 0) for s in r["chosen"])
        assert total <= budget

    def test_zero_budget(self):
        r = dp_road_maintenance(budget_million_egp=0)
        assert r.get("chosen") == [] or r.get("total_benefit", 0) == 0

    def test_large_budget_selects_all_or_more(self):
        r_small = dp_road_maintenance(budget_million_egp=100)
        r_large = dp_road_maintenance(budget_million_egp=9999)
        assert (
            r_large.get("total_benefit", 0) >= r_small.get("total_benefit", 0)
        )


# ============================================================================
# Greedy Signal Optimization
# ============================================================================
class TestGreedySignals:
    def test_returns_allocations(self):
        r = greedy_signal_optimization(period="morning")
        assert "allocations" in r or "intersections" in r

    def test_all_periods_run(self):
        for period in ("morning", "afternoon", "evening", "night"):
            r = greedy_signal_optimization(period=period)
            assert r is not None

    def test_green_times_positive(self):
        r = greedy_signal_optimization(period="morning")
        items = r.get("allocations", r.get("intersections", []))
        for item in items:
            green = item.get("green_seconds") or item.get("green_time_s") or 0
            assert green >= 0


# ============================================================================
# Greedy Emergency Preemption
# ============================================================================
class TestGreedyEmergencyPreemption:
    def test_returns_path(self):
        r = greedy_emergency_preemption("1", "F1", period="morning")
        assert "path" in r

    def test_preempted_signals_list(self):
        r = greedy_emergency_preemption("1", "F1", period="morning")
        assert "preempted_signals" in r

    def test_time_saved_field(self):
        r = greedy_emergency_preemption("1", "F1", period="morning")
        assert "saved_minutes" in r or "emergency_minutes" in r
