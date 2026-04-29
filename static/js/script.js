// Global variables
let networkMap, routeMap, emergencyMap, transportMap, signalMap;
let neighborhoods = [];
let facilities = [];
let existingRoads = [];
let potentialRoads = [];

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Setup navigation
    setupNavigation();
    
    // Load initial data
    loadInitialData();
    
    // Setup forms
    setupForms();
});

function setupNavigation() {
    // Handle navigation clicks
    document.querySelectorAll('[data-section]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const section = this.getAttribute('data-section');
            
            // Hide all sections
            document.querySelectorAll('.content-section').forEach(sec => {
                sec.style.display = 'none';
            });
            
            // Show selected section
            document.getElementById(`${section}-section`).style.display = 'block';
            
            // Update active nav link
            document.querySelectorAll('.nav-link').forEach(navLink => {
                navLink.classList.remove('active');
            });
            this.classList.add('active');
            
            // Initialize map if needed
            if (section === 'network' && !networkMap) {
                initNetworkMap();
            } else if (section === 'traffic' && !routeMap) {
                initRouteMap();
            } else if (section === 'emergency' && !emergencyMap) {
                initEmergencyMap();
            } else if (section === 'public' && !transportMap) {
                initTransportMap();
            } else if (section === 'signals' && !signalMap) {
                initSignalMap();
            }
        });
    });
}

function loadInitialData() {
    fetch('/api/road_network')
        .then(response => response.json())
        .then(data => {
            neighborhoods = data.neighborhoods;
            facilities = data.facilities;
            existingRoads = data.existing_roads;
            potentialRoads = data.potential_roads;
            
            // Populate location dropdowns
            populateLocationDropdowns();
            
            // Initialize the first map
            initNetworkMap();
        })
        .catch(error => {
            console.error('Error loading initial data:', error);
        });
}

function populateLocationDropdowns() {
    const locationDropdowns = [
        'start-location', 'end-location', 
        'emergency-start', 'emergency-end',
        'intersections-select'
    ];
    
    locationDropdowns.forEach(dropdownId => {
        const dropdown = document.getElementById(dropdownId);
        if (!dropdown) return;
        
        // Clear existing options
        dropdown.innerHTML = '';
        
        // Add neighborhoods
        const neighborhoodGroup = document.createElement('optgroup');
        neighborhoodGroup.label = 'Neighborhoods';
        neighborhoods.forEach(loc => {
            const option = document.createElement('option');
            option.value = loc.id;
            option.textContent = `${loc.name} (${loc.type})`;
            neighborhoodGroup.appendChild(option);
        });
        dropdown.appendChild(neighborhoodGroup);
        
        // Add facilities
        const facilityGroup = document.createElement('optgroup');
        facilityGroup.label = 'Important Facilities';
        facilities.forEach(loc => {
            const option = document.createElement('option');
            option.value = loc.id;
            option.textContent = `${loc.name} (${loc.type})`;
            facilityGroup.appendChild(option);
        });
        dropdown.appendChild(facilityGroup);
    });
    
    // For emergency end locations, show only medical facilities
    const emergencyEnd = document.getElementById('emergency-end');
    if (emergencyEnd) {
        emergencyEnd.innerHTML = '';
        facilities.filter(f => f.type.includes('Medical')).forEach(loc => {
            const option = document.createElement('option');
            option.value = loc.id;
            option.textContent = `${loc.name} (${loc.type})`;
            emergencyEnd.appendChild(option);
        });
    }
}

function setupForms() {
    // MST Form
    document.getElementById('mst-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const data = {
            algorithm: formData.get('algorithm'),
            prioritize_population: formData.get('prioritize_population') === 'on'
        };
        
        fetch('/api/optimize_network', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            displayMSTResults(data);
            updateNetworkMap(data);
        })
        .catch(error => {
            console.error('Error optimizing network:', error);
        });
    });
    
    // Route Form
    document.getElementById('route-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const data = {
            start: formData.get('start'),
            end: formData.get('end'),
            time_of_day: formData.get('time_of_day')
        };
        
        fetch('/api/shortest_path', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            displayRouteResults(data);
            updateRouteMap(data);
        })
        .catch(error => {
            console.error('Error finding shortest path:', error);
        });
    });
    
    // Emergency Route Form
    // Update the emergency form submission
// Update the emergency form submission
document.getElementById('emergency-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData(this);
    const start = formData.get('start');
    const end = formData.get('end');
    
    // Validate hospital selection
    const hospitalIds = facilities.filter(f => f.type.includes('Medical')).map(f => f.id);
    if (!hospitalIds.includes(end)) {
        document.getElementById('emergency-results').innerHTML = `
            <div class="alert alert-danger">
                Please select a valid hospital as the destination
            </div>
        `;
        return;
    }
    
    fetch('/api/emergency_route', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            start: start,
            end: end,
            time_of_day: formData.get('time_of_day')
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { throw new Error(err.error || 'Network error'); });
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        displayEmergencyResults(data);
        updateEmergencyMap(data);
    })
    .catch(error => {
        console.error('Emergency route error:', error);
        const resultsDiv = document.getElementById('emergency-results');
        resultsDiv.innerHTML = `
            <div class="alert alert-danger">
                ${error.message || 'Failed to calculate emergency route'}
                ${error.message.includes('No path found') ? `
                <div class="mt-2">
                    <p>Possible solutions:</p>
                    <ul>
                        <li>Try a different hospital</li>
                        <li>Check if your starting location is properly connected</li>
                        <li>Report this location to city planners</li>
                    </ul>
                </div>
                ` : ''}
            </div>
        `;
    });
});
    
    // Public Transport Optimization Button
    document.getElementById('optimize-transport-btn').addEventListener('click', function() {
        fetch('/api/optimize_transport', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            displayTransportResults(data);
            updateTransportMap(data);
        })
        .catch(error => {
            console.error('Error optimizing public transport:', error);
        });
    });
    
    // Signal Optimization Form
    document.getElementById('signal-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const intersections = Array.from(document.getElementById('intersections-select').selectedOptions)
            .map(option => option.value);
        
        const data = {
            intersections: intersections,
            time_of_day: formData.get('time_of_day')
        };
        
        fetch('/api/optimize_signals', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            displaySignalResults(data);
            updateSignalMap(data);
        })
        .catch(error => {
            console.error('Error optimizing signals:', error);
        });
    });
}

// Map Initialization Functions
function initNetworkMap() {
    networkMap = L.map('network-map').setView([30.04, 31.24], 11);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(networkMap);
    
    // Add existing roads
    existingRoads.forEach(road => {
        const fromLoc = findLocation(road.from);
        const toLoc = findLocation(road.to);
        
        if (fromLoc && toLoc) {
            L.polyline(
                [[fromLoc.y, fromLoc.x], [toLoc.y, toLoc.x]],
                {color: 'blue', weight: 3}
            ).addTo(networkMap).bindPopup(
                `Road from ${fromLoc.name} to ${toLoc.name}<br>
                Distance: ${road.distance} km<br>
                Capacity: ${road.capacity} vehicles/hour<br>
                Condition: ${road.condition}/10`
            );
        }
    });
    
    // Add neighborhoods
    neighborhoods.forEach(loc => {
        L.circleMarker([loc.y, loc.x], {
            radius: 5 + (loc.population / 100000),
            fillColor: loc.type === 'Residential' ? 'green' : 
                      loc.type === 'Business' ? 'blue' : 'orange',
            color: '#000',
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8
        }).bindPopup(`<b>${loc.name}</b><br>Type: ${loc.type}<br>Population: ${loc.population}`)
        .addTo(networkMap);
    });
    
    // Add facilities
    facilities.forEach(loc => {
        L.circleMarker([loc.y, loc.x], {
            radius: 8,
            fillColor: 'red',
            color: '#000',
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8
        }).bindPopup(`<b>${loc.name}</b><br>Type: ${loc.type}`)
        .addTo(networkMap);
    });
}

function initRouteMap() {
    routeMap = L.map('route-map').setView([30.04, 31.24], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(routeMap);
    
    // Add existing roads
    existingRoads.forEach(road => {
        const fromLoc = findLocation(road.from);
        const toLoc = findLocation(road.to);
        
        if (fromLoc && toLoc) {
            L.polyline(
                [[fromLoc.y, fromLoc.x], [toLoc.y, toLoc.x]],
                {color: 'gray', weight: 2, opacity: 0.7}
            ).addTo(routeMap);
        }
    });
}

function initEmergencyMap() {
    emergencyMap = L.map('emergency-map').setView([30.04, 31.24], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(emergencyMap);
    
    // Add hospitals
    facilities.filter(f => f.type.includes('Medical')).forEach(loc => {
        L.circleMarker([loc.y, loc.x], {
            radius: 10,
            fillColor: 'red',
            color: '#000',
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8
        }).bindPopup(`<b>${loc.name}</b><br>Medical Facility`)
        .addTo(emergencyMap);
    });
}

function initTransportMap() {
    transportMap = L.map('transport-map').setView([30.04, 31.24], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(transportMap);
}

function initSignalMap() {
    signalMap = L.map('signal-map').setView([30.04, 31.24], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(signalMap);
}

// Helper Functions
function findLocation(id) {
    const loc = neighborhoods.find(n => n.id === id) || facilities.find(f => f.id === id);
    return loc ? {name: loc.name, x: loc.x, y: loc.y} : null;
}

// Result Display Functions
function displayMSTResults(data) {
    const resultsDiv = document.getElementById('mst-results');
    resultsDiv.innerHTML = '';
    
    const totalCost = data.total_cost.toLocaleString();
    const totalDistance = data.total_distance.toFixed(1);
    
    const html = `
        <div class="result-item">
            <h6>Optimized Road Network</h6>
            <p><strong>Total Distance:</strong> <span class="result-value">${totalDistance} km</span></p>
            <p><strong>Construction Cost:</strong> <span class="result-value">${totalCost} million EGP</span></p>
            <p><strong>Critical Facilities Connected:</strong> 
                <span class="result-value">${data.critical_facilities_connected ? 'Yes' : 'No'}</span>
            </p>
            <p><strong>Roads Included:</strong> ${data.edges.length}</p>
        </div>
        
        <div class="mt-3">
            <h6>New Roads Recommended</h6>
            <ul class="list-group">
                ${data.edges.filter(e => !e.existing).map(road => {
                    const fromName = findLocation(road.from)?.name || road.from;
                    const toName = findLocation(road.to)?.name || road.to;
                    return `
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            ${fromName} to ${toName}
                            <span class="badge bg-primary rounded-pill">${road.distance} km</span>
                        </li>
                    `;
                }).join('')}
            </ul>
        </div>
    `;
    
    resultsDiv.innerHTML = html;
}

function updateNetworkMap(data) {
    // Clear existing layers except base map
    networkMap.eachLayer(layer => {
        if (!layer._url) {  // Keep only tile layers
            networkMap.removeLayer(layer);
        }
    });
    
    // Add all locations
    neighborhoods.forEach(loc => {
        L.circleMarker([loc.y, loc.x], {
            radius: 5 + (loc.population / 100000),
            fillColor: loc.type === 'Residential' ? 'green' : 
                      loc.type === 'Business' ? 'blue' : 'orange',
            color: '#000',
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8
        }).bindPopup(`<b>${loc.name}</b><br>Type: ${loc.type}<br>Population: ${loc.population}`)
        .addTo(networkMap);
    });
    
    facilities.forEach(loc => {
        L.circleMarker([loc.y, loc.x], {
            radius: 8,
            fillColor: 'red',
            color: '#000',
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8
        }).bindPopup(`<b>${loc.name}</b><br>Type: ${loc.type}`)
        .addTo(networkMap);
    });
    
    // Add MST edges
    data.edges.forEach(road => {
        const fromLoc = findLocation(road.from);
        const toLoc = findLocation(road.to);
        
        if (fromLoc && toLoc) {
            const color = road.existing ? 'blue' : 'green';
            const dashArray = road.existing ? null : '5, 5';
            
            L.polyline(
                [[fromLoc.y, fromLoc.x], [toLoc.y, toLoc.x]],
                {color: color, weight: 3, dashArray: dashArray}
            ).bindPopup(
                `Road from ${fromLoc.name} to ${toLoc.name}<br>
                Distance: ${road.distance} km<br>
                ${road.existing ? 'Existing' : 'Proposed'}`
            ).addTo(networkMap);
        }
    });
}

function displayRouteResults(data) {
    const resultsDiv = document.getElementById('route-results');
    resultsDiv.innerHTML = '';
    
    if (data.error) {
        resultsDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
        return;
    }
    
    const totalTime = data.time.toFixed(1);
    const totalDistance = data.distance.toFixed(1);
    const avgCongestion = (data.path_details.average_congestion * 100).toFixed(1);
    
    const html = `
        <div class="result-item">
            <h6>Optimal Route</h6>
            <p><strong>Total Distance:</strong> <span class="result-value">${totalDistance} km</span></p>
            <p><strong>Estimated Time:</strong> <span class="result-value">${totalTime} minutes</span></p>
            <p><strong>Average Congestion:</strong> <span class="result-value">${avgCongestion}%</span></p>
        </div>
        
        <div class="mt-3">
            <h6>Route Steps</h6>
            ${data.path_details.steps.map(step => `
                <div class="route-step">
                    <strong>${step.from_name}</strong> to <strong>${step.to_name}</strong><br>
                    Distance: ${step.distance} km | Time: ${step.time.toFixed(1)} min<br>
                    Traffic: ${step.traffic}/${step.capacity} (${(step.congestion * 100).toFixed(1)}% congestion)
                </div>
            `).join('')}
        </div>
    `;
    
    resultsDiv.innerHTML = html;
}

function updateRouteMap(data) {
    // Clear existing layers except base map
    routeMap.eachLayer(layer => {
        if (!layer._url) {  // Keep only tile layers
            routeMap.removeLayer(layer);
        }
    });
    
    // Add all roads (gray background)
    existingRoads.forEach(road => {
        const fromLoc = findLocation(road.from);
        const toLoc = findLocation(road.to);
        
        if (fromLoc && toLoc) {
            L.polyline(
                [[fromLoc.y, fromLoc.x], [toLoc.y, toLoc.x]],
                {color: 'gray', weight: 2, opacity: 0.5}
            ).addTo(routeMap);
        }
    });
    
    // Highlight the optimal path
    if (data.path && data.path.length > 1) {
        const pathCoords = [];
        
        for (let i = 0; i < data.path.length - 1; i++) {
            const fromId = data.path[i];
            const toId = data.path[i+1];
            
            const fromLoc = findLocation(fromId);
            const toLoc = findLocation(toId);
            
            if (fromLoc && toLoc) {
                pathCoords.push([fromLoc.y, fromLoc.x]);
                pathCoords.push([toLoc.y, toLoc.x]);
                
                // Add markers for start and end
                if (i === 0) {
                    L.marker([fromLoc.y, fromLoc.x], {
                        icon: L.divIcon({
                            className: 'start-marker',
                            html: '🟢',
                            iconSize: [20, 20]
                        })
                    }).bindPopup(`<b>Start:</b> ${fromLoc.name}`)
                    .addTo(routeMap);
                }
                
                if (i === data.path.length - 2) {
                    L.marker([toLoc.y, toLoc.x], {
                        icon: L.divIcon({
                            className: 'end-marker',
                            html: '🔴',
                            iconSize: [20, 20]
                        })
                    }).bindPopup(`<b>Destination:</b> ${toLoc.name}`)
                    .addTo(routeMap);
                }
            }
        }
        
        // Draw the path
        L.polyline(pathCoords, {
            color: 'blue',
            weight: 5,
            opacity: 0.7
        }).addTo(routeMap);
        
        // Fit bounds to show the entire path
        const bounds = L.latLngBounds(pathCoords);
        routeMap.fitBounds(bounds, {padding: [50, 50]});
    }
}

function displayEmergencyResults(data) {
    const resultsDiv = document.getElementById('emergency-results');
    resultsDiv.innerHTML = '';
    
    if (data.error) {
        resultsDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
        return;
    }
    
    const totalTime = data.time.toFixed(1);
    const totalDistance = data.distance.toFixed(1);
    const avgCongestion = (data.path_details.average_congestion * 100).toFixed(1);
    
    const html = `
        <div class="result-item">
            <h6>Emergency Route</h6>
            <p><strong>Total Distance:</strong> <span class="result-value">${totalDistance} km</span></p>
            <p><strong>Estimated Time:</strong> <span class="result-value">${totalTime} minutes</span></p>
            <p><strong>Average Congestion:</strong> <span class="result-value">${avgCongestion}%</span></p>
        </div>
        
        <div class="mt-3">
            <h6>Route Steps</h6>
            ${data.path_details.steps.map(step => `
                <div class="emergency-step">
                    <strong>${step.from_name}</strong> to <strong>${step.to_name}</strong><br>
                    Distance: ${step.distance} km | Time: ${step.time.toFixed(1)} min<br>
                    Traffic: ${step.traffic}/${step.capacity} (${(step.congestion * 100).toFixed(1)}% congestion)
                </div>
            `).join('')}
        </div>
    `;
    
    resultsDiv.innerHTML = html;
}

function updateEmergencyMap(data) {
    // Clear existing layers except base map
    emergencyMap.eachLayer(layer => {
        if (!layer._url) {  // Keep only tile layers
            emergencyMap.removeLayer(layer);
        }
    });

    // Add hospitals
    facilities.filter(f => f.type.includes('Medical')).forEach(loc => {
        L.circleMarker([loc.y, loc.x], {
            radius: 10,
            fillColor: 'red',
            color: '#000',
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8
        }).bindPopup(`<b>${loc.name}</b><br>Medical Facility`)
        .addTo(emergencyMap);
    });

    // Highlight the emergency path
    if (data.path && data.path.length > 1) {
        const pathCoords = [];
        const validCoords = [];
        
        for (let i = 0; i < data.path.length - 1; i++) {
            const fromId = data.path[i];
            const toId = data.path[i+1];
            
            const fromLoc = findLocation(fromId);
            const toLoc = findLocation(toId);
            
            if (fromLoc && toLoc) {
                const fromCoord = [fromLoc.y, fromLoc.x];
                const toCoord = [toLoc.y, toLoc.x];
                
                pathCoords.push(fromCoord);
                pathCoords.push(toCoord);
                validCoords.push(fromCoord);
                validCoords.push(toCoord);
                
                // Add markers
                if (i === 0) {
                    L.marker(fromCoord, {
                        icon: L.divIcon({
                            className: 'start-marker',
                            html: '🟢',
                            iconSize: [20, 20]
                        })
                    }).bindPopup(`<b>Start:</b> ${fromLoc.name}`)
                    .addTo(emergencyMap);
                }
                
                if (i === data.path.length - 2) {
                    L.marker(toCoord, {
                        icon: L.divIcon({
                            className: 'hospital-marker',
                            html: '🏥',
                            iconSize: [20, 20]
                        })
                    }).bindPopup(`<b>Hospital:</b> ${toLoc.name}`)
                    .addTo(emergencyMap);
                }
            }
        }

        // Draw the path if we have valid coordinates
        if (pathCoords.length > 0) {
            L.polyline(pathCoords, {
                color: 'red',
                weight: 5,
                opacity: 0.7,
                dashArray: '10, 10'
            }).addTo(emergencyMap);

            // Only fit bounds if we have valid coordinates
            if (validCoords.length > 0) {
                try {
                    const bounds = L.latLngBounds(validCoords);
                    emergencyMap.fitBounds(bounds, {padding: [50, 50]});
                } catch (e) {
                    console.error("Bounds error:", e);
                    // Fallback to Cairo center if bounds are invalid
                    emergencyMap.setView([30.04, 31.24], 11);
                }
            }
        }
    } else {
        // Default view if no path
        emergencyMap.setView([30.04, 31.24], 11);
    }
}

function displayTransportResults(data) {
    const resultsDiv = document.getElementById('transport-results');
    resultsDiv.innerHTML = '';
    
    const improvement = (data.estimated_improvement.total * 100).toFixed(1);
    
    const html = `
        <div class="result-item">
            <h6>Public Transport Optimization</h6>
            <p><strong>Estimated Improvement:</strong> <span class="result-value">${improvement}%</span></p>
        </div>
        
        <div class="mt-3">
            <h6>Metro Line Optimizations</h6>
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Line</th>
                        <th>Optimal Frequency</th>
                        <th>Trains Needed</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.metro_schedules.map(line => `
                        <tr>
                            <td>${line.line_name}</td>
                            <td>${line.optimal_frequency.toFixed(2)} trains/hour</td>
                            <td>${line.trains_needed}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
        
        <div class="mt-3">
            <h6>Bus Route Optimizations</h6>
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Route</th>
                        <th>Optimal Buses</th>
                        <th>Current Utilization</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.bus_schedules.map(route => `
                        <tr>
                            <td>${route.route_id}</td>
                            <td>${Math.ceil(route.optimal_buses)}</td>
                            <td>
                                <div class="progress">
                                    <div class="progress-bar" 
                                         style="width: ${Math.min(100, route.utilization * 100)}%">
                                        ${(route.utilization * 100).toFixed(1)}%
                                    </div>
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
        
        <div class="mt-3">
            <h6>Road Maintenance Plan</h6>
            <p><strong>Total Budget:</strong> ${data.maintenance_plan.total_cost} million EGP</p>
            <p><strong>Roads Selected:</strong> ${data.maintenance_plan.selected_roads.length}</p>
            <p><strong>Average Condition Improvement:</strong> 
                ${data.maintenance_plan.average_improvement.toFixed(1)} points
            </p>
            
            <ul class="list-group mt-2">
                ${data.maintenance_plan.selected_roads.map(road => {
                    const fromName = findLocation(road.from)?.name || road.from;
                    const toName = findLocation(road.to)?.name || road.to;
                    return `
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            ${fromName} to ${toName}
                            <span>
                                <span class="badge bg-secondary">Current: ${road.condition}/10</span>
                                <span class="badge bg-success">Improved: 10/10</span>
                                <span class="badge bg-primary">Cost: ${road.cost}M EGP</span>
                            </span>
                        </li>
                    `;
                }).join('')}
            </ul>
        </div>
    `;
    
    resultsDiv.innerHTML = html;
}

function updateTransportMap(data) {
    // Clear existing layers except base map
    transportMap.eachLayer(layer => {
        if (!layer._url) {  // Keep only tile layers
            transportMap.removeLayer(layer);
        }
    });
    
    // Add metro lines
    data.metro_schedules.forEach(line => {
        const stations = line.stations.map(id => findLocation(id)).filter(Boolean);
        const coords = stations.map(s => [s.y, s.x]);
        
        if (coords.length > 1) {
            L.polyline(coords, {
                color: 'red',
                weight: 4,
                opacity: 0.7
            }).bindPopup(`<b>${line.line_name}</b><br>Optimal frequency: ${line.optimal_frequency.toFixed(2)} trains/hour`)
            .addTo(transportMap);
        }
        
        // Add station markers
        stations.forEach(station => {
            L.circleMarker([station.y, station.x], {
                radius: 6,
                fillColor: 'red',
                color: '#000',
                weight: 1,
                opacity: 1,
                fillOpacity: 0.8
            }).bindPopup(`<b>${station.name}</b><br>Metro Station`)
            .addTo(transportMap);
        });
    });
    
    // Add bus routes
    data.bus_schedules.forEach(route => {
        const stops = route.stops.map(id => findLocation(id)).filter(Boolean);
        const coords = stops.map(s => [s.y, s.x]);
        
        if (coords.length > 1) {
            L.polyline(coords, {
                color: 'blue',
                weight: 3,
                opacity: 0.5,
                dashArray: '5, 5'
            }).bindPopup(`<b>Bus Route ${route.route_id}</b><br>Optimal buses: ${Math.ceil(route.optimal_buses)}`)
            .addTo(transportMap);
        }
    });
    
    // Add maintenance roads
    data.maintenance_plan.selected_roads.forEach(road => {
        const fromLoc = findLocation(road.from);
        const toLoc = findLocation(road.to);
        
        if (fromLoc && toLoc) {
            L.polyline(
                [[fromLoc.y, fromLoc.x], [toLoc.y, toLoc.x]],
                {color: 'orange', weight: 4}
            ).bindPopup(
                `<b>Maintenance Priority</b><br>
                From: ${fromLoc.name}<br>
                To: ${toLoc.name}<br>
                Current condition: ${road.condition}/10<br>
                Cost: ${road.cost}M EGP`
            ).addTo(transportMap);
        }
    });
}

function displaySignalResults(data) {
    const resultsDiv = document.getElementById('signal-results');
    resultsDiv.innerHTML = '';
    
    const html = `
        <div class="result-item">
            <h6>Optimized Traffic Signals</h6>
            <p><strong>Intersections Optimized:</strong> ${data.length}</p>
        </div>
        
        ${data.map(signal => `
            <div class="card mt-3">
                <div class="card-header">
                    <h6>${signal.intersection_name}</h6>
                </div>
                <div class="card-body">
                    <p><strong>Approaches:</strong> ${signal.approaches}</p>
                    <p><strong>Cycle Time:</strong> ${signal.cycle_time} seconds</p>
                    
                    <h6 class="mt-3">Signal Phases</h6>
                    ${signal.signal_phases.map(phase => `
                        <div class="signal-phase ${phase.emergency_priority ? 'emergency-priority' : ''}">
                            <strong>${phase.approach_name}</strong><br>
                            Green Time: ${phase.green_time.toFixed(1)} seconds<br>
                            Priority: ${phase.priority.toFixed(1)}
                            ${phase.emergency_priority ? '<br><span class="badge bg-danger">Emergency Priority</span>' : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('')}
    `;
    
    resultsDiv.innerHTML = html;
}

function updateSignalMap(data) {
    // Clear existing layers except base map
    signalMap.eachLayer(layer => {
        if (!layer._url) {  // Keep only tile layers
            signalMap.removeLayer(layer);
        }
    });
    
    // Add all roads (gray background)
    existingRoads.forEach(road => {
        const fromLoc = findLocation(road.from);
        const toLoc = findLocation(road.to);
        
        if (fromLoc && toLoc) {
            L.polyline(
                [[fromLoc.y, fromLoc.x], [toLoc.y, toLoc.x]],
                {color: 'gray', weight: 2, opacity: 0.5}
            ).addTo(signalMap);
        }
    });
    
    // Add optimized intersections
    data.forEach(signal => {
        const intersection = findLocation(signal.intersection);
        if (!intersection) return;
        
        // Create a pie chart for the signal phases
        let startAngle = 0;
        let endAngle = 0;
        
        signal.signal_phases.forEach(phase => {
            endAngle = startAngle + (phase.green_time / signal.cycle_time) * 360;
            
            const options = {
                stroke: false,
                color: phase.emergency_priority ? '#dc3545' : '#28a745',
                fillColor: phase.emergency_priority ? '#dc3545' : '#28a745',
                fillOpacity: 0.7,
                startAngle: startAngle,
                endAngle: endAngle,
                radius: 15
            };
            
            L.semiCircle([intersection.y, intersection.x], options)
                .bindPopup(`
                    <b>${signal.intersection_name}</b><br>
                    <b>${phase.approach_name}</b><br>
                    Green Time: ${phase.green_time.toFixed(1)}s<br>
                    Priority: ${phase.priority.toFixed(1)}
                `)
                .addTo(signalMap);
            
            startAngle = endAngle;
        });
        
        // Add intersection marker
        L.circleMarker([intersection.y, intersection.x], {
            radius: 5,
            fillColor: '#343a40',
            color: '#000',
            weight: 1,
            opacity: 1,
            fillOpacity: 1
        }).bindPopup(`<b>${signal.intersection_name}</b><br>Optimized traffic signals`)
        .addTo(signalMap);
    });
    
    // Fit bounds to show all optimized intersections
    if (data.length > 0) {
        const bounds = L.latLngBounds(
            data.map(signal => {
                const loc = findLocation(signal.intersection);
                return loc ? [loc.y, loc.x] : null;
            }).filter(Boolean)
        );
        signalMap.fitBounds(bounds, {padding: [50, 50]});
    }
}