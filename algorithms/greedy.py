
class TrafficSignalOptimizer:
    def __init__(self, cairo_data):
        self.data = cairo_data
    
    def optimize_signals(self, intersections, time_of_day='morning'):
        # Greedy algorithm for traffic signal optimization
        if not intersections:
            intersections = self._identify_major_intersections()
        
        optimized_signals = []
        
        for intersection in intersections:
            # Get all roads connected to this intersection
            connected_roads = [
                r for r in self.data.existing_roads 
                if r['from'] == intersection or r['to'] == intersection
            ]
            
            if not connected_roads:
                continue
            
            # Calculate traffic flow for each approach
            approaches = []
            for road in connected_roads:
                other_end = road['to'] if road['from'] == intersection else road['from']
                traffic = self.data.get_road_traffic(intersection, other_end, time_of_day)
                capacity = road['capacity']
                congestion = traffic / capacity
                
                approaches.append({
                    'from': other_end,
                    'name': self.data.get_location_name(other_end),
                    'traffic': traffic,
                    'congestion': congestion,
                    'priority': 1  # Default priority
                })
            
            # Assign priorities based on traffic and type of road
            for approach in approaches:
                # Higher priority for roads with more traffic
                approach['priority'] += approach['congestion'] * 2
                
                # Check if road leads to critical facility
                other_end = approach['from']
                loc = self.data.get_neighborhood(other_end) or self.data.get_facility(other_end)
                if loc and loc.get('type') in ['Medical', 'Airport', 'Government']:
                    approach['priority'] += 2
            
            # Sort by priority (greedy choice)
            approaches.sort(key=lambda x: -x['priority'])
            
            # Calculate green time allocation (simplified)
            total_priority = sum(a['priority'] for a in approaches)
            cycle_time = 120  # seconds
            min_green = 15  # seconds
            
            signal_phases = []
            remaining_time = cycle_time - (min_green * len(approaches))
            
            for approach in approaches:
                if total_priority > 0:
                    extra_time = (approach['priority'] / total_priority) * remaining_time
                else:
                    extra_time = 0
                
                green_time = min_green + extra_time
                signal_phases.append({
                    'approach': approach['from'],
                    'approach_name': approach['name'],
                    'green_time': green_time,
                    'priority': approach['priority'],
                    'congestion': approach['congestion']
                })
            
            optimized_signals.append({
                'intersection': intersection,
                'intersection_name': self.data.get_location_name(intersection),
                'approaches': len(connected_roads),
                'signal_phases': signal_phases,
                'cycle_time': cycle_time
            })
        
        return optimized_signals
    
    def _identify_major_intersections(self):
        # Identify intersections with highest traffic (greedy approach)
        intersection_counts = {}
        
        for road in self.data.existing_roads:
            intersection_counts[road['from']] = intersection_counts.get(road['from'], 0) + 1
            intersection_counts[road['to']] = intersection_counts.get(road['to'], 0) + 1
        
        # Get top 10 intersections with most connections
        sorted_intersections = sorted(intersection_counts.items(), key=lambda x: -x[1])
        top_intersections = [x[0] for x in sorted_intersections[:10]]
        
        return top_intersections
    
    def emergency_preemption(self, emergency_route, time_of_day='morning'):
        # Greedy approach to prioritize emergency vehicle along its route
        if not emergency_route or len(emergency_route) < 2:
            return []
        
        preemption_plan = []
        
        for i in range(len(emergency_route) - 1):
            current = emergency_route[i]
            next_loc = emergency_route[i+1]
            
            # Find all intersections along this segment
            intersections = self._find_intersections_between(current, next_loc)
            
            for intersection in intersections:
                # Get current signal plan
                signal_plan = self.optimize_signals([intersection], time_of_day)
                if not signal_plan:
                    continue
                
                current_plan = signal_plan[0]
                
                # Find the approach the emergency vehicle is coming from
                coming_from = current if i > 0 else None
                if i == 0:
                    # First segment, find which approach leads to the starting point
                    roads = [r for r in self.data.existing_roads 
                            if (r['from'] == intersection and r['to'] == current) or 
                               (r['to'] == intersection and r['from'] == current)]
                    if roads:
                        coming_from = current
                
                # Modify the signal plan to prioritize this approach
                modified_phases = []
                found_approach = False
                
                for phase in current_plan['signal_phases']:
                    if phase['approach'] == coming_from:
                        # Give this approach maximum green time
                        modified_phases.append({
                            **phase,
                            'green_time': current_plan['cycle_time'] * 0.7,  # 70% of cycle
                            'emergency_priority': True
                        })
                        found_approach = True
                    else:
                        # Reduce other phases
                        modified_phases.append({
                            **phase,
                            'green_time': phase['green_time'] * 0.3  # Reduce to 30%
                        })
                
                if found_approach:
                    preemption_plan.append({
                        'intersection': intersection,
                        'intersection_name': current_plan['intersection_name'],
                        'original_plan': current_plan,
                        'modified_plan': {
                            **current_plan,
                            'signal_phases': modified_phases
                        },
                        'emergency_approach': coming_from,
                        'emergency_approach_name': self.data.get_location_name(coming_from) if coming_from else "Unknown",
                        'time_saved': self._estimate_time_saved(current_plan, modified_phases, coming_from)
                    })
        
        return preemption_plan
    
    def _find_intersections_between(self, start, end):
        # Find all intersections between two locations along the direct road
        intersections = set()
        
        # Check if there's a direct road
        direct_road = next((r for r in self.data.existing_roads 
                          if (r['from'] == start and r['to'] == end) or 
                             (r['from'] == end and r['to'] == start)), None)
        
        if direct_road:
            # For simplicity, assume no intermediate intersections on direct roads
            # In a real implementation, we might have more detailed road segments
            return []
        
        # If no direct road, find path through intersections
        visited = set()
        queue = [start]
        
        while queue:
            current = queue.pop(0)
            if current == end:
                break
                
            if current in visited:
                continue
                
            visited.add(current)
            
            # Get all connected roads
            connected_roads = [r for r in self.data.existing_roads 
                             if r['from'] == current or r['to'] == current]
            
            for road in connected_roads:
                neighbor = road['to'] if road['from'] == current else road['from']
                
                # Count connections to identify intersections
                connections = [r for r in self.data.existing_roads 
                              if r['from'] == neighbor or r['to'] == neighbor]
                
                if len(connections) > 2:  # More than just incoming and outgoing
                    intersections.add(neighbor)
                
                if neighbor not in visited:
                    queue.append(neighbor)
        
        return list(intersections)
    
    def _estimate_time_saved(self, original_plan, modified_phases, approach):
        # Estimate time saved by emergency preemption
        if not approach:
            return 0
        
        original_wait = 0
        modified_wait = 0
        
        # Find the approach in both plans
        original_phase = next((p for p in original_plan['signal_phases'] if p['approach'] == approach), None)
        modified_phase = next((p for p in modified_phases if p['approach'] == approach), None)
        
        if not original_phase or not modified_phase:
            return 0
        
        # Calculate average wait time reduction
        original_ratio = original_phase['green_time'] / original_plan['cycle_time']
        modified_ratio = modified_phase['green_time'] / original_plan['cycle_time']
        
        # Average wait time is roughly cycle_time * (1 - ratio)^2 / (2 * (1 - ratio))
        # Simplified to cycle_time * (1 - ratio) / 2
        original_wait = original_plan['cycle_time'] * (1 - original_ratio) / 2
        modified_wait = original_plan['cycle_time'] * (1 - modified_ratio) / 2
        
        return max(0, original_wait - modified_wait)