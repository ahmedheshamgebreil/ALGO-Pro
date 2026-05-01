"""
Transit Integration Algorithms

This module implements algorithms for integrating different transportation modes
and optimizing transit networks.
"""

import networkx as nx
import pandas as pd
import numpy as np
import time
import heapq

def optimize_transit_connections(G, bus_stops, metro_stations, neighborhoods_df, public_demand_df):
    """
    Optimize connections between different transit modes (bus and metro) to improve
    overall transportation network efficiency.
    
    Parameters:
    -----------
    G : networkx.Graph
        Graph representing the transportation network
    bus_stops : set
        Set of bus stop nodes
    metro_stations : set
        Set of metro station nodes
    neighborhoods_df : pandas DataFrame
        DataFrame containing information about neighborhoods
    public_demand_df : pandas DataFrame
        DataFrame containing public transportation demand information
    
    Returns:
    --------
    list
        List of recommended new connections
    float
        Execution time in seconds
    """
    start_time = time.time()
    
    # Extract demand data
    demand_matrix = {}
    for _, row in public_demand_df.iterrows():
        from_id = str(row["FromID"]).strip()
        to_id = str(row["ToID"]).strip()
        daily_passengers = row["Daily Passengers"]
        demand_matrix[(from_id, to_id)] = daily_passengers
    
    # Extract population data
    population_by_id = {}
    for _, row in neighborhoods_df.iterrows():
        node_id = str(row["ID"]).strip()
        population = float(row["Population"])
        population_by_id[node_id] = population
    
    # Find potential connections between bus stops and metro stations
    potential_connections = []
    
    for bus_stop in bus_stops:
        if bus_stop not in G.nodes:
            continue
            
        bus_pos = G.nodes[bus_stop].get('pos')
        if not bus_pos:
            continue
            
        for metro_station in metro_stations:
            if metro_station not in G.nodes or bus_stop == metro_station:
                continue
                
            metro_pos = G.nodes[metro_station].get('pos')
            if not metro_pos:
                continue
                
            # Check if there's already a direct connection
            if G.has_edge(bus_stop, metro_station):
                continue
                
            # Calculate distance between bus stop and metro station
            from src.utils.graph_utils import distance_calc
            distance = distance_calc(bus_pos[0], bus_pos[1], metro_pos[0], metro_pos[1])
            
            # Only consider connections within 1 km
            if distance > 1000:
                continue
                
            # Calculate potential demand for this connection
            demand = 0
            for (from_id, to_id), passengers in demand_matrix.items():
                # If either endpoint is the bus stop or metro station, add to demand
                if from_id == bus_stop or from_id == metro_station or to_id == bus_stop or to_id == metro_station:
                    demand += passengers * 0.1  # Assume 10% of passengers would use this connection
            
            # Calculate score based on distance and demand
            # Higher demand and shorter distance = better score
            score = demand / (distance + 100)  # Add 100 to avoid division by very small numbers
            
            potential_connections.append({
                'bus_stop': bus_stop,
                'metro_station': metro_station,
                'distance': distance,
                'demand': demand,
                'score': score
            })
    
    # Sort connections by score (descending)
    potential_connections.sort(key=lambda x: x['score'], reverse=True)
    
    # Select top connections (limit to 10)
    recommended_connections = potential_connections[:10]
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return recommended_connections, execution_time

def multi_modal_path_planning(G, traffic_data, start, end, time_period):
    """
    Find optimal paths using multiple transportation modes.
    
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
    
    Returns:
    --------
    dict
        Dictionary containing paths for different transportation modes
    float
        Execution time in seconds
    """
    start_time = time.time()
    
    # Define transportation modes
    modes = ['car', 'bus', 'metro', 'mixed']
    
    # Initialize results
    results = {}
    
    # Find path for each mode
    for mode in modes:
        if mode != 'mixed':
            # Use Dijkstra's algorithm for single-mode paths
            from algorithms.greedy.dijkstra import dijkstra_with_traffic
            path, total_weight, _, _ = dijkstra_with_traffic(G, traffic_data, start, end, time_period, transport_mode=mode)
            
            results[mode] = {
                'path': path,
                'total_weight': total_weight
            }
        else:
            # For mixed mode, we need to consider transfers between modes
            # This is a more complex algorithm that finds optimal combinations of modes
            mixed_path, mixed_weight = find_mixed_mode_path(G, traffic_data, start, end, time_period)
            
            results[mode] = {
                'path': mixed_path,
                'total_weight': mixed_weight
            }
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return results, execution_time

def find_mixed_mode_path(G, traffic_data, start, end, time_period):
    """
    Find optimal path using a combination of transportation modes.
    
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
    
    Returns:
    --------
    list
        Path from start to end
    float
        Total path weight
    """
    # Initialize data structures
    distances = {node: float('inf') for node in G.nodes}
    distances[start] = 0
    previous = {node: None for node in G.nodes}
    edge_keys = {node: {} for node in G.nodes}
    modes = {node: None for node in G.nodes}  # Track mode used to reach each node
    pq = [(0, start)]
    
    # Dijkstra's algorithm with mode switching
    while pq:
        current_distance, current_node = heapq.heappop(pq)
        
        if current_node == end:
            break
            
        if current_distance > distances[current_node]:
            continue
            
        # Get current mode
        current_mode = modes[current_node]
        
        for neighbor, edges in G[current_node].items():
            for key, data in edges.items():
                road_type = data.get('road_type')
                
                # Determine possible modes for this edge
                possible_modes = []
                if road_type in ['existing', 'potential', 'virtual_connection', 'virtual_link']:
                    possible_modes.append('car')
                if road_type == 'bus':
                    possible_modes.append('bus')
                if road_type == 'metro':
                    possible_modes.append('metro')
                
                for mode in possible_modes:
                    # Calculate edge weight based on mode
                    base_distance = data.get('distance', 1000)
                    from algorithms.greedy.dijkstra import get_edge_weight
                    weight = get_edge_weight(G, traffic_data, current_node, neighbor, key, time_period, None, base_distance, mode)
                    
                    if weight == float('inf'):
                        continue
                    
                    # Add mode switching penalty (5 minutes)
                    if current_mode is not None and current_mode != mode:
                        weight += 5
                    
                    distance = distances[current_node] + weight
                    
                    if distance < distances[neighbor]:
                        distances[neighbor] = distance
                        previous[neighbor] = current_node
                        edge_keys[neighbor][current_node] = key
                        modes[neighbor] = mode
                        heapq.heappush(pq, (distance, neighbor))
    
    # Reconstruct path
    path = []
    total_weight = 0
    current = end
    
    if previous[current] or current == start:
        while current:
            path.append(current)
            next_node = previous[current]
            if next_node:
                key = edge_keys[current][next_node]
                mode = modes[current]
                base_distance = G[current][next_node][key].get('distance', 1000)
                from algorithms.greedy.dijkstra import get_edge_weight
                weight = get_edge_weight(G, traffic_data, current, next_node, key, time_period, None, base_distance, mode)
                total_weight += weight
            current = next_node
        path.reverse()
    
    return path, total_weight

def optimize_bus_routes(G, bus_routes_df, neighborhoods_df, public_demand_df):
    """
    Optimize bus routes based on demand and population distribution.
    
    Parameters:
    -----------
    G : networkx.Graph
        Graph representing the transportation network
    bus_routes_df : pandas DataFrame
        DataFrame containing bus route information
    neighborhoods_df : pandas DataFrame
        DataFrame containing information about neighborhoods
    public_demand_df : pandas DataFrame
        DataFrame containing public transportation demand information
    
    Returns:
    --------
    dict
        Dictionary containing optimized bus routes
    float
        Execution time in seconds
    """
    start_time = time.time()
    
    # Extract demand data
    demand_matrix = {}
    for _, row in public_demand_df.iterrows():
        from_id = str(row["FromID"]).strip()
        to_id = str(row["ToID"]).strip()
        daily_passengers = row["Daily Passengers"]
        demand_matrix[(from_id, to_id)] = daily_passengers
    
    # Extract population data
    population_by_id = {}
    for _, row in neighborhoods_df.iterrows():
        node_id = str(row["ID"]).strip()
        population = float(row["Population"])
        population_by_id[node_id] = population
    
    # Extract existing bus routes
    existing_routes = {}
    for _, row in bus_routes_df.iterrows():
        route_id = row["RouteID"]
        stops = [stop.strip().strip('"') for stop in row["Stops(comma-separated IDs)"].split(",")]
        buses_assigned = row["Buses Assigned"]
        daily_passengers = row["Daily Passengers"]
        
        existing_routes[route_id] = {
            "stops": stops,
            "buses_assigned": buses_assigned,
            "daily_passengers": daily_passengers
        }
    
    # Analyze each route for potential improvements
    optimized_routes = {}
    
    for route_id, route_info in existing_routes.items():
        stops = route_info["stops"]
        buses_assigned = route_info["buses_assigned"]
        daily_passengers = route_info["daily_passengers"]
        
        # Calculate current route metrics
        current_length = 0
        current_demand_coverage = 0
        
        for i in range(len(stops) - 1):
            from_stop = stops[i]
            to_stop = stops[i + 1]
            
            # Calculate distance between stops
            if from_stop in G.nodes and to_stop in G.nodes:
                if G.has_edge(from_stop, to_stop):
                    # Find minimum distance edge
                    min_distance = float('inf')
                    for key, data in G[from_stop][to_stop].items():
                        if data.get('distance', float('inf')) < min_distance:
                            min_distance = data.get('distance')
                    
                    current_length += min_distance
                else:
                    # If no direct edge, use shortest path
                    try:
                        path = nx.shortest_path(G, from_stop, to_stop, weight='distance')
                        path_length = 0
                        for j in range(len(path) - 1):
                            u, v = path[j], path[j + 1]
                            min_distance = float('inf')
                            for key, data in G[u][v].items():
                                if data.get('distance', float('inf')) < min_distance:
                                    min_distance = data.get('distance')
                            path_length += min_distance
                        current_length += path_length
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        # If no path exists, use a default distance
                        current_length += 1000
            
            # Calculate demand coverage
            demand_key = (from_stop, to_stop)
            reverse_key = (to_stop, from_stop)
            current_demand_coverage += demand_matrix.get(demand_key, 0) + demand_matrix.get(reverse_key, 0)
        
        # Try to optimize the route
        # 1. Check if any high-demand areas are not covered
        # 2. Check if any low-demand stops can be removed
        # 3. Check if route order can be optimized
        
        # For simplicity, we'll just suggest adding high-demand areas
        high_demand_pairs = []
        for (from_id, to_id), passengers in demand_matrix.items():
            if passengers > 1000 and from_id not in stops and to_id not in stops:
                # Check if either endpoint is close to the route
                for stop in stops:
                    if stop in G.nodes and from_id in G.nodes:
                        try:
                            path = nx.shortest_path(G, stop, from_id, weight='distance')
                            if len(path) <= 3:  # Within 2 hops
                                high_demand_pairs.append((from_id, to_id, passengers))
                                break
                        except (nx.NetworkXNoPath, nx.NodeNotFound):
                            pass
                    
                    if stop in G.nodes and to_id in G.nodes:
                        try:
                            path = nx.shortest_path(G, stop, to_id, weight='distance')
                            if len(path) <= 3:  # Within 2 hops
                                high_demand_pairs.append((from_id, to_id, passengers))
                                break
                        except (nx.NetworkXNoPath, nx.NodeNotFound):
                            pass
        
        # Sort by demand
        high_demand_pairs.sort(key=lambda x: x[2], reverse=True)
        
        # Suggest adding top 3 high-demand areas
        suggested_additions = high_demand_pairs[:3]
        
        optimized_routes[route_id] = {
            "original_stops": stops,
            "original_buses": buses_assigned,
            "original_passengers": daily_passengers,
            "current_length_meters": current_length,
            "current_demand_coverage": current_demand_coverage,
            "suggested_additions": suggested_additions
        }
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return optimized_routes, execution_time
