"""
A* Algorithm for Emergency Routing

This module implements the A* algorithm for finding optimal emergency routes in the transportation network,
taking into account traffic conditions and prioritizing emergency vehicles.
"""

import heapq
import time
import math

def heuristic(G, node, goal):
    """
    Calculate heuristic distance between two nodes using their coordinates.
    
    Parameters:
    -----------
    G : networkx.Graph
        Graph representing the transportation network
    node : str
        Current node ID
    goal : str
        Goal node ID
    
    Returns:
    --------
    float
        Estimated distance in minutes
    """
    if 'pos' in G.nodes[node] and 'pos' in G.nodes[goal]:
        x1, y1 = G.nodes[node]['pos']
        x2, y2 = G.nodes[goal]['pos']
        
        # Calculate Euclidean distance
        lat_factor = 111000 * math.cos(math.radians(30))  # Cairo is around 30°N
        lon_factor = 111000
        dx = (x2 - x1) * lon_factor
        dy = (y2 - y1) * lat_factor
        distance = math.sqrt(dx**2 + dy**2)
        
        # Convert to minutes (assuming 100 km/h speed)
        time_minutes = (distance / 1000) / 100 * 60
        return time_minutes
    return 0

def a_star_emergency_routing(G, traffic_data, start, end, emergency_time_period):
    """
    A* algorithm for finding optimal emergency routes.
    
    Parameters:
    -----------
    G : networkx.Graph
        Graph representing the transportation network
    traffic_data : dict
        Dictionary containing traffic flow data
    start : str
        Starting node ID
    end : str
        Destination node ID
    emergency_time_period : str
        Time period (morning, afternoon, evening, night)
    
    Returns:
    --------
    list
        Path from start to end
    float
        Total path distance in meters
    float
        Total travel time in minutes
    dict
        Edge keys used in the path
    float
        Execution time in seconds
    """
    start_time = time.time()  # Start measuring execution time
    queue = []
    heapq.heappush(queue, (0, 0, start))
    g_scores = {node: float('inf') for node in G.nodes}
    f_scores = {node: float('inf') for node in G.nodes}
    previous = {node: None for node in G.nodes}
    edge_keys = {node: {} for node in G.nodes}
    g_scores[start] = 0
    f_scores[start] = heuristic(G, start, end)

    while queue:
        _, current_g, current_node = heapq.heappop(queue)
        if current_node == end:
            break
        for neighbor, edges in G[current_node].items():
            for key, data in edges.items():
                base_distance = data.get('distance', 1000)
                weight = get_edge_weight(G, traffic_data, current_node, neighbor, key, None, emergency_time_period, base_distance, 'emergency')
                if weight == float('inf'):
                    continue
                tentative_g_score = g_scores[current_node] + weight
                if tentative_g_score < g_scores[neighbor]:
                    g_scores[neighbor] = tentative_g_score
                    f_scores[neighbor] = tentative_g_score + heuristic(G, neighbor, end)
                    previous[neighbor] = current_node
                    edge_keys[neighbor][current_node] = key
                    heapq.heappush(queue, (f_scores[neighbor], tentative_g_score, neighbor))

    path = []
    total_travel_time = 0
    total_distance = 0
    current = end
    if previous[current] or current == start:
        while current:
            path.append(current)
            next_node = previous[current]
            if next_node:
                key = edge_keys[current][next_node]
                base_distance = G[current][next_node][key].get('distance', 1000)
                weight = get_edge_weight(G, traffic_data, current, next_node, key, None, emergency_time_period, base_distance, 'emergency')
                total_travel_time += weight
                total_distance += base_distance
            current = next_node
        path.reverse()

    end_time = time.time()
    execution_time = end_time - start_time
    
    return path, total_distance, total_travel_time, edge_keys, execution_time

def get_edge_weight(G, traffic_data, u, v, key, time_period, emergency_time_period, base_distance, transport_mode, emergency_path=None, emergency_active=False):
    """
    Calculate edge weight based on traffic conditions and transport mode.
    
    Parameters:
    -----------
    G : networkx.Graph
        Graph representing the transportation network
    traffic_data : dict
        Dictionary containing traffic flow data
    u, v : str
        Edge endpoints
    key : int
        Edge key in multigraph
    time_period : str
        Time period for regular traffic
    emergency_time_period : str
        Time period for emergency traffic
    base_distance : float
        Base distance of the edge in meters
    transport_mode : str
        Transport mode (car, bus, metro, emergency)
    emergency_path : list, optional
        Path of emergency vehicle
    emergency_active : bool, optional
        Whether emergency vehicle is active
    
    Returns:
    --------
    float
        Edge weight (travel time in minutes)
    """
    road_id_1 = f"{u}-{v}"
    road_id_2 = f"{v}-{u}"
    road_type = G[u][v][key].get('road_type')

    # Define allowed road types for each transport mode
    allowed_road_types = {
        'car': ['existing', 'potential', 'bus', 'virtual_connection', 'virtual_link'],
        'bus': ['bus'],
        'metro': ['metro'],
        'emergency': ['existing', 'potential', 'virtual_connection', 'virtual_link']
    }

    # If the road type is not allowed for this transport mode, return infinite weight
    if road_type not in allowed_road_types[transport_mode]:
        return float('inf')

    # Base speeds (km/h)
    base_speeds = {
        'car': 120,
        'bus': 100,
        'metro': 90,
        'emergency': 100
    }
    
    capacity = G[u][v][key].get('capacity', 2000)  # Default capacity if not specified
    traffic_flow = None
    if time_period:
        traffic_flow = traffic_data.get(time_period.lower(), {}).get((str(u), str(v)), capacity)
    elif emergency_time_period:
        traffic_flow = traffic_data.get(emergency_time_period.lower(), {}).get((str(u), str(v)), capacity)

    # Calculate speed based on traffic
    base_speed = base_speeds[transport_mode]
    if transport_mode in ['car', 'bus', 'emergency'] and traffic_flow is not None:
        traffic_factor = traffic_flow / capacity if capacity > 0 else 1.0
        traffic_factor = max(0.5, min(traffic_factor, 1.5))  # Cap between 0.5 and 1.5
        speed = base_speed / traffic_factor
    else:
        speed = base_speed  # Metro speed is constant

    # Convert distance to time (in minutes)
    distance_km = base_distance / 1000
    time_minutes = (distance_km / speed) * 60
    return time_minutes
