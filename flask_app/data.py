"""
Cairo Transportation Network — Provided Data
Source: CSE112 Project Provided Data
"""

NEIGHBORHOODS = [
    {"id": "1",  "name": "Maadi",                       "population": 250000, "type": "Residential", "x": 31.25, "y": 29.96},
    {"id": "2",  "name": "Nasr City",                   "population": 500000, "type": "Mixed",       "x": 31.34, "y": 30.06},
    {"id": "3",  "name": "Downtown Cairo",              "population": 100000, "type": "Business",    "x": 31.24, "y": 30.04},
    {"id": "4",  "name": "New Cairo",                   "population": 300000, "type": "Residential", "x": 31.47, "y": 30.03},
    {"id": "5",  "name": "Heliopolis",                  "population": 200000, "type": "Mixed",       "x": 31.32, "y": 30.09},
    {"id": "6",  "name": "Zamalek",                     "population":  50000, "type": "Residential", "x": 31.22, "y": 30.06},
    {"id": "7",  "name": "6th October City",            "population": 400000, "type": "Mixed",       "x": 30.98, "y": 29.93},
    {"id": "8",  "name": "Giza",                        "population": 550000, "type": "Mixed",       "x": 31.21, "y": 29.99},
    {"id": "9",  "name": "Mohandessin",                 "population": 180000, "type": "Business",    "x": 31.20, "y": 30.05},
    {"id": "10", "name": "Dokki",                       "population": 220000, "type": "Mixed",       "x": 31.21, "y": 30.03},
    {"id": "11", "name": "Shubra",                      "population": 450000, "type": "Residential", "x": 31.24, "y": 30.11},
    {"id": "12", "name": "Helwan",                      "population": 350000, "type": "Industrial",  "x": 31.33, "y": 29.85},
    {"id": "13", "name": "New Administrative Capital",  "population":  50000, "type": "Government",  "x": 31.80, "y": 30.02},
    {"id": "14", "name": "Al Rehab",                    "population": 120000, "type": "Residential", "x": 31.49, "y": 30.06},
    {"id": "15", "name": "Sheikh Zayed",                "population": 150000, "type": "Residential", "x": 30.94, "y": 30.01},
]

FACILITIES = [
    {"id": "F1",  "name": "Cairo International Airport", "type": "Airport",     "x": 31.41, "y": 30.11},
    {"id": "F2",  "name": "Ramses Railway Station",      "type": "Transit Hub", "x": 31.25, "y": 30.06},
    {"id": "F3",  "name": "Cairo University",            "type": "Education",   "x": 31.21, "y": 30.03},
    {"id": "F4",  "name": "Al-Azhar University",         "type": "Education",   "x": 31.26, "y": 30.05},
    {"id": "F5",  "name": "Egyptian Museum",             "type": "Tourism",     "x": 31.23, "y": 30.05},
    {"id": "F6",  "name": "Cairo International Stadium", "type": "Sports",      "x": 31.30, "y": 30.07},
    {"id": "F7",  "name": "Smart Village",               "type": "Business",    "x": 30.97, "y": 30.07},
    {"id": "F8",  "name": "Cairo Festival City",         "type": "Commercial",  "x": 31.40, "y": 30.03},
    {"id": "F9",  "name": "Qasr El Aini Hospital",       "type": "Medical",     "x": 31.23, "y": 30.03},
    {"id": "F10", "name": "Maadi Military Hospital",     "type": "Medical",     "x": 31.25, "y": 29.95},
]

# (FromID, ToID, Distance(km), Capacity(veh/h), Condition(1-10))
EXISTING_ROADS = [
    ("1",  "3",  8.5, 3000, 7),
    ("1",  "8",  6.2, 2500, 6),
    ("2",  "3",  5.9, 2800, 8),
    ("2",  "5",  4.0, 3200, 9),
    ("3",  "5",  6.1, 3500, 7),
    ("3",  "6",  3.2, 2000, 8),
    ("3",  "9",  4.5, 2600, 6),
    ("3",  "10", 3.8, 2400, 7),
    ("4",  "2",  15.2, 3800, 9),
    ("4",  "14", 5.3, 3000, 10),
    ("5",  "11", 7.9, 3100, 7),
    ("6",  "9",  2.2, 1800, 8),
    ("7",  "8",  24.5, 3500, 8),
    ("7",  "15", 9.8, 3000, 9),
    ("8",  "10", 3.3, 2200, 7),
    ("8",  "12", 14.8, 2600, 5),
    ("9",  "10", 2.1, 1900, 7),
    ("10", "11", 8.7, 2400, 6),
    ("11", "F2", 3.6, 2200, 7),
    ("12", "1",  12.7, 2800, 6),
    ("13", "4",  45.0, 4000, 10),
    ("14", "13", 35.5, 3800, 9),
    ("15", "7",  9.8, 3000, 9),
    ("F1", "5",  7.5, 3500, 9),
    ("F1", "2",  9.2, 3200, 8),
    ("F2", "3",  2.5, 2000, 7),
    ("F7", "15", 8.3, 2800, 8),
    ("F8", "4",  6.1, 3000, 9),
]

# (FromID, ToID, Distance(km), Capacity(veh/h), Cost(Million EGP))
POTENTIAL_ROADS = [
    ("1",  "4",  22.8, 4000, 450),
    ("1",  "14", 25.3, 3800, 500),
    ("2",  "13", 48.2, 4500, 950),
    ("3",  "13", 56.7, 4500, 1100),
    ("5",  "4",  16.8, 3500, 320),
    ("6",  "8",  7.5, 2500, 150),
    ("7",  "13", 82.3, 4000, 1600),
    ("9",  "11", 6.9, 2800, 140),
    ("10", "F7", 27.4, 3200, 550),
    ("11", "13", 62.1, 4200, 1250),
    ("12", "14", 30.5, 3600, 610),
    ("14", "5",  18.2, 3300, 360),
    ("15", "9",  22.7, 3000, 450),
    ("F1", "13", 40.2, 4000, 800),
    ("F7", "9",  26.8, 3200, 540),
]

# RoadID "A-B" -> (Morning, Afternoon, Evening, Night) vehicles/hour
TRAFFIC_FLOW = {
    "1-3":  (2800, 1500, 2600, 800),
    "1-8":  (2200, 1200, 2100, 600),
    "2-3":  (2700, 1400, 2500, 700),
    "2-5":  (3000, 1600, 2800, 650),
    "3-5":  (3200, 1700, 3100, 800),
    "3-6":  (1800, 1400, 1900, 500),
    "3-9":  (2400, 1300, 2200, 550),
    "3-10": (2300, 1200, 2100, 500),
    "4-2":  (3600, 1800, 3300, 750),
    "4-14": (2800, 1600, 2600, 600),
    "5-11": (2900, 1500, 2700, 650),
    "6-9":  (1700, 1300, 1800, 450),
    "7-8":  (3200, 1700, 3000, 700),
    "7-15": (2800, 1500, 2600, 600),
    "8-10": (2000, 1100, 1900, 450),
    "8-12": (2400, 1300, 2200, 500),
    "9-10": (1800, 1200, 1700, 400),
    "10-11":(2200, 1300, 2100, 500),
    "11-F2":(2100, 1200, 2000, 450),
    "12-1": (2600, 1400, 2400, 550),
    "13-4": (3800, 2000, 3500, 800),
    "14-13":(3600, 1900, 3300, 750),
    "15-7": (2800, 1500, 2600, 600),
    "F1-5": (3300, 2200, 3100, 1200),
    "F1-2": (3000, 2000, 2800, 1100),
    "F2-3": (1900, 1600, 1800, 900),
    "F7-15":(2600, 1500, 2400, 550),
    "F8-4": (2800, 1600, 2600, 600),
}

METRO_LINES = [
    {"id": "M1", "name": "Line 1 (Helwan-New Marg)", "stations": ["12", "1", "3", "F2", "11"], "daily_passengers": 1500000},
    {"id": "M2", "name": "Line 2 (Shubra-Giza)",     "stations": ["11", "F2", "3", "10", "8"], "daily_passengers": 1200000},
    {"id": "M3", "name": "Line 3 (Airport-Imbaba)",  "stations": ["F1", "5", "2", "3", "9"],   "daily_passengers":  800000},
]

BUS_ROUTES = [
    {"id": "B1",  "stops": ["1", "3", "6", "9"],            "buses": 25, "daily_passengers": 35000},
    {"id": "B2",  "stops": ["7", "15", "8", "10", "3"],     "buses": 30, "daily_passengers": 42000},
    {"id": "B3",  "stops": ["2", "5", "F1"],                "buses": 20, "daily_passengers": 28000},
    {"id": "B4",  "stops": ["4", "14", "2", "3"],           "buses": 22, "daily_passengers": 31000},
    {"id": "B5",  "stops": ["8", "12", "1"],                "buses": 18, "daily_passengers": 25000},
    {"id": "B6",  "stops": ["11", "5", "2"],                "buses": 24, "daily_passengers": 33000},
    {"id": "B7",  "stops": ["13", "4", "14"],               "buses": 15, "daily_passengers": 21000},
    {"id": "B8",  "stops": ["F7", "15", "7"],               "buses": 12, "daily_passengers": 17000},
    {"id": "B9",  "stops": ["1", "8", "10", "9", "6"],      "buses": 28, "daily_passengers": 39000},
    {"id": "B10", "stops": ["F8", "4", "2", "5"],           "buses": 20, "daily_passengers": 28000},
]

TRANSIT_DEMAND = [
    ("3",  "5",  15000),
    ("1",  "3",  12000),
    ("2",  "3",  18000),
    ("F2", "11", 25000),
    ("F1", "3",  20000),
    ("7",  "3",  14000),
    ("4",  "3",  16000),
    ("8",  "3",  22000),
    ("3",  "9",  13000),
    ("5",  "2",  17000),
    ("11", "3",  24000),
    ("12", "3",  11000),
    ("1",  "8",   9000),
    ("7",  "F7", 18000),
    ("4",  "F8", 12000),
    ("13", "3",   8000),
    ("14", "4",   7000),
]


def all_nodes():
    """Return list of all nodes (neighborhoods + facilities) with id, name, type, x, y."""
    nodes = []
    for n in NEIGHBORHOODS:
        nodes.append({**n, "category": "neighborhood"})
    for f in FACILITIES:
        nodes.append({**f, "population": 0, "category": "facility"})
    return nodes


def node_index():
    """Return dict id -> node info."""
    return {n["id"]: n for n in all_nodes()}


def critical_facility_ids():
    """IDs considered critical (medical, government, transit hub, airport)."""
    crit = set()
    for f in FACILITIES:
        if f["type"] in ("Medical", "Transit Hub", "Airport"):
            crit.add(f["id"])
    for n in NEIGHBORHOODS:
        if n["type"] == "Government":
            crit.add(n["id"])
    return crit


def medical_facility_ids():
    return {f["id"] for f in FACILITIES if f["type"] == "Medical"}


def road_key(a, b):
    """Canonical undirected edge key matching TRAFFIC_FLOW dict."""
    if f"{a}-{b}" in TRAFFIC_FLOW:
        return f"{a}-{b}"
    if f"{b}-{a}" in TRAFFIC_FLOW:
        return f"{b}-{a}"
    return None
