class CairoData:
    def __init__(self):
        self.neighborhoods = []
        self.facilities = []
        self.existing_roads = []
        self.potential_roads = []
        self.traffic_patterns = []
        self.metro_lines = []
        self.bus_routes = []
        self.transport_demand = []
        self.load_data()

    def load_data(self):
        """Load all Cairo transportation data"""
        self._load_locations()
        self._load_roads()
        self._load_transport()
        print("Data loaded successfully:")
        print(f"- {len(self.neighborhoods)} neighborhoods")
        print(f"- {len(self.facilities)} facilities")
        print(f"- {len(self.existing_roads)} existing roads")
        print(f"- {len(self.metro_lines)} metro lines")

    def _load_locations(self):
        """Load neighborhoods and facilities"""
        self.neighborhoods = [
            {"id": 1, "name": "Maadi", "population": 250000, "type": "Residential", "x": 31.25, "y": 29.96},
            {"id": 2, "name": "Nasr City", "population": 500000, "type": "Mixed", "x": 31.34, "y": 30.06},
            {"id": 3, "name": "Downtown Cairo", "population": 100000, "type": "Business", "x": 31.24, "y": 30.04},
            {"id": 4, "name": "New Cairo", "population": 300000, "type": "Residential", "x": 31.47, "y": 30.03},
            {"id": 5, "name": "Heliopolis", "population": 200000, "type": "Mixed", "x": 31.32, "y": 30.09},
            {"id": 6, "name": "Zamalek", "population": 50000, "type": "Residential", "x": 31.22, "y": 30.06},
            {"id": 7, "name": "6th October City", "population": 400000, "type": "Mixed", "x": 30.98, "y": 29.93},
            {"id": 8, "name": "Giza", "population": 550000, "type": "Mixed", "x": 31.21, "y": 29.99},
            {"id": 9, "name": "Mohandessin", "population": 180000, "type": "Business", "x": 31.20, "y": 30.05},
            {"id": 10, "name": "Dokki", "population": 220000, "type": "Mixed", "x": 31.21, "y": 30.03},
            {"id": 11, "name": "Shubra", "population": 450000, "type": "Residential", "x": 31.24, "y": 30.11},
            {"id": 12, "name": "Helwan", "population": 350000, "type": "Industrial", "x": 31.33, "y": 29.85},
            {"id": 13, "name": "New Administrative Capital", "population": 50000, "type": "Government", "x": 31.80, "y": 30.02},
            {"id": 14, "name": "Al Rehab", "population": 120000, "type": "Residential", "x": 31.49, "y": 30.06},
            {"id": 15, "name": "Sheikh Zayed", "population": 150000, "type": "Residential", "x": 30.94, "y": 30.01}
        ]
        
        self.facilities = [
            {"id": "F1", "name": "Cairo International Airport", "type": "Airport", "x": 31.41, "y": 30.11},
            {"id": "F2", "name": "Ramses Railway Station", "type": "Transit Hub", "x": 31.25, "y": 30.06},
            {"id": "F3", "name": "Cairo University", "type": "Education", "x": 31.21, "y": 30.03},
            {"id": "F4", "name": "Al-Azhar University", "type": "Education", "x": 31.26, "y": 30.05},
            {"id": "F5", "name": "Egyptian Museum", "type": "Tourism", "x": 31.23, "y": 30.05},
            {"id": "F6", "name": "Cairo International Stadium", "type": "Sports", "x": 31.30, "y": 30.07},
            {"id": "F7", "name": "Smart Village", "type": "Business", "x": 30.97, "y": 30.07},
            {"id": "F8", "name": "Cairo Festival City", "type": "Commercial", "x": 31.40, "y": 30.03},
            {"id": "F9", "name": "Qasr El Aini Hospital", "type": "Medical", "x": 31.23, "y": 30.03},
            {"id": "F10", "name": "Maadi Military Hospital", "type": "Medical", "x": 31.25, "y": 29.95},
            {"id": "F11", "name": "Dar El Fouad Hospital", "type": "Medical", "x": 30.99, "y": 29.97},
            {"id": "F12", "name": "57357 Hospital", "type": "Medical", "x": 31.28, "y": 30.08}
        ]

    def _load_roads(self):
        """Load road network data with guaranteed connections to hospitals"""
        self.existing_roads = [
            # Existing roads between neighborhoods
            {"from": 1, "to": 3, "distance": 8.5, "capacity": 3000, "condition": 7},
            {"from": 1, "to": 8, "distance": 6.2, "capacity": 2500, "condition": 6},
            {"from": 2, "to": 3, "distance": 5.9, "capacity": 2800, "condition": 8},
            {"from": 2, "to": 5, "distance": 4.0, "capacity": 3200, "condition": 9},
            {"from": 3, "to": 5, "distance": 6.1, "capacity": 3500, "condition": 7},
            {"from": 3, "to": 6, "distance": 3.2, "capacity": 2000, "condition": 8},
            {"from": 3, "to": 9, "distance": 4.5, "capacity": 2600, "condition": 6},
            {"from": 3, "to": 10, "distance": 3.8, "capacity": 2400, "condition": 7},
            {"from": 4, "to": 2, "distance": 15.2, "capacity": 3800, "condition": 9},
            {"from": 4, "to": 14, "distance": 5.3, "capacity": 3000, "condition": 10},
            {"from": 5, "to": 11, "distance": 7.9, "capacity": 3100, "condition": 7},
            {"from": 6, "to": 9, "distance": 2.2, "capacity": 1800, "condition": 8},
            {"from": 7, "to": 8, "distance": 24.5, "capacity": 3500, "condition": 8},
            {"from": 7, "to": 15, "distance": 9.8, "capacity": 3000, "condition": 9},
            {"from": 8, "to": 10, "distance": 3.3, "capacity": 2200, "condition": 7},
            {"from": 8, "to": 12, "distance": 14.8, "capacity": 2600, "condition": 5},
            {"from": 9, "to": 10, "distance": 2.1, "capacity": 1900, "condition": 7},
            {"from": 10, "to": 11, "distance": 8.7, "capacity": 2400, "condition": 6},
            {"from": 11, "to": "F2", "distance": 3.6, "capacity": 2200, "condition": 7},
            {"from": 12, "to": 1, "distance": 12.7, "capacity": 2800, "condition": 6},
            {"from": 13, "to": 4, "distance": 45.0, "capacity": 4000, "condition": 10},
            {"from": 14, "to": 13, "distance": 35.5, "capacity": 3800, "condition": 9},
            {"from": 15, "to": 7, "distance": 9.8, "capacity": 3000, "condition": 9},
            {"from": "F1", "to": 5, "distance": 7.5, "capacity": 3500, "condition": 9},
            {"from": "F1", "to": 2, "distance": 9.2, "capacity": 3200, "condition": 8},
            {"from": "F2", "to": 3, "distance": 2.5, "capacity": 2000, "condition": 7},
            {"from": "F7", "to": 15, "distance": 8.3, "capacity": 2800, "condition": 8},
            {"from": "F8", "to": 4, "distance": 6.1, "capacity": 3000, "condition": 9},

            # New hospital connections (critical for emergency routes)
            {"from": "F9", "to": 3, "distance": 1.5, "capacity": 2000, "condition": 8},  # Qasr El Aini to Downtown
            {"from": "F9", "to": 10, "distance": 2.1, "capacity": 1800, "condition": 7},  # Qasr El Aini to Dokki
            {"from": "F10", "to": 1, "distance": 1.8, "capacity": 2200, "condition": 8},  # Maadi Military to Maadi
            {"from": "F10", "to": 12, "distance": 5.2, "capacity": 2400, "condition": 7},  # Maadi Military to Helwan
            {"from": "F11", "to": 7, "distance": 3.5, "capacity": 2000, "condition": 8},  # Dar El Fouad to 6th October
            {"from": "F11", "to": 15, "distance": 4.8, "capacity": 2200, "condition": 7},  # Dar El Fouad to Sheikh Zayed
            {"from": "F12", "to": 5, "distance": 2.7, "capacity": 2500, "condition": 9},  # 57357 to Heliopolis
            {"from": "F12", "to": 2, "distance": 3.1, "capacity": 2300, "condition": 8},  # 57357 to Nasr City
        ]
        
        self.potential_roads = [
            {"from": 1, "to": 4, "distance": 22.8, "capacity": 4000, "cost": 450},
            {"from": 1, "to": 14, "distance": 25.3, "capacity": 3800, "cost": 500},
            {"from": 2, "to": 13, "distance": 48.2, "capacity": 4500, "cost": 950},
            {"from": 3, "to": 13, "distance": 56.7, "capacity": 4500, "cost": 1100},
            {"from": 5, "to": 4, "distance": 16.8, "capacity": 3500, "cost": 320},
            {"from": 6, "to": 8, "distance": 7.5, "capacity": 2500, "cost": 150},
            {"from": 7, "to": 13, "distance": 82.3, "capacity": 4000, "cost": 1600},
            {"from": 9, "to": 11, "distance": 6.9, "capacity": 2800, "cost": 140},
            {"from": 10, "to": "F7", "distance": 27.4, "capacity": 3200, "cost": 550},
            {"from": 11, "to": 13, "distance": 62.1, "capacity": 4200, "cost": 1250},
            {"from": 12, "to": 14, "distance": 30.5, "capacity": 3600, "cost": 610},
            {"from": 14, "to": 5, "distance": 18.2, "capacity": 3300, "cost": 360},
            {"from": 15, "to": 9, "distance": 22.7, "capacity": 3000, "cost": 450},
            {"from": "F1", "to": 13, "distance": 40.2, "capacity": 4000, "cost": 800},
            {"from": "F7", "to": 9, "distance": 26.8, "capacity": 3200, "cost": 540}
        ]
        
        self.traffic_patterns = [
            {"road": "1-3", "morning": 2800, "afternoon": 1500, "evening": 2600, "night": 800},
            {"road": "1-8", "morning": 2200, "afternoon": 1200, "evening": 2100, "night": 600},
            {"road": "2-3", "morning": 2700, "afternoon": 1400, "evening": 2500, "night": 700},
            {"road": "2-5", "morning": 3000, "afternoon": 1600, "evening": 2800, "night": 650},
            {"road": "3-5", "morning": 3200, "afternoon": 1700, "evening": 3100, "night": 800},
            {"road": "3-6", "morning": 1800, "afternoon": 1400, "evening": 1900, "night": 500},
            {"road": "3-9", "morning": 2400, "afternoon": 1300, "evening": 2200, "night": 550},
            {"road": "3-10", "morning": 2300, "afternoon": 1200, "evening": 2100, "night": 500},
            {"road": "4-2", "morning": 3600, "afternoon": 1800, "evening": 3300, "night": 750},
            {"road": "4-14", "morning": 2800, "afternoon": 1600, "evening": 2600, "night": 600},
            {"road": "5-11", "morning": 2900, "afternoon": 1500, "evening": 2700, "night": 650},
            {"road": "6-9", "morning": 1700, "afternoon": 1300, "evening": 1800, "night": 450},
            {"road": "7-8", "morning": 3200, "afternoon": 1700, "evening": 3000, "night": 700},
            {"road": "7-15", "morning": 2800, "afternoon": 1500, "evening": 2600, "night": 600},
            {"road": "8-10", "morning": 2000, "afternoon": 1100, "evening": 1900, "night": 450},
            {"road": "8-12", "morning": 2400, "afternoon": 1300, "evening": 2200, "night": 500},
            {"road": "9-10", "morning": 1800, "afternoon": 1200, "evening": 1700, "night": 400},
            {"road": "10-11", "morning": 2200, "afternoon": 1300, "evening": 2100, "night": 500},
            {"road": "11-F2", "morning": 2100, "afternoon": 1200, "evening": 2000, "night": 450},
            {"road": "12-1", "morning": 2600, "afternoon": 1400, "evening": 2400, "night": 550},
            {"road": "13-4", "morning": 3800, "afternoon": 2000, "evening": 3500, "night": 800},
            {"road": "14-13", "morning": 3600, "afternoon": 1900, "evening": 3300, "night": 750},
            {"road": "15-7", "morning": 2800, "afternoon": 1500, "evening": 2600, "night": 600},
            {"road": "F1-5", "morning": 3300, "afternoon": 2200, "evening": 3100, "night": 1200},
            {"road": "F1-2", "morning": 3000, "afternoon": 2000, "evening": 2800, "night": 1100},
            {"road": "F2-3", "morning": 1900, "afternoon": 1600, "evening": 1800, "night": 900},
            {"road": "F7-15", "morning": 2600, "afternoon": 1500, "evening": 2400, "night": 550},
            {"road": "F8-4", "morning": 2800, "afternoon": 1600, "evening": 2600, "night": 600},
            
            # Hospital road traffic patterns
            {"road": "F9-3", "morning": 1500, "afternoon": 1000, "evening": 1400, "night": 400},
            {"road": "F9-10", "morning": 1200, "afternoon": 800, "evening": 1100, "night": 300},
            {"road": "F10-1", "morning": 1300, "afternoon": 900, "evening": 1200, "night": 350},
            {"road": "F10-12", "morning": 1100, "afternoon": 700, "evening": 1000, "night": 250},
            {"road": "F11-7", "morning": 1400, "afternoon": 950, "evening": 1300, "night": 400},
            {"road": "F11-15", "morning": 1200, "afternoon": 850, "evening": 1100, "night": 300},
            {"road": "F12-5", "morning": 1600, "afternoon": 1100, "evening": 1500, "night": 450},
            {"road": "F12-2", "morning": 1700, "afternoon": 1200, "evening": 1600, "night": 500}
        ]

    def _load_transport(self):
        """Load public transport data"""
        self.metro_lines = [
            {"id": "M1", "name": "Line 1 (Helwan-New Marg)", "stations": [12,1,3,"F2",11], "passengers": 1500000},
            {"id": "M2", "name": "Line 2 (Shubra-Giza)", "stations": [11,"F2",3,10,8], "passengers": 1200000},
            {"id": "M3", "name": "Line 3 (Airport-Imbaba)", "stations": ["F1",5,2,3,9], "passengers": 800000}
        ]
        
        self.bus_routes = [
            {"id": "B1", "stops": [1,3,6,9], "buses": 25, "passengers": 35000},
            {"id": "B2", "stops": [7,15,8,10,3], "buses": 30, "passengers": 42000},
            {"id": "B3", "stops": [2,5,"F1"], "buses": 20, "passengers": 28000},
            {"id": "B4", "stops": [4,14,2,3], "buses": 22, "passengers": 31000},
            {"id": "B5", "stops": [8,12,1], "buses": 18, "passengers": 25000},
            {"id": "B6", "stops": [11,5,2], "buses": 24, "passengers": 33000},
            {"id": "B7", "stops": [13,4,14], "buses": 15, "passengers": 21000},
            {"id": "B8", "stops": ["F7",15,7], "buses": 12, "passengers": 17000},
            {"id": "B9", "stops": [1,8,10,9,6], "buses": 28, "passengers": 39000},
            {"id": "B10", "stops": ["F8",4,2,5], "buses": 20, "passengers": 28000},
            {"id": "B11", "stops": ["F9",3,10,"F3"], "buses": 18, "passengers": 22000},  # Hospital route
            {"id": "B12", "stops": ["F10",1,12,"F11"], "buses": 15, "passengers": 18000}  # Hospital route
        ]
        
        self.transport_demand = [
            {"from": 3, "to": 5, "passengers": 15000},
            {"from": 1, "to": 3, "passengers": 12000},
            {"from": 2, "to": 3, "passengers": 18000},
            {"from": "F2", "to": 11, "passengers": 25000},
            {"from": "F1", "to": 3, "passengers": 20000},
            {"from": 7, "to": 3, "passengers": 14000},
            {"from": 4, "to": 3, "passengers": 16000},
            {"from": 8, "to": 3, "passengers": 22000},
            {"from": 3, "to": 9, "passengers": 13000},
            {"from": 5, "to": 2, "passengers": 17000},
            {"from": 11, "to": 3, "passengers": 24000},
            {"from": 12, "to": 3, "passengers": 11000},
            {"from": 1, "to": 8, "passengers": 9000},
            {"from": 7, "to": "F7", "passengers": 18000},
            {"from": 4, "to": "F8", "passengers": 12000},
            {"from": 13, "to": 3, "passengers": 8000},
            {"from": 14, "to": 4, "passengers": 7000},
            
            # Hospital-related transport demand
            {"from": 3, "to": "F9", "passengers": 8500},
            {"from": 1, "to": "F10", "passengers": 7500},
            {"from": 7, "to": "F11", "passengers": 6500},
            {"from": 5, "to": "F12", "passengers": 9500}
        ]

    def location_exists(self, location_id):
        """Check if a location exists in neighborhoods or facilities"""
        try:
            location_id = str(location_id)
            # Check neighborhoods
            if any(str(n['id']) == location_id for n in self.neighborhoods):
                return True
            # Check facilities
            if any(f['id'] == location_id for f in self.facilities):
                return True
            return False
        except Exception as e:
            print(f"Error checking location existence: {e}")
            return False

    def get_neighborhood(self, id):
        """Get neighborhood by ID"""
        try:
            id = str(id)
            return next((n for n in self.neighborhoods if str(n['id']) == id), None)
        except Exception as e:
            print(f"Error getting neighborhood {id}: {e}")
            return None

    def get_facility(self, id):
        """Get facility by ID"""
        try:
            id = str(id)
            return next((f for f in self.facilities if f['id'] == id), None)
        except Exception as e:
            print(f"Error getting facility {id}: {e}")
            return None

    def get_location_name(self, id):
        """Get location name by ID"""
        try:
            loc = self.get_neighborhood(id) or self.get_facility(id)
            return loc['name'] if loc else f"Unknown Location ({id})"
        except Exception as e:
            print(f"Error getting location name {id}: {e}")
            return f"Error: {id}"

    def get_road_traffic(self, from_id, to_id, time_of_day):
        """Get traffic data for a road segment"""
        try:
            from_id = str(from_id)
            to_id = str(to_id)
            
            road_id = f"{from_id}-{to_id}"
            road = next((r for r in self.traffic_patterns if r['road'] == road_id), None)
            if not road:
                road_id = f"{to_id}-{from_id}"
                road = next((r for r in self.traffic_patterns if r['road'] == road_id), None)
            
            return road.get(time_of_day, 1000) if road else 1000
        except Exception as e:
            print(f"Error getting traffic for {from_id}-{to_id}: {e}")
            return 1000

    def get_road_between(self, from_id, to_id):
        """Get road data between two locations"""
        try:
            from_id = str(from_id)
            to_id = str(to_id)
            
            road = next((r for r in self.existing_roads if 
                        (str(r['from']) == from_id and str(r['to']) == to_id) or 
                        (str(r['from']) == to_id and str(r['to']) == from_id)), None)
            return road
        except Exception as e:
            print(f"Error getting road between {from_id} and {to_id}: {e}")
            return None

    def get_all_location_ids(self):
        """Get all valid location IDs"""
        neighborhood_ids = [str(n['id']) for n in self.neighborhoods]
        facility_ids = [f['id'] for f in self.facilities]
        return neighborhood_ids + facility_ids