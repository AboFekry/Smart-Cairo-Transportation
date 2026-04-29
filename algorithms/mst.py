class MSTOptimizer:
    def __init__(self, cairo_data):
        self.data = cairo_data
    
    def optimize_network(self, use_prim=True, prioritize_population=True):
        # Prepare graph data
        graph = self._prepare_graph(prioritize_population)
        
        if use_prim:
            return self._prim_mst(graph)
        else:
            return self._kruskal_mst(graph)
    
    def _prepare_graph(self, prioritize_population):
        # Create a graph representation with weighted edges
        graph = {'nodes': [], 'edges': []}
        
        # Add all locations as nodes
        for loc in self.data.neighborhoods + self.data.facilities:
            graph['nodes'].append({
                'id': loc['id'],
                'name': loc.get('name', ''),
                'population': loc.get('population', 0),
                'type': loc.get('type', ''),
                'x': loc['x'],
                'y': loc['y']
            })
        
        # Add existing roads with weights based on condition and capacity
        for road in self.data.existing_roads:
            from_node = next(n for n in graph['nodes'] if n['id'] == road['from'])
            to_node = next(n for n in graph['nodes'] if n['id'] == road['to'])
            
            # Weight calculation based on distance, condition, and capacity
            weight = road['distance'] * (1 + (10 - road['condition'])/10)
            
            if prioritize_population:
                pop_factor = (from_node['population'] + to_node['population']) / 1000000
                weight = weight / (1 + pop_factor)
            
            graph['edges'].append({
                'from': road['from'],
                'to': road['to'],
                'weight': weight,
                'existing': True,
                'distance': road['distance'],
                'capacity': road['capacity'],
                'condition': road['condition']
            })
        
        # Add potential roads with weights considering construction cost
        for road in self.data.potential_roads:
            from_node = next(n for n in graph['nodes'] if n['id'] == road['from'])
            to_node = next(n for n in graph['nodes'] if n['id'] == road['to'])
            
            weight = road['distance'] * (1 + road['cost']/1000)
            
            if prioritize_population:
                pop_factor = (from_node['population'] + to_node['population']) / 1000000
                weight = weight / (1 + pop_factor)
            
            graph['edges'].append({
                'from': road['from'],
                'to': road['to'],
                'weight': weight,
                'existing': False,
                'distance': road['distance'],
                'capacity': road['capacity'],
                'cost': road['cost']
            })
        
        return graph
    
    def _prim_mst(self, graph):
        # Implementation of Prim's algorithm
        nodes = graph['nodes']
        edges = graph['edges']
        
        if not nodes:
            return {'nodes': [], 'edges': []}
        
        mst_nodes = [nodes[0]['id']]
        mst_edges = []
        
        while len(mst_nodes) < len(nodes):
            candidate_edges = [
                e for e in edges 
                if (e['from'] in mst_nodes and e['to'] not in mst_nodes) or 
                   (e['to'] in mst_nodes and e['from'] not in mst_nodes)
            ]
            
            if not candidate_edges:
                break  # Disconnected graph
                
            min_edge = min(candidate_edges, key=lambda x: x['weight'])
            mst_edges.append(min_edge)
            
            if min_edge['from'] not in mst_nodes:
                mst_nodes.append(min_edge['from'])
            else:
                mst_nodes.append(min_edge['to'])
        
        return {
            'nodes': [n for n in nodes if n['id'] in mst_nodes],
            'edges': mst_edges,
            'total_distance': sum(e['distance'] for e in mst_edges),
            'total_cost': sum(e.get('cost', 0) for e in mst_edges if not e['existing']),
            'critical_facilities_connected': self._check_critical_facilities(mst_edges)
        }
    
    def _kruskal_mst(self, graph):
        # Implementation of Kruskal's algorithm
        nodes = graph['nodes']
        edges = sorted(graph['edges'], key=lambda x: x['weight'])
        
        parent = {n['id']: n['id'] for n in nodes}
        
        def find(u):
            while parent[u] != u:
                parent[u] = parent[parent[u]]
                u = parent[u]
            return u
        
        def union(u, v):
            u_root = find(u)
            v_root = find(v)
            if u_root == v_root:
                return False
            parent[v_root] = u_root
            return True
        
        mst_edges = []
        for edge in edges:
            if union(edge['from'], edge['to']):
                mst_edges.append(edge)
                if len(mst_edges) == len(nodes) - 1:
                    break
        
        mst_nodes = list(set([e['from'] for e in mst_edges] + [e['to'] for e in mst_edges]))
        
        return {
            'nodes': [n for n in nodes if n['id'] in mst_nodes],
            'edges': mst_edges,
            'total_distance': sum(e['distance'] for e in mst_edges),
            'total_cost': sum(e.get('cost', 0) for e in mst_edges if not e['existing']),
            'critical_facilities_connected': self._check_critical_facilities(mst_edges)
        }
    
    def _check_critical_facilities(self, edges):
        critical_facilities = ['F1', 'F2', 'F9', 'F10']  # Airport, Railway, Hospitals
        connected_nodes = set()
        
        for edge in edges:
            connected_nodes.add(edge['from'])
            connected_nodes.add(edge['to'])
        
        return all(f in connected_nodes for f in critical_facilities)