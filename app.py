from flask import Flask, render_template, jsonify, request
from data.cairo_data import CairoData
from algorithms.shortest_path import ShortestPathFinder
from algorithms.mst import MSTOptimizer
from algorithms.dynamic_prog import PublicTransportOptimizer
from algorithms.greedy import TrafficSignalOptimizer
import os
import sys

app = Flask(__name__)

# Fix paths for Vercel
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Initialize data with correct path
cairo_data = CairoData()
try:
    cairo_data.load_data()
except Exception as e:
    print(f"Error loading data: {e}")
    # You might need to adjust the load_data method to use BASE_DIR

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Template error: {e}", 500

@app.route('/api/road_network', methods=['GET'])
def get_road_network():
    try:
        return jsonify({
            'neighborhoods': cairo_data.neighborhoods,
            'facilities': cairo_data.facilities,
            'existing_roads': cairo_data.existing_roads,
            'potential_roads': cairo_data.potential_roads
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/shortest_path', methods=['POST'])
def find_shortest_path():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        start = data.get('start')
        end = data.get('end')
        time_of_day = data.get('time_of_day', 'morning')
        
        if not start or not end:
            return jsonify({'error': 'Missing start or end location'}), 400
        
        if str(start) == str(end):
            return jsonify({'error': 'Start and end locations cannot be the same'}), 400
        
        if not cairo_data.location_exists(start):
            return jsonify({'error': f'Start location ID {start} not found'}), 404
        
        if not cairo_data.location_exists(end):
            return jsonify({'error': f'End location ID {end} not found'}), 404
        
        path_finder = ShortestPathFinder(cairo_data)
        result = path_finder.find_shortest_path(str(start), str(end), time_of_day)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Failed to calculate path: {str(e)}'}), 500

@app.route('/api/optimize_network', methods=['POST'])
def optimize_network():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        optimizer = MSTOptimizer(cairo_data)
        result = optimizer.optimize_network(
            use_prim=data.get('algorithm', 'prim') == 'prim',
            prioritize_population=data.get('prioritize_population', True)
        )
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Network optimization failed: {str(e)}'}), 500

@app.route('/api/optimize_transport', methods=['POST'])
def optimize_transport():
    try:
        optimizer = PublicTransportOptimizer(cairo_data)
        result = optimizer.optimize_schedules()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Transport optimization failed: {str(e)}'}), 500

@app.route('/api/optimize_signals', methods=['POST'])
def optimize_signals():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        optimizer = TrafficSignalOptimizer(cairo_data)
        result = optimizer.optimize_signals(
            intersections=data.get('intersections', []),
            time_of_day=data.get('time_of_day', 'morning')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Signal optimization failed: {str(e)}'}), 500

@app.route('/api/emergency_route', methods=['POST'])
def find_emergency_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        start = data.get('start')
        end = data.get('end')
        time_of_day = data.get('time_of_day', 'morning')
        
        if not start or not end:
            return jsonify({'error': 'Missing start or end location'}), 400
        
        if str(start) == str(end):
            return jsonify({'error': 'Start and end locations cannot be the same'}), 400
        
        if not cairo_data.location_exists(start):
            return jsonify({'error': f'Start location ID {start} not found'}), 404
        
        if not cairo_data.location_exists(end):
            return jsonify({'error': f'End location ID {end} not found'}), 404
        
        end_facility = cairo_data.get_facility(end)
        if not end_facility or 'Medical' not in end_facility['type']:
            return jsonify({'error': 'Destination must be a medical facility'}), 400
        
        path_finder = ShortestPathFinder(cairo_data)
        result = path_finder.emergency_route(str(start), str(end), time_of_day)
        
        if result.get('path'):
            path_coords = []
            for loc_id in result['path']:
                loc = cairo_data.get_neighborhood(loc_id) or cairo_data.get_facility(loc_id)
                if loc:
                    path_coords.append({'lat': loc['y'], 'lng': loc['x']})
            result['path_coords'] = path_coords
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Failed to calculate emergency route: {str(e)}'}), 500



handler = app