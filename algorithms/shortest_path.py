import heapq
import math

class ShortestPathFinder:
    def __init__(self, cairo_data):
        self.data = cairo_data
    
    def find_shortest_path(self, start, end, time_of_day='morning'):
        return self._find_path(start, end, time_of_day, emergency=False)
    
    def emergency_route(self, start, end, time_of_day='morning'):
        return self._find_path(start, end, time_of_day, emergency=True)
    
    def _find_path(self, start, end, time_of_day, emergency):
        graph = self._prepare_graph(time_of_day, emergency)
        
        start = str(start)
        end = str(end)
        
        if start not in graph or end not in graph:
            return {'path': [], 'distance': 0, 'time': 0, 'error': 'Invalid start or end location'}
        
        # Dijkstra's algorithm with priority queue
        distances = {node: float('inf') for node in graph}
        distances[start] = 0
        previous = {node: None for node in graph}
        visited = set()
        
        priority_queue = [(0, start)]
        
        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)
            
            if current_node in visited:
                continue
                
            visited.add(current_node)
            
            if current_node == end:
                break
                
            for neighbor, edge_data in graph[current_node].items():
                distance = current_distance + edge_data['weight']
                
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current_node
                    heapq.heappush(priority_queue, (distance, neighbor))
        
        if distances[end] == float('inf'):
            # Try again with relaxed constraints if no path found
            if emergency:
                return self._find_path(start, end, time_of_day, emergency=False)
            return {'path': [], 'distance': 0, 'time': 0, 'error': 'No path found'}
        
        # Reconstruct path
        path = []
        current = end
        while current is not None:
            path.append(current)
            current = previous.get(current)
        path.reverse()
        
        # Calculate path details
        path_details = self._get_path_details(path, time_of_day, emergency)
        total_distance = path_details['total_distance']
        total_time = sum(step['time'] for step in path_details['steps']) if path_details['steps'] else 0
        
        return {
            'path': path,
            'distance': total_distance,
            'time': total_time,
            'path_details': path_details
        }
    
    def _prepare_graph(self, time_of_day, emergency):
        graph = {}
        
        # Add all nodes
        for loc in self.data.neighborhoods + self.data.facilities:
            graph[str(loc['id'])] = {}
        
        # Add all edges
        for road in self.data.existing_roads:
            from_id = str(road['from'])
            to_id = str(road['to'])
            
            if from_id not in graph or to_id not in graph:
                continue
                
            traffic = self.data.get_road_traffic(from_id, to_id, time_of_day)
            capacity = road['capacity']
            congestion = min(traffic / capacity, 2.0)  # Cap congestion at 200%
            
            # Calculate speed
            if emergency:
                base_speed = 80  # km/h for emergency vehicles
                congestion_factor = max(0.4, 1 - (congestion * 0.3))  # 40-100% of speed
            else:
                base_speed = 30  # km/h for regular traffic
                congestion_factor = max(0.2, 1 - (congestion * 0.4))  # 20-100% of speed
            
            speed = base_speed * congestion_factor
            
            # Road condition penalty (1-10, 10 is best)
            condition_factor = 1 + ((10 - road['condition']) * 0.05)  # 1.0-1.45 multiplier
            
            # Calculate weight (time in hours)
            weight = (road['distance'] / speed) * condition_factor if speed > 0 else float('inf')
            
            # Add edge in both directions
            graph[from_id][to_id] = {
                'weight': weight,
                'distance': road['distance'],
                'traffic': traffic,
                'capacity': capacity,
                'condition': road['condition']
            }
            graph[to_id][from_id] = {
                'weight': weight,
                'distance': road['distance'],
                'traffic': traffic,
                'capacity': capacity,
                'condition': road['condition']
            }
        
        return graph
    
    def _get_location_coords(self, loc_id):
        loc = self.data.get_neighborhood(loc_id) or self.data.get_facility(loc_id)
        if loc:
            return {'x': loc['x'], 'y': loc['y']}
        return None
    
    def _get_path_details(self, path, time_of_day, emergency=False):
        details = []
        total_distance = 0
        valid_steps = 0

        for i in range(len(path) - 1):
            from_id = path[i]
            to_id = path[i+1]
            
            road = self.data.get_road_between(from_id, to_id)
            if not road:
                continue
                
            distance = road['distance']
            total_distance += distance
            
            traffic = self.data.get_road_traffic(from_id, to_id, time_of_day)
            capacity = road['capacity']
            congestion = min(traffic / capacity, 2.0)  # Cap at 200% congestion
            
            # Calculate time
            if emergency:
                speed = 80 * max(0.4, 1 - (congestion * 0.3))  # 40-100% of speed
            else:
                speed = 30 * max(0.2, 1 - (congestion * 0.4))  # 20-100% of speed
            
            condition_factor = 1 + ((10 - road['condition']) * 0.05)
            time = (distance / speed) * condition_factor * 60  # in minutes
            
            details.append({
                'from': from_id,
                'to': to_id,
                'from_name': self.data.get_location_name(from_id),
                'to_name': self.data.get_location_name(to_id),
                'distance': distance,
                'condition': road['condition'],
                'traffic': traffic,
                'capacity': capacity,
                'congestion': congestion,
                'time': time
            })
            valid_steps += 1

        return {
            'steps': details,
            'total_distance': total_distance,
            'average_congestion': sum(d['congestion'] for d in details) / valid_steps if valid_steps > 0 else 0
        }