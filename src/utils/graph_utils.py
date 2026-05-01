"""
Graph Creation Utility for Smart City Transportation Project

This module provides functions for creating and manipulating the transportation network graph.
"""

import networkx as nx
import math
import pandas as pd

def create_graph(data):
    """
    Create a transportation network graph from the loaded data.
    
    Parameters:
    -----------
    data : dict
        Dictionary containing loaded data
    
    Returns:
    --------
    networkx.Graph
        Graph representing the transportation network
    set
        Set of bus stop nodes
    set
        Set of metro station nodes
    dict
        Dictionary containing traffic data
    """
    G = nx.MultiGraph()
    bus_stops = set()
    metro_stations = set()
    
    # Add nodes from neighborhoods
    for _, row in data["neighborhoods"].iterrows():
        node_id = str(row["ID"]).strip().strip('"')
        G.add_node(node_id,
                   name=str(row["Name"]).strip(),
                   population=float(row["Population"]),
                   type=str(row["Type"]).strip().lower(),
                   pos=(float(row["X-coordinate"]), float(row["Y-coordinate"])))
    
    # Add nodes from facilities
    for _, row in data["facilities"].iterrows():
        node_id = str(row["ID"]).strip().strip('"')
        x = row["X-coordinate"]
        y = row["Y-coordinate"]
        node_type = str(row["Type"]).strip().lower()
        if pd.notnull(x) and pd.notnull(y):
            G.add_node(node_id,
                       name=str(row["Name"]).strip(),
                       type=node_type,
                       pos=(float(x), float(y)))
        else:
            G.add_node(node_id,
                       name=str(row["Name"]).strip(),
                       type=node_type)
    
    # Add edges from existing roads
    for _, row in data["existing_roads"].iterrows():
        from_id = str(row["FromID"]).strip().strip('"')
        to_id = str(row["ToID"]).strip().strip('"')
        distance_m = float(row["Distance(km)"]) * 1000  # Convert to meters
        if distance_m > 100000:  # Flag unrealistic distances (>100 km)
            print(f"Warning: Unrealistic distance between {from_id} and {to_id}: {distance_m/1000} km")
            continue
        G.add_edge(from_id, to_id,
                   distance=distance_m,
                   capacity=float(row["Current Capacity(vehicles/hour)"]),
                   condition=float(row["Condition(1-10)"]),
                   road_type="existing",
                   cost=0.0)
    
    # Add edges from bus routes
    bus_edges = {}
    for _, row in data["bus_routes"].iterrows():
        stops = [stop.strip().strip('"') for stop in row["Stops(comma-separated IDs)"].split(",")]
        route_id = row["RouteID"]
        buses_assigned = row["Buses Assigned"]
        daily_passengers = row["Daily Passengers"]
        for i in range(len(stops) - 1):
            from_stop = stops[i]
            to_stop = stops[i + 1]
            if from_stop not in G.nodes:
                G.add_node(from_stop, name=from_stop, type="bus_stop")
            if to_stop not in G.nodes:
                G.add_node(to_stop, name=to_stop, type="bus_stop")
            bus_stops.add(from_stop)
            bus_stops.add(to_stop)
            # Find distance from existing roads
            distance = None
            for _, road_row in data["existing_roads"].iterrows():
                if (str(road_row["FromID"]).strip().strip('"') == from_stop and 
                    str(road_row["ToID"]).strip().strip('"') == to_stop) or \
                   (str(road_row["FromID"]).strip().strip('"') == to_stop and 
                    str(road_row["ToID"]).strip().strip('"') == from_stop):
                    distance = float(road_row["Distance(km)"]) * 1000
                    break
            if distance is None:
                distance = data["existing_roads"]["Distance(km)"].mean() * 1000 if not data["existing_roads"].empty else 1500
            edge_data = {
                'distance': distance,
                'capacity': daily_passengers / 24,
                'condition': 7.0,
                'road_type': "bus",
                'cost': 0.0,
                'route_id': route_id,
                'buses_assigned': buses_assigned
            }
            edge_key = G.add_edge(from_stop, to_stop, **edge_data)
            edge_pair = tuple(sorted([from_stop, to_stop]))
            if edge_pair not in bus_edges:
                bus_edges[edge_pair] = []
            bus_edges[edge_pair].append((edge_key, edge_data))
    
    # Add edges from metro lines
    metro_edges = {}
    for _, row in data["metro_lines"].iterrows():
        stations = [station.strip().strip('"') for station in row["Stations(comma-separated IDs)"].split(",")]
        line_id = row["LineID"]
        daily_passengers = row["Daily Passengers"]
        for i in range(len(stations) - 1):
            from_station = stations[i]
            to_station = stations[i + 1]
            if from_station not in G.nodes:
                G.add_node(from_station, name=from_station, type="metro_station")
            if to_station not in G.nodes:
                G.add_node(to_station, name=to_station, type="metro_station")
            metro_stations.add(from_station)
            metro_stations.add(to_station)
            # Find distance from existing roads
            distance = None
            for _, road_row in data["existing_roads"].iterrows():
                if (str(road_row["FromID"]).strip().strip('"') == from_station and 
                    str(road_row["ToID"]).strip().strip('"') == to_station) or \
                   (str(road_row["FromID"]).strip().strip('"') == to_station and 
                    str(road_row["ToID"]).strip().strip('"') == from_station):
                    distance = float(road_row["Distance(km)"]) * 1000
                    break
            if distance is None:
                distance = data["existing_roads"]["Distance(km)"].mean() * 1000 if not data["existing_roads"].empty else 2000
            edge_data = {
                'distance': distance,
                'capacity': daily_passengers / 24,
                'condition': 8.0,
                'road_type': "metro",
                'cost': 0.0,
                'line_id': line_id
            }
            edge_key = G.add_edge(from_station, to_station, **edge_data)
            edge_pair = tuple(sorted([from_station, to_station]))
            if edge_pair not in metro_edges:
                metro_edges[edge_pair] = []
            metro_edges[edge_pair].append((edge_key, edge_data))
    
    # Add edges from potential roads
    for _, row in data["potential_roads"].iterrows():
        from_id = str(row["FromID"]).strip().strip('"')
        to_id = str(row["ToID"]).strip().strip('"')
        distance_m = float(row["Distance(km)"]) * 1000
        if distance_m > 100000:  # Flag unrealistic distances
            print(f"Warning: Unrealistic distance between {from_id} and {to_id}: {distance_m/1000} km")
            continue
        G.add_edge(from_id, to_id,
                   distance=distance_m,
                   capacity=float(row["Estimated Capacity(vehicles/hour)"]),
                   cost=float(row["Construction Cost(Million EGP)"]),
                   road_type="potential",
                   condition=10.0)
    
    # Handle nodes without pos
    all_coords = {}
    for _, row in data["neighborhoods"].iterrows():
        node_id = str(row["ID"]).strip().strip('"')
        all_coords[node_id] = (row["X-coordinate"], row["Y-coordinate"])
    for _, row in data["facilities"].iterrows():
        node_id = str(row["ID"]).strip().strip('"')
        x = row["X-coordinate"]
        y = row["Y-coordinate"]
        if pd.notnull(x) and pd.notnull(y):
            all_coords[node_id] = (x, y)
    
    positions = nx.get_node_attributes(G, 'pos')
    for node in G.nodes:
        if node not in positions:
            if node in all_coords:
                G.nodes[node]["pos"] = all_coords[node]
            else:
                # Find nearest node with coordinates
                min_dist = float("inf")
                nearest = None
                for other_node, pos in all_coords.items():
                    if other_node != node:
                        d = distance_calc(pos[0], pos[1], pos[0], pos[1])
                        if d < min_dist:
                            min_dist = d
                            nearest = other_node
                if nearest:
                    x, y = all_coords[nearest]
                    G.nodes[node]["pos"] = (x + 0.01, y + 0.01)
                    # Use shortest path distance instead of Euclidean
                    try:
                        path = nx.shortest_path(G, node, nearest, weight="distance")
                        calculated_distance = nx.path_weight(G, path, "distance")
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        calculated_distance = 1000  # Fallback distance
                    G.add_edge(node, nearest,
                               distance=calculated_distance,
                               road_type="virtual_link",
                               condition=10.0,
                               cost=0.0)
                else:
                    G.nodes[node]["pos"] = (0, 0)
    
    # Connect isolated nodes
    isolated_nodes = list(nx.isolates(G))
    for node in isolated_nodes:
        min_dist = float("inf")
        nearest_node = None
        x1, y1 = G.nodes[node]["pos"]
        for other_node, pos in all_coords.items():
            if other_node != node:
                x2, y2 = pos
                d = distance_calc(x1, y1, x2, y2)
                if d < min_dist:
                    min_dist = d
                    nearest_node = other_node
        if nearest_node:
            try:
                path = nx.shortest_path(G, node, nearest_node, weight="distance")
                calculated_distance = nx.path_weight(G, path, "distance")
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                calculated_distance = min_dist
            G.add_edge(node, nearest_node,
                       distance=calculated_distance,
                       road_type="virtual_connection",
                       condition=8.0,
                       cost=0.0)
    
    return G, bus_stops, metro_stations, data["traffic_data"]

def distance_calc(x1, y1, x2, y2):
    """
    Calculate approximate distance in meters between two points.
    
    Parameters:
    -----------
    x1, y1 : float
        Coordinates of first point
    x2, y2 : float
        Coordinates of second point
    
    Returns:
    --------
    float
        Distance in meters
    """
    # Approximate distance in meters (1 degree ≈ 111 km at equator, adjusted for Cairo's latitude)
    lat_factor = 111000 * math.cos(math.radians(30))  # Cairo is around 30°N
    lon_factor = 111000
    dx = (x2 - x1) * lon_factor
    dy = (y2 - y1) * lat_factor
    return math.sqrt(dx**2 + dy**2)

def get_available_places(G, bus_stops, metro_stations, transport_mode):
    """
    Get available places for a specific transport mode.
    
    Parameters:
    -----------
    G : networkx.Graph
        Graph representing the transportation network
    bus_stops : set
        Set of bus stop nodes
    metro_stations : set
        Set of metro station nodes
    transport_mode : str
        Transport mode (car, bus, metro, emergency)
    
    Returns:
    --------
    dict
        Dictionary mapping node IDs to place names
    """
    available_places = {}
    
    if transport_mode == 'car' or transport_mode == 'emergency':
        # All nodes are available for cars and emergency vehicles
        for node in G.nodes:
            if 'name' in G.nodes[node]:
                available_places[node] = G.nodes[node]['name']
    elif transport_mode == 'bus':
        # Only bus stops are available for buses
        for node in bus_stops:
            if node in G.nodes and 'name' in G.nodes[node]:
                available_places[node] = G.nodes[node]['name']
    elif transport_mode == 'metro':
        # Only metro stations are available for metro
        for node in metro_stations:
            if node in G.nodes and 'name' in G.nodes[node]:
                available_places[node] = G.nodes[node]['name']
    
    return available_places
