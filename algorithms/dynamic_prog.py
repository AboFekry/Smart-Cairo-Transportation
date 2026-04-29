class PublicTransportOptimizer:
    def __init__(self, cairo_data):
        self.data = cairo_data
    
    def optimize_schedules(self):
        # Optimize metro schedules using dynamic programming
        metro_schedules = self._optimize_metro_schedules()
        
        # Optimize bus schedules using dynamic programming
        bus_schedules = self._optimize_bus_schedules()
        
        # Optimize resource allocation for road maintenance
        maintenance_plan = self._optimize_road_maintenance()
        
        return {
            'metro_schedules': metro_schedules,
            'bus_schedules': bus_schedules,
            'maintenance_plan': maintenance_plan,
            'estimated_improvement': self._estimate_improvement(metro_schedules, bus_schedules, maintenance_plan)
        }
    
    def _optimize_metro_schedules(self):
        # DP approach to optimize metro schedules based on demand
        results = []
        
        for line in self.data.metro_lines:
            stations = line['stations']
            passengers = line['passengers']
            
            # Create a DP table for scheduling trains between stations
            n = len(stations)
            dp = [[0] * n for _ in range(n)]
            
            # Base case: direct trips between stations
            for i in range(n):
                for j in range(i+1, n):
                    from_id = stations[i]
                    to_id = stations[j]
                    
                    # Find demand between these stations
                    demand = next((d['passengers'] for d in self.data.transport_demand 
                                 if d['from'] == from_id and d['to'] == to_id), 0)
                    reverse_demand = next((d['passengers'] for d in self.data.transport_demand 
                                          if d['from'] == to_id and d['to'] == from_id), 0)
                    total_demand = demand + reverse_demand
                    
                    # Calculate optimal frequency (trains per hour)
                    capacity_per_train = 1000  # passengers per train
                    min_frequency = max(2, total_demand / capacity_per_train / 18)  # at least 2 trains/hour
                    
                    dp[i][j] = min_frequency
            
            # Fill DP table for multi-segment trips
            for length in range(2, n):
                for i in range(n - length):
                    j = i + length
                    min_freq = float('inf')
                    
                    for k in range(i+1, j):
                        freq = max(dp[i][k], dp[k][j])
                        if freq < min_freq:
                            min_freq = freq
                    
                    dp[i][j] = min(dp[i][j], min_freq)
            
            # Determine final schedule
            optimal_frequency = dp[0][n-1]
            trains_needed = max(4, int(optimal_frequency * 18))  # 18 operating hours
            
            results.append({
                'line_id': line['id'],
                'line_name': line['name'],
                'optimal_frequency': optimal_frequency,
                'trains_needed': trains_needed,
                'current_trains': trains_needed,  # In real implementation, compare with current
                'stations': stations,
                'station_names': [self.data.get_location_name(s) for s in stations]
            })
        
        return results
    
    def _optimize_bus_schedules(self):
        # Similar DP approach for bus routes
        results = []
        
        for route in self.data.bus_routes:
            stops = route['stops']
            current_buses = route['buses']
            passengers = route['passengers']
            
            # Calculate demand along the route
            total_demand = 0
            for i in range(len(stops)):
                for j in range(i+1, len(stops)):
                    from_id = stops[i]
                    to_id = stops[j]
                    
                    demand = next((d['passengers'] for d in self.data.transport_demand 
                                 if d['from'] == from_id and d['to'] == to_id), 0)
                    reverse_demand = next((d['passengers'] for d in self.data.transport_demand 
                                          if d['from'] == to_id and d['to'] == from_id), 0)
                    total_demand += demand + reverse_demand
            
            # Calculate optimal number of buses
            capacity_per_bus = 50  # passengers per bus
            trips_per_bus_per_day = 10  # average trips per bus
            optimal_buses = max(2, total_demand / (capacity_per_bus * trips_per_bus_per_day))
            
            results.append({
                'route_id': route['id'],
                'optimal_buses': optimal_buses,
                'current_buses': current_buses,
                'stops': stops,
                'stop_names': [self.data.get_location_name(s) for s in stops],
                'demand': total_demand,
                'utilization': passengers / (current_buses * capacity_per_bus * trips_per_bus_per_day) if current_buses > 0 else 0
            })
        
        return results
    
    def _optimize_road_maintenance(self):
        # Knapsack problem approach for road maintenance allocation
        roads = self.data.existing_roads.copy()
        budget = 500  # million EGP
        
        # Add a value score for each road based on condition, traffic, and importance
        for road in roads:
            traffic = max(
                self.data.get_road_traffic(road['from'], road['to'], 'morning'),
                self.data.get_road_traffic(road['from'], road['to'], 'evening')
            )
            
            # Calculate importance score
            from_node = self.data.get_neighborhood(road['from']) or self.data.get_facility(road['from'])
            to_node = self.data.get_neighborhood(road['to']) or self.data.get_facility(road['to'])
            
            population_factor = 0
            if from_node and to_node:
                population_factor = (from_node.get('population', 0) + to_node.get('population', 0)) / 1000000
            
            critical_factor = 1
            if (isinstance(road['from'], str) and road['from'].startswith('F')) or \
               (isinstance(road['to'], str) and road['to'].startswith('F')):
                critical_factor = 2
            
            condition = road['condition']
            improvement_possible = (10 - condition) * 0.5  # 0.5 point improvement per million
            
            road['value'] = traffic * (1 + population_factor) * critical_factor * improvement_possible
            road['cost'] = (10 - condition) * 5  # million EGP to improve to condition 10
        
        # 0/1 Knapsack DP solution
        n = len(roads)
        dp = [[0] * (budget + 1) for _ in range(n + 1)]
        
        for i in range(1, n + 1):
            road = roads[i-1]
            for w in range(1, budget + 1):
                if road['cost'] <= w:
                    dp[i][w] = max(dp[i-1][w], dp[i-1][w - road['cost']] + road['value'])
                else:
                    dp[i][w] = dp[i-1][w]
        
        # Backtrack to find selected roads
        selected = []
        w = budget
        total_cost = 0
        total_value = 0
        
        for i in range(n, 0, -1):
            if dp[i][w] != dp[i-1][w]:
                road = roads[i-1]
                selected.append(road)
                w -= road['cost']
                total_cost += road['cost']
                total_value += road['value']
        
        return {
            'selected_roads': selected,
            'total_cost': total_cost,
            'total_value': total_value,
            'average_improvement': sum(10 - r['condition'] for r in selected) / len(selected) if selected else 0
        }
    
    def _estimate_improvement(self, metro_schedules, bus_schedules, maintenance_plan):
        # Estimate overall improvement from optimizations
        metro_improvement = 0
        for metro in metro_schedules:
            if metro['current_trains'] > 0:
                metro_improvement += (metro['trains_needed'] / metro['current_trains']) * 0.2  # up to 20% improvement
        
        bus_improvement = 0
        for bus in bus_schedules:
            if bus['current_buses'] > 0:
                utilization = bus['utilization']
                if utilization > 1:
                    improvement = (bus['optimal_buses'] / bus['current_buses']) * 0.15  # up to 15% improvement
                    bus_improvement += improvement
        
        road_improvement = maintenance_plan['average_improvement'] * 0.05 if maintenance_plan['selected_roads'] else 0
        
        total_improvement = min(0.5, (metro_improvement + bus_improvement + road_improvement) / 3)
        
        return {
            'metro': metro_improvement,
            'bus': bus_improvement,
            'road': road_improvement,
            'total': total_improvement
        }