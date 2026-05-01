"""
Algorithm implementations for the Cairo Transportation System:
  - Kruskal's MST (with critical-facility constraints)
  - Dijkstra's shortest path
  - A* search (Euclidean / Haversine heuristic)
  - Time-dependent Dijkstra (rush hour aware)
  - DP scheduling for transit vehicles
  - DP resource allocation for road maintenance
  - Greedy traffic-signal optimization
  - Greedy emergency vehicle preemption
"""
from __future__ import annotations

import heapq
import math
import time
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

from data import (
    EXISTING_ROADS,
    POTENTIAL_ROADS,
    TRAFFIC_FLOW,
    NEIGHBORHOODS,
    FACILITIES,
    METRO_LINES,
    BUS_ROUTES,
    node_index,
    critical_facility_ids,
    road_key,
)

# Approx km per degree of lat/long around Cairo (~30°N).
KM_PER_DEG_LAT = 110.574
KM_PER_DEG_LON = 96.486  # 111.32 * cos(30°)


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------
def build_graph(include_potential: bool = False):
    """Adjacency list: node -> list of (neighbor, distance_km, capacity, kind, meta)
    kind in {"existing", "potential"}.
    """
    adj: Dict[str, List[Tuple[str, float, int, str, dict]]] = defaultdict(list)
    for a, b, dist, cap, cond in EXISTING_ROADS:
        adj[a].append((b, dist, cap, "existing", {"condition": cond}))
        adj[b].append((a, dist, cap, "existing", {"condition": cond}))
    if include_potential:
        for a, b, dist, cap, cost in POTENTIAL_ROADS:
            adj[a].append((b, dist, cap, "potential", {"cost_million_egp": cost}))
            adj[b].append((a, dist, cap, "potential", {"cost_million_egp": cost}))
    return adj


# ---------------------------------------------------------------------------
# A. Minimum Spanning Tree — Kruskal's algorithm
# ---------------------------------------------------------------------------
class DSU:
    def __init__(self, items):
        self.parent = {i: i for i in items}
        self.rank = {i: 0 for i in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        return True


def kruskal_mst(prioritize_population: bool = True,
                ensure_critical_connectivity: bool = True):
    """
    Kruskal's MST that designs a cost-efficient road network.

    - Existing roads cost = distance (km) (assumed already-built / cheap).
    - Potential roads cost = construction cost (Million EGP) normalized to a
      comparable scale (cost_million / 50.0).
    - When `prioritize_population` is True, edges connecting high-population
      nodes get a small weight discount so the MST favors them.
    - When `ensure_critical_connectivity` is True, critical-facility edges
      are forced into the spanning tree first (greedy lifting), then
      Kruskal proceeds normally.

    Returns dict with the chosen edges and summary stats.
    """
    nodes = node_index()
    pop = {nid: n.get("population", 0) for nid, n in nodes.items()}
    max_pop = max(pop.values()) if pop else 1
    crit = critical_facility_ids()

    # Build candidate edge list
    edges = []
    for a, b, dist, cap, cond in EXISTING_ROADS:
        w = dist  # km — already-built road
        if prioritize_population:
            pop_score = (pop.get(a, 0) + pop.get(b, 0)) / (2 * max_pop)
            w *= (1.0 - 0.25 * pop_score)  # up to 25% discount
        edges.append({
            "a": a, "b": b, "distance": dist, "capacity": cap,
            "kind": "existing", "weight": w, "cost_million_egp": 0.0,
            "condition": cond,
        })
    for a, b, dist, cap, cost in POTENTIAL_ROADS:
        # Cost-based weight for new construction
        w = dist + cost / 50.0
        if prioritize_population:
            pop_score = (pop.get(a, 0) + pop.get(b, 0)) / (2 * max_pop)
            w *= (1.0 - 0.25 * pop_score)
        edges.append({
            "a": a, "b": b, "distance": dist, "capacity": cap,
            "kind": "potential", "weight": w, "cost_million_egp": float(cost),
            "condition": None,
        })

    edges.sort(key=lambda e: e["weight"])

    dsu = DSU(nodes.keys())
    mst_edges = []
    total_distance = 0.0
    total_cost = 0.0

    t0 = time.perf_counter()

    # 1) Lift critical-facility edges first (greedy modification)
    if ensure_critical_connectivity:
        critical_edges = [e for e in edges
                          if e["a"] in crit or e["b"] in crit]
        critical_edges.sort(key=lambda e: e["weight"])
        for e in critical_edges:
            if dsu.union(e["a"], e["b"]):
                mst_edges.append(e)
                total_distance += e["distance"]
                total_cost += e["cost_million_egp"]

    # 2) Standard Kruskal over the rest
    for e in edges:
        if dsu.union(e["a"], e["b"]):
            mst_edges.append(e)
            total_distance += e["distance"]
            total_cost += e["cost_million_egp"]

    t1 = time.perf_counter()

    # Connectivity check
    roots = {dsu.find(n) for n in nodes}
    components = len(roots)
    connected = (components == 1)
    isolated = [nid for nid in nodes
                if not any(e["a"] == nid or e["b"] == nid for e in mst_edges)]

    return {
        "edges": mst_edges,
        "total_distance_km": round(total_distance, 2),
        "total_construction_cost_million_egp": round(total_cost, 2),
        "edge_count": len(mst_edges),
        "node_count": len(nodes),
        "connected": connected,
        "components": components,
        "isolated_nodes": isolated,
        "elapsed_ms": round((t1 - t0) * 1000, 3),
        "complexity": "O(E log E) — sort dominates; DSU ops are α(N) ≈ O(1)",
    }


# ---------------------------------------------------------------------------
# B. Shortest Paths — Dijkstra, A*, time-dependent Dijkstra
# ---------------------------------------------------------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def euclidean_km(node_a, node_b):
    """Straight-line km between two node dicts using their (x=lon, y=lat) coords."""
    return haversine_km(node_a["y"], node_a["x"], node_b["y"], node_b["x"])


def edge_travel_time_minutes(distance_km: float,
                             capacity: int,
                             flow: int = 0) -> float:
    """
    BPR-style travel time:
        t = t0 * (1 + 0.15 * (V/C)^4)
    Free-flow speed assumed 60 km/h.
    """
    free_flow_min = (distance_km / 60.0) * 60.0
    if capacity <= 0:
        return free_flow_min
    ratio = max(0.0, flow) / capacity
    return free_flow_min * (1.0 + 0.15 * (ratio ** 4))


def _flow_for_period(a: str, b: str, period: str) -> int:
    """Return vehicles/hour flow for a given period: morning/afternoon/evening/night."""
    key = road_key(a, b)
    if not key or key not in TRAFFIC_FLOW:
        return 0
    morning, afternoon, evening, night = TRAFFIC_FLOW[key]
    return {
        "morning": morning,
        "afternoon": afternoon,
        "evening": evening,
        "night": night,
    }.get(period, afternoon)


def dijkstra(source: str,
             target: Optional[str] = None,
             period: Optional[str] = None,
             include_potential: bool = False,
             memo: Optional[dict] = None):
    """
    Standard Dijkstra. If `period` is set, edge weight is travel-time in
    minutes that respects time-of-day traffic. Otherwise weight is km.

    `memo` (optional dict) caches full shortest-path results per (source, period).
    """
    cache_key = (source, period, include_potential)
    if memo is not None and cache_key in memo:
        dist, prev = memo[cache_key]
    else:
        adj = build_graph(include_potential=include_potential)
        dist = {n: math.inf for n in adj}
        prev: Dict[str, Optional[str]] = {n: None for n in adj}
        if source not in dist:
            return {"path": [], "edges": [], "cost": math.inf, "unit": "km",
                    "expanded": 0, "elapsed_ms": 0.0}
        dist[source] = 0
        pq = [(0, source)]
        expanded = 0
        visited_order: List[str] = []
        seen = set()
        t0 = time.perf_counter()
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            expanded += 1
            if u not in seen:
                seen.add(u)
                visited_order.append(u)
            for v, dist_km, cap, _kind, _meta in adj[u]:
                if period:
                    flow = _flow_for_period(u, v, period)
                    w = edge_travel_time_minutes(dist_km, cap, flow)
                else:
                    w = dist_km
                nd = d + w
                if nd < dist[v]:
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))
        t1 = time.perf_counter()
        if memo is not None:
            memo[cache_key] = (dist, prev)

    unit = "minutes" if period else "km"
    if target is None:
        return {"distances": dist, "prev": prev, "unit": unit}

    if target not in dist or dist[target] == math.inf:
        return {"path": [], "edges": [], "cost": math.inf, "unit": unit,
                "expanded": 0, "elapsed_ms": 0.0}

    path = _reconstruct_path(prev, target)
    edges = list(zip(path, path[1:]))
    return {
        "path": path,
        "edges": edges,
        "cost": round(dist[target], 3),
        "unit": unit,
        "expanded": locals().get("expanded", 0),
        "visited_order": locals().get("visited_order", []),
        "prev": prev,
        "elapsed_ms": round((locals().get("t1", time.perf_counter()) - locals().get("t0", time.perf_counter())) * 1000, 3),
    }


def a_star(source: str,
           target: str,
           period: Optional[str] = None,
           emergency: bool = False,
           include_potential: bool = False):
    """
    A* search with Haversine heuristic. When `emergency` is True, the cost
    function applies an emergency-priority discount on edge travel time
    (signal preemption -> assume 30% faster).
    """
    nodes = node_index()
    adj = build_graph(include_potential=include_potential)
    if (source not in nodes or target not in nodes
            or source not in adj or target not in adj):
        return {"path": [], "edges": [], "cost": math.inf, "unit": "minutes",
                "expanded": 0, "elapsed_ms": 0.0,
                "note": "Source or target is not connected to the road network."}

    target_node = nodes[target]

    def heuristic(n: str) -> float:
        if not period:
            return euclidean_km(nodes[n], target_node)
        # Time heuristic: distance / 60 km/h, in minutes (admissible lower bound)
        return (euclidean_km(nodes[n], target_node) / 60.0) * 60.0

    g = {n: math.inf for n in adj}
    prev: Dict[str, Optional[str]] = {n: None for n in adj}
    g[source] = 0
    pq = [(heuristic(source), 0, source)]
    expanded = 0
    visited_order: List[str] = []
    seen_nodes = set()

    t0 = time.perf_counter()
    while pq:
        f, d, u = heapq.heappop(pq)
        if u == target:
            if u not in seen_nodes:
                seen_nodes.add(u)
                visited_order.append(u)
            break
        if d > g[u]:
            continue
        expanded += 1
        if u not in seen_nodes:
            seen_nodes.add(u)
            visited_order.append(u)
        for v, dist_km, cap, _kind, _meta in adj[u]:
            if period:
                flow = _flow_for_period(u, v, period)
                w = edge_travel_time_minutes(dist_km, cap, flow)
                if emergency:
                    w *= 0.7  # signal preemption + clear-the-road effect
            else:
                w = dist_km
            ng = d + w
            if ng < g[v]:
                g[v] = ng
                prev[v] = u
                heapq.heappush(pq, (ng + heuristic(v), ng, v))
    t1 = time.perf_counter()

    unit = "minutes" if period else "km"
    if g[target] == math.inf:
        return {"path": [], "edges": [], "cost": math.inf, "unit": unit,
                "expanded": expanded, "elapsed_ms": round((t1 - t0) * 1000, 3)}

    path = _reconstruct_path(prev, target)
    return {
        "path": path,
        "edges": list(zip(path, path[1:])),
        "cost": round(g[target], 3),
        "unit": unit,
        "expanded": expanded,
        "visited_order": visited_order,
        "prev": prev,
        "elapsed_ms": round((t1 - t0) * 1000, 3),
    }


def _reconstruct_path(prev: Dict[str, Optional[str]], target: str) -> List[str]:
    path = []
    cur: Optional[str] = target
    while cur is not None:
        path.append(cur)
        cur = prev.get(cur)
    path.reverse()
    return path


# ---------------------------------------------------------------------------
# C. Dynamic Programming
# ---------------------------------------------------------------------------
def dp_transit_schedule(total_vehicles: int = 80,
                        line_demand: Optional[Dict[str, int]] = None,
                        passenger_value_per_vehicle: Optional[Dict[str, List[float]]] = None):
    """
    Knapsack-style DP for allocating a fleet of vehicles across metro & bus
    lines to maximize total daily passengers served.

    For each line we estimate marginal passengers/vehicle as:
        base = daily_passengers / current_vehicles
    with diminishing returns (10% drop per extra vehicle beyond current).
    Each line can receive 0..min(2*current_vehicles, total_vehicles) vehicles.

    Bounded-knapsack DP: O(L * V) time, O(V) space.
    """
    lines = []
    for m in METRO_LINES:
        # Treat metro "vehicles" abstractly: 1 vehicle = 1 train assigned per peak slot.
        # Use a synthetic baseline of 12 trains.
        baseline = 12
        per_vehicle = m["daily_passengers"] / baseline
        lines.append({
            "id": m["id"],
            "name": m["name"],
            "kind": "metro",
            "current": baseline,
            "max_extra": baseline,
            "value_per_vehicle": per_vehicle,
        })
    for b in BUS_ROUTES:
        lines.append({
            "id": b["id"],
            "name": f"Bus {b['id']}",
            "kind": "bus",
            "current": b["buses"],
            "max_extra": b["buses"],
            "value_per_vehicle": b["daily_passengers"] / max(1, b["buses"]),
        })

    V = total_vehicles
    L = len(lines)

    # Diminishing returns: pre-compute marginal passenger value per vehicle.
    marginals = []
    for ln in lines:
        cap = ln["current"] + ln["max_extra"]
        per_v = []
        for k in range(1, cap + 1):
            # Each additional vehicle yields 90% of the previous one.
            per_v.append(ln["value_per_vehicle"] * (0.9 ** (k - 1)))
        marginals.append(per_v)

    # dp[v] = best total value using v vehicles total
    dp = [0.0] * (V + 1)
    take = [[0] * (V + 1) for _ in range(L)]

    t0 = time.perf_counter()
    for i, ln in enumerate(marginals):
        new_dp = dp[:]
        new_take = take[i][:]
        cap_i = len(ln)
        for v in range(V + 1):
            best = dp[v]
            best_k = 0
            cumulative = 0.0
            for k in range(1, min(cap_i, v) + 1):
                cumulative += ln[k - 1]
                cand = dp[v - k] + cumulative
                if cand > best:
                    best = cand
                    best_k = k
            new_dp[v] = best
            new_take[v] = best_k
        dp = new_dp
        take[i] = new_take
    t1 = time.perf_counter()

    # Backtrack allocation
    allocation = [0] * L
    remaining = V
    for i in range(L - 1, -1, -1):
        k = take[i][remaining]
        allocation[i] = k
        remaining -= k

    plan = []
    for ln, k in zip(lines, allocation):
        plan.append({
            "id": ln["id"],
            "name": ln["name"],
            "kind": ln["kind"],
            "vehicles_assigned": k,
            "estimated_passengers": round(
                sum(ln["value_per_vehicle"] * (0.9 ** (j)) for j in range(k)), 1
            ),
        })

    return {
        "plan": plan,
        "total_vehicles": V,
        "vehicles_used": sum(allocation),
        "total_estimated_passengers": round(dp[V], 1),
        "elapsed_ms": round((t1 - t0) * 1000, 3),
        "complexity": "O(L * V * K) — bounded knapsack with per-item caps",
    }


def dp_road_maintenance(budget_million_egp: int = 500):
    """
    0/1 Knapsack DP — pick a subset of roads to repair within budget that
    maximizes total maintenance benefit.

    Cost   = distance_km * (11 - condition) * 2     (worse roads cost more)
    Benefit= traffic_flow_morning * (11 - condition) (more impact where worse + busier)
    """
    items = []
    for a, b, dist, cap, cond in EXISTING_ROADS:
        cost = max(1, int(round(dist * (11 - cond) * 2)))
        flow_key = road_key(a, b)
        morning_flow = TRAFFIC_FLOW[flow_key][0] if flow_key in TRAFFIC_FLOW else cap
        benefit = morning_flow * (11 - cond)
        items.append({
            "a": a, "b": b, "distance": dist, "condition": cond,
            "cost": cost, "benefit": benefit,
        })

    B = budget_million_egp
    n = len(items)
    dp = [[0] * (B + 1) for _ in range(n + 1)]

    t0 = time.perf_counter()
    for i in range(1, n + 1):
        c = items[i - 1]["cost"]
        v = items[i - 1]["benefit"]
        for b in range(B + 1):
            dp[i][b] = dp[i - 1][b]
            if c <= b:
                dp[i][b] = max(dp[i][b], dp[i - 1][b - c] + v)
    t1 = time.perf_counter()

    # Backtrack chosen items
    chosen = []
    b = B
    for i in range(n, 0, -1):
        if dp[i][b] != dp[i - 1][b]:
            chosen.append(items[i - 1])
            b -= items[i - 1]["cost"]
    chosen.reverse()

    return {
        "chosen": chosen,
        "total_cost_million_egp": sum(c["cost"] for c in chosen),
        "total_benefit": dp[n][B],
        "budget_million_egp": B,
        "elapsed_ms": round((t1 - t0) * 1000, 3),
        "complexity": "O(n * B) — classic 0/1 knapsack",
    }


# ---------------------------------------------------------------------------
# D. Greedy
# ---------------------------------------------------------------------------
def greedy_signal_optimization(period: str = "morning"):
    """
    Greedy approach for traffic-signal green-time allocation at each
    intersection (node). For every node, sort incoming flows by volume and
    assign green proportional to vehicle demand on each approach.
    A 90-second total cycle is split among approaches (min 8s each).
    """
    flows_by_node: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
    for a, b, _dist, cap, _cond in EXISTING_ROADS:
        key = road_key(a, b)
        if not key or key not in TRAFFIC_FLOW:
            continue
        m, af, ev, n = TRAFFIC_FLOW[key]
        f = {"morning": m, "afternoon": af, "evening": ev, "night": n}.get(period, m)
        flows_by_node[a].append((b, f))
        flows_by_node[b].append((a, f))

    plan = []
    for node, approaches in flows_by_node.items():
        if len(approaches) < 2:
            continue  # No real intersection to manage
        approaches.sort(key=lambda x: -x[1])
        total_flow = sum(f for _, f in approaches)
        cycle_seconds = 90
        min_green = 8
        # Reserve the minimum slice for each approach, distribute the rest greedily.
        free_seconds = cycle_seconds - min_green * len(approaches)
        free_seconds = max(0, free_seconds)
        allocations = []
        for nbr, flow in approaches:
            extra = (flow / total_flow) * free_seconds if total_flow else 0
            green = min_green + extra
            allocations.append({
                "approach_from": nbr,
                "flow_vph": flow,
                "green_seconds": round(green, 1),
            })
        plan.append({
            "intersection": node,
            "cycle_seconds": cycle_seconds,
            "total_flow_vph": total_flow,
            "allocations": allocations,
        })

    plan.sort(key=lambda p: -p["total_flow_vph"])
    return {
        "period": period,
        "intersections": plan,
        "complexity": "O(E log E) — sorting flows per intersection",
    }


def greedy_emergency_preemption(source: str, target: str, period: str = "morning"):
    """
    Greedy emergency-vehicle preemption simulation:
      - Use A* to plan the route.
      - Along the route, greedily preempt every signal on the path so the
        vehicle gets immediate green.
      - Compare against a normal trip on the same path.
    """
    plan = a_star(source, target, period=period, emergency=True)
    normal = a_star(source, target, period=period, emergency=False)
    if not plan["path"]:
        return {"path": [], "preempted_signals": [], "saved_minutes": 0,
                "emergency_minutes": math.inf, "normal_minutes": math.inf}
    preempted = plan["path"][1:-1]  # all intermediate nodes
    return {
        "path": plan["path"],
        "preempted_signals": preempted,
        "preempted_count": len(preempted),
        "emergency_minutes": plan["cost"],
        "normal_minutes": normal["cost"],
        "saved_minutes": round(normal["cost"] - plan["cost"], 3),
        "complexity": "O(V) — single sweep over the planned path",
    }


# ---------------------------------------------------------------------------
# Helpers for emergency response
# ---------------------------------------------------------------------------
def nearest_medical_route(source: str, period: str = "morning"):
    """Find the closest medical facility from `source` using A*.

    Returns the facility ID, the road-network target to dispatch to (which
    may be a proxy node if the hospital itself isn't on the road network),
    and the route. Falls back to the road-connected node closest to a
    hospital when no medical facility is on the road network.
    """
    from data import medical_facility_ids
    nodes = node_index()
    adj = build_graph()
    best = None
    for fid in medical_facility_ids():
        result = a_star(source, fid, period=period, emergency=True)
        if not result["path"]:
            continue
        if best is None or result["cost"] < best["cost"]:
            best = {**result, "facility_id": fid, "dispatch_target": fid}
    if best:
        return best
    # Fallback: route to the road-connected node closest to each hospital.
    if source not in nodes or source not in adj:
        return {"path": [], "cost": math.inf, "facility_id": None,
                "dispatch_target": None}
    best_proxy = None
    for fid in medical_facility_ids():
        if fid not in nodes:
            continue
        f_node = nodes[fid]
        nearest_node = min(adj.keys(),
                           key=lambda nid: euclidean_km(nodes[nid], f_node))
        if nearest_node == source:
            continue
        result = a_star(source, nearest_node, period=period, emergency=True)
        if not result["path"]:
            continue
        # Add straight-line walking time from road to hospital
        extra_min = (euclidean_km(nodes[nearest_node], f_node) / 60.0) * 60.0
        result = {**result, "cost": result["cost"] + extra_min}
        result["facility_id"] = fid
        result["dispatch_target"] = nearest_node
        result["note"] = (
            f"{f_node['name']} is not on the road network — dispatching to "
            f"{nodes[nearest_node]['name']} (closest connected node)."
        )
        if best_proxy is None or result["cost"] < best_proxy["cost"]:
            best_proxy = result
    return best_proxy or {"path": [], "cost": math.inf, "facility_id": None,
                          "dispatch_target": None}
