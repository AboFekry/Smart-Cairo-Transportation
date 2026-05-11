"""
Pytest configuration and shared fixtures for algorithm tests.
"""
import pytest
from collections import defaultdict


@pytest.fixture
def small_graph():
    """
    Small test graph: 6 nodes (A-F), 8 edges.
    Returns adjacency list: node -> list of (neighbor, distance_km, capacity, kind, meta)
    """
    adj = defaultdict(list)
    # Edges: A-B:1, A-C:4, B-C:2, B-D:5, C-D:1, C-E:3, D-E:1, E-F:2
    edges = [
        ("A", "B", 1, 1000, "existing", {"condition": 8}),
        ("A", "C", 4, 1000, "existing", {"condition": 8}),
        ("B", "C", 2, 1000, "existing", {"condition": 8}),
        ("B", "D", 5, 1000, "existing", {"condition": 8}),
        ("C", "D", 1, 1000, "existing", {"condition": 8}),
        ("C", "E", 3, 1000, "existing", {"condition": 8}),
        ("D", "E", 1, 1000, "existing", {"condition": 8}),
        ("E", "F", 2, 1000, "existing", {"condition": 8}),
    ]
    for a, b, dist, cap, kind, meta in edges:
        adj[a].append((b, dist, cap, kind, meta))
        adj[b].append((a, dist, cap, kind, meta))
    return adj


@pytest.fixture
def small_nodes():
    """Node coordinates for heuristic calculations."""
    return {
        "A": {"x": 0, "y": 0},
        "B": {"x": 1, "y": 0},
        "C": {"x": 2, "y": 1},
        "D": {"x": 3, "y": 0},
        "E": {"x": 4, "y": 1},
        "F": {"x": 5, "y": 1},
    }


@pytest.fixture
def small_metro_lines():
    """Small metro lines for transit tests."""
    return [
        {"id": "M1", "name": "Line 1", "daily_passengers": 100000},
        {"id": "M2", "name": "Line 2", "daily_passengers": 80000},
    ]


@pytest.fixture
def small_bus_routes():
    """Small bus routes for transit tests."""
    return [
        {"id": "B1", "stops": ["A", "B"], "buses": 10, "daily_passengers": 5000},
        {"id": "B2", "stops": ["C", "D"], "buses": 8, "daily_passengers": 4000},
    ]


@pytest.fixture
def small_roads():
    """Small roads for maintenance tests."""
    return [
        ("A", "B", 1, 1000, 7),  # dist, cap, cond
        ("B", "C", 2, 1000, 6),
        ("C", "D", 1, 1000, 8),
    ]


@pytest.fixture
def small_traffic_flow():
    """Traffic flow for roads."""
    return {
        "A-B": (800, 600, 700, 300),
        "B-C": (900, 700, 800, 400),
        "C-D": (1000, 800, 900, 500),
    }