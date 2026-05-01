"""
Dijkstra's Algorithm with Traffic Considerations

This module implements Dijkstra's algorithm for finding shortest paths in the transportation network,
taking into account traffic conditions at different times of day.
"""

import heapq
import time

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

def dijkstra_with_traffic(G, traffic_data, start, end, time_period, emergency_time_period=None, transport_mode='car', emergency_path=None, emergency_active=False):
    """
    Dijkstra's algorithm for finding shortest paths, taking into account traffic conditions.
    
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
    time_period : str
        Time period (morning, afternoon, evening, night)
    emergency_time_period : str, optional
        Time period for emergency traffic
    transport_mode : str, optional
        Transport mode (car, bus, metro, emergency)
    emergency_path : list, optional
        Path of emergency vehicle
    emergency_active : bool, optional
        Whether emergency vehicle is active
    
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
    
    # Initialize data structures
    distances = {node: float('inf') for node in G.nodes}
    distances[start] = 0
    previous = {node: None for node in G.nodes}
    edge_keys = {node: {} for node in G.nodes}
    pq = [(0, start)]
    
    # Dijkstra's algorithm
    while pq:
        current_distance, current_node = heapq.heappop(pq)
        
        if current_node == end:
            break
            
        if current_distance > distances[current_node]:
            continue
            
        for neighbor, edges in G[current_node].items():
            for key, data in edges.items():
                # Calculate edge weight based on traffic
                base_distance = data.get('distance', 1000)
                weight = get_edge_weight(G, traffic_data, current_node, neighbor, key, time_period, emergency_time_period, base_distance, transport_mode, emergency_path, emergency_active)
                
                if weight == float('inf'):
                    continue
                    
                distance = distances[current_node] + weight
                
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current_node
                    edge_keys[neighbor][current_node] = key
                    heapq.heappush(pq, (distance, neighbor))
    
    # Reconstruct path
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
                weight = get_edge_weight(G, traffic_data, current, next_node, key, time_period, emergency_time_period, base_distance, transport_mode, emergency_path, emergency_active)
                total_travel_time += weight
                total_distance += base_distance
            current = next_node
        path.reverse()
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return path, total_distance, total_travel_time, edge_keys, execution_time

def get_time_complexity(algorithm_name):
    """
    Get the theoretical time complexity of an algorithm.
    
    Parameters:
    -----------
    algorithm_name : str
        Name of the algorithm
    
    Returns:
    --------
    str
        Time complexity in Big O notation
    """
    complexities = {
        "dijkstra_with_traffic": "O((E + V) log V) where E is the number of edges and V is the number of vertices",
        "a_star_emergency_routing": "O((E + V) log V) where E is the number of edges and V is the number of vertices",
        "memoized_path_planning": "O((E + V) log V) for first computation, O(1) for cached paths"
    }
    
    return complexities.get(algorithm_name, "Unknown")

def simulate_emergency_delay(G, traffic_data, car_path, emergency_path, car_time_period, emergency_time_period):
    """
    Simulate the delay caused by an emergency vehicle on a car's path.
    
    Parameters:
    -----------
    G : networkx.Graph
        Graph representing the transportation network
    traffic_data : dict
        Dictionary containing traffic flow data
    car_path : list
        Path of the car
    emergency_path : list
        Path of the emergency vehicle
    car_time_period : str
        Time period for car traffic
    emergency_time_period : str
        Time period for emergency traffic
    
    Returns:
    --------
    list
        Updated car path
    float
        Delay in meters
    """
    # Find common edges between car path and emergency path
    common_edges = []
    for i in range(len(car_path) - 1):
        car_edge = (car_path[i], car_path[i+1])
        for j in range(len(emergency_path) - 1):
            emergency_edge = (emergency_path[j], emergency_path[j+1])
            if car_edge == emergency_edge or car_edge == (emergency_edge[1], emergency_edge[0]):
                common_edges.append(car_edge)
                break
    
    # Calculate delay based on common edges
    delay = 0
    for u, v in common_edges:
        # Find edge data
        edge_data = None
        for key, data in G[u][v].items():
            if data.get('road_type') in ['existing', 'potential', 'virtual_connection', 'virtual_link']:
                edge_data = data
                break
        
        if edge_data:
            base_distance = edge_data.get('distance', 1000)
            # Add 20% delay for each common edge
            delay += base_distance * 0.2
    
    # إضافة تأخير افتراضي إذا لم يكن هناك حواف مشتركة
    if delay == 0:
        # حساب إجمالي مسافة مسار العربية
        total_car_distance = 0
        for i in range(len(car_path) - 1):
            u, v = car_path[i], car_path[i+1]
            for key, data in G[u][v].items():
                if 'distance' in data:
                    total_car_distance += data['distance']
                    break
        
        # إضافة تأخير بنسبة 3% من إجمالي المسافة
        delay = total_car_distance * 0.03
    
    # Return original path and calculated delay
    return car_path, delay
