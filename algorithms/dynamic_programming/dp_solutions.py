"""
Dynamic Programming Solutions for Transportation Network Optimization

This module implements dynamic programming solutions for:
1. Optimal scheduling of public transportation vehicles
2. Resource allocation for road maintenance
3. Memoization techniques for route planning algorithms
"""

import pandas as pd
import numpy as np
import time
from collections import defaultdict
import heapq

def optimize_public_transport_schedule(metro_lines_df, bus_routes_df, public_demand_df):
    """
    Implements a dynamic programming solution for optimal scheduling of public transportation
    vehicles across metro and bus lines to maximize passenger service while minimizing resources.
    
    Parameters:
    -----------
    metro_lines_df : pandas DataFrame
        DataFrame containing metro line information
    bus_routes_df : pandas DataFrame
        DataFrame containing bus route information
    public_demand_df : pandas DataFrame
        DataFrame containing public transportation demand information
    
    Returns:
    --------
    dict
        Optimized schedule with vehicle allocations and frequencies
    float
        Execution time in seconds
    """
    start_time = time.time()
    
    # Extract relevant data
    metro_lines = {}
    for _, row in metro_lines_df.iterrows():
        line_id = row["LineID"]
        daily_passengers = row["Daily Passengers"]
        stations = [station.strip().strip('"') for station in row["Stations(comma-separated IDs)"].split(",")]
        metro_lines[line_id] = {
            "daily_passengers": daily_passengers,
            "stations": stations,
            "num_stations": len(stations)
        }
    
    bus_routes = {}
    for _, row in bus_routes_df.iterrows():
        route_id = row["RouteID"]
        daily_passengers = row["Daily Passengers"]
        buses_assigned = row["Buses Assigned"]
        stops = [stop.strip().strip('"') for stop in row["Stops(comma-separated IDs)"].split(",")]
        bus_routes[route_id] = {
            "daily_passengers": daily_passengers,
            "buses_assigned": buses_assigned,
            "stops": stops,
            "num_stops": len(stops)
        }
    
    # Create demand matrix from public demand data
    demand_matrix = {}
    for _, row in public_demand_df.iterrows():
        from_id = str(row["FromID"]).strip()
        to_id = str(row["ToID"]).strip()
        daily_passengers = row["Daily Passengers"]
        demand_matrix[(from_id, to_id)] = daily_passengers
    
    # Define time periods and their weights
    time_periods = ["morning", "afternoon", "evening", "night"]
    time_weights = {"morning": 0.35, "afternoon": 0.25, "evening": 0.30, "night": 0.10}
    
    # Dynamic Programming for Metro Scheduling
    # We'll optimize the number of trains per hour for each line in each time period
    metro_schedule = {}
    for line_id, line_info in metro_lines.items():
        metro_schedule[line_id] = {}
        daily_passengers = line_info["daily_passengers"]
        num_stations = line_info["num_stations"]
        
        # Base capacity: assume each train can carry 1000 passengers
        base_capacity = 1000
        
        # Calculate optimal trains per hour for each time period
        for period in time_periods:
            period_demand = daily_passengers * time_weights[period]
            
            # Dynamic programming to find optimal number of trains
            # State: number of trains
            # Value: service quality (passengers served / waiting time)
            max_trains = 20  # Maximum trains per hour
            dp = [0] * (max_trains + 1)
            
            for trains in range(1, max_trains + 1):
                # Calculate service quality
                capacity = trains * base_capacity
                waiting_time = 60 / trains  # minutes between trains
                
                if capacity >= period_demand:
                    service_quality = period_demand / waiting_time
                else:
                    # Penalty for insufficient capacity
                    service_quality = capacity / waiting_time - (period_demand - capacity) * 0.5
                
                dp[trains] = service_quality
            
            # Find optimal number of trains
            optimal_trains = max(range(1, max_trains + 1), key=lambda t: dp[t])
            
            metro_schedule[line_id][period] = {
                "trains_per_hour": optimal_trains,
                "headway_minutes": 60 / optimal_trains,
                "capacity": optimal_trains * base_capacity,
                "expected_demand": period_demand
            }
    
    # Dynamic Programming for Bus Scheduling
    bus_schedule = {}
    for route_id, route_info in bus_routes.items():
        bus_schedule[route_id] = {}
        daily_passengers = route_info["daily_passengers"]
        current_buses = route_info["buses_assigned"]
        num_stops = route_info["num_stops"]
        
        # Base capacity: assume each bus can carry 80 passengers
        base_capacity = 80
        
        # Calculate optimal buses per hour for each time period
        for period in time_periods:
            period_demand = daily_passengers * time_weights[period]
            
            # Dynamic programming to find optimal number of buses
            # State: number of buses
            # Value: service quality (passengers served / waiting time)
            max_buses = 30  # Maximum buses per hour
            dp = [0] * (max_buses + 1)
            
            for buses in range(1, max_buses + 1):
                # Calculate service quality
                capacity = buses * base_capacity
                waiting_time = 60 / buses  # minutes between buses
                
                if capacity >= period_demand:
                    service_quality = period_demand / waiting_time
                else:
                    # Penalty for insufficient capacity
                    service_quality = capacity / waiting_time - (period_demand - capacity) * 0.5
                
                # Add cost factor
                cost_factor = buses / current_buses if buses > current_buses else 1.0
                service_quality = service_quality / cost_factor
                
                dp[buses] = service_quality
            
            # Find optimal number of buses
            optimal_buses = max(range(1, max_buses + 1), key=lambda b: dp[b])
            
            bus_schedule[route_id][period] = {
                "buses_per_hour": optimal_buses,
                "headway_minutes": 60 / optimal_buses,
                "capacity": optimal_buses * base_capacity,
                "expected_demand": period_demand
            }
    
    # Combine schedules
    optimized_schedule = {
        "metro": metro_schedule,
        "bus": bus_schedule
    }
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return optimized_schedule, execution_time

def allocate_road_maintenance_resources(existing_roads_df, neighborhoods_df, budget=1000):
    """
    Uses dynamic programming to solve the resource allocation problem for road maintenance
    in areas with poor road conditions.
    
    Parameters:
    -----------
    existing_roads_df : pandas DataFrame
        DataFrame containing information about existing roads
    neighborhoods_df : pandas DataFrame
        DataFrame containing information about neighborhoods
    budget : float, optional
        Total maintenance budget in Million EGP
    
    Returns:
    --------
    dict
        Optimal allocation of maintenance resources
    float
        Execution time in seconds
    """
    start_time = time.time()
    
    # Extract road condition data
    roads = []
    for _, row in existing_roads_df.iterrows():
        from_id = str(row["FromID"]).strip()
        to_id = str(row["ToID"]).strip()
        distance_km = float(row["Distance(km)"])
        condition = float(row["Condition(1-10)"])
        
        # Calculate maintenance priority (lower condition = higher priority)
        # Also consider road length (longer roads with bad condition are prioritized)
        maintenance_priority = (10 - condition) * distance_km
        
        # Estimate maintenance cost (worse condition = higher cost)
        # Cost model: 1 Million EGP per km for a road in worst condition (1/10)
        # Better conditions cost proportionally less
        maintenance_cost = distance_km * (11 - condition) / 10
        
        # Calculate benefit of maintenance (improvement in condition)
        # Assume maintenance brings condition to 9/10
        condition_improvement = max(0, 9 - condition)
        
        # Calculate benefit per cost
        benefit = condition_improvement * distance_km
        
        roads.append({
            "road_id": f"{from_id}-{to_id}",
            "from_id": from_id,
            "to_id": to_id,
            "distance_km": distance_km,
            "current_condition": condition,
            "maintenance_priority": maintenance_priority,
            "maintenance_cost": maintenance_cost,
            "benefit": benefit
        })
    
    # Sort roads by maintenance priority (descending)
    roads.sort(key=lambda x: x["maintenance_priority"], reverse=True)
    
    # Get population data for neighborhoods
    population_by_id = {}
    for _, row in neighborhoods_df.iterrows():
        node_id = str(row["ID"]).strip()
        population = float(row["Population"])
        population_by_id[node_id] = population
    
    # Calculate population affected by each road
    for road in roads:
        from_pop = population_by_id.get(road["from_id"], 0)
        to_pop = population_by_id.get(road["to_id"], 0)
        road["affected_population"] = from_pop + to_pop
        
        # Adjust benefit by population affected
        road["population_adjusted_benefit"] = road["benefit"] * (road["affected_population"] / 100000)
    
    # Dynamic Programming for Knapsack Problem
    # Convert budget to integer units for DP (1 unit = 0.1 Million EGP)
    budget_units = int(budget * 10)
    
    # Initialize DP table
    dp = [0] * (budget_units + 1)
    selected_roads = [[] for _ in range(budget_units + 1)]
    
    # Fill DP table
    for road in roads:
        cost_units = int(road["maintenance_cost"] * 10)
        if cost_units <= 0:
            continue
            
        for b in range(budget_units, cost_units - 1, -1):
            new_benefit = dp[b - cost_units] + road["population_adjusted_benefit"]
            if new_benefit > dp[b]:
                dp[b] = new_benefit
                selected_roads[b] = selected_roads[b - cost_units] + [road["road_id"]]
    
    # Find optimal solution
    optimal_budget_units = max(range(budget_units + 1), key=lambda b: dp[b])
    optimal_roads = selected_roads[optimal_budget_units]
    
    # Create result dictionary
    maintenance_plan = {
        "total_budget": budget,
        "used_budget": optimal_budget_units / 10,
        "total_benefit": dp[optimal_budget_units],
        "roads_to_maintain": []
    }
    
    # Add details for selected roads
    for road_id in optimal_roads:
        road_info = next(road for road in roads if road["road_id"] == road_id)
        maintenance_plan["roads_to_maintain"].append({
            "road_id": road_id,
            "from_id": road_info["from_id"],
            "to_id": road_info["to_id"],
            "distance_km": road_info["distance_km"],
            "current_condition": road_info["current_condition"],
            "maintenance_cost": road_info["maintenance_cost"],
            "benefit": road_info["benefit"],
            "affected_population": road_info["affected_population"]
        })
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return maintenance_plan, execution_time

def memoized_path_planning(G, traffic_data, start, end, time_period, memo=None):
    """
    Applies memoization techniques to improve performance of route planning algorithms.
    
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
    memo : dict, optional
        Memoization dictionary for storing computed paths
    
    Returns:
    --------
    list
        Path from start to end
    float
        Total path weight
    dict
        Updated memoization dictionary
    float
        Execution time in seconds
    """
    start_time = time.time()
    
    # Initialize memoization dictionary if not provided
    if memo is None:
        memo = {}
    
    # Check if path is already computed
    key = (start, end, time_period)
    if key in memo:
        path, weight = memo[key]
        end_time = time.time()
        execution_time = end_time - start_time
        return path, weight, memo, execution_time
    
    # If path is not in memo, compute it using Dijkstra's algorithm
    distances = {node: float('inf') for node in G.nodes}
    distances[start] = 0
    previous = {node: None for node in G.nodes}
    edge_keys = {node: {} for node in G.nodes}
    pq = [(0, start)]
    
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
                road_type = data.get('road_type', 'existing')
                
                # Skip if road type is not suitable for cars
                if road_type not in ['existing', 'potential', 'virtual_connection', 'virtual_link']:
                    continue
                
                # Get traffic flow for this road
                capacity = data.get('capacity', 2000)
                traffic_flow = traffic_data.get(time_period.lower(), {}).get((str(current_node), str(neighbor)), capacity)
                
                # Calculate speed based on traffic
                base_speed = 120  # km/h for cars
                if traffic_flow is not None:
                    traffic_factor = traffic_flow / capacity if capacity > 0 else 1.0
                    traffic_factor = max(0.5, min(traffic_factor, 1.5))  # Cap between 0.5 and 1.5
                    speed = base_speed / traffic_factor
                else:
                    speed = base_speed
                
                # Convert distance to time (in minutes)
                distance_km = base_distance / 1000
                weight = (distance_km / speed) * 60  # minutes
                
                # Avoid extremely long detours
                if base_distance > 50000:  # Skip edges longer than 50 km
                    continue
                    
                distance = distances[current_node] + weight
                
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current_node
                    edge_keys[neighbor][current_node] = key
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
                base_distance = G[current][next_node][key].get('distance', 1000)
                
                # Calculate weight for this edge
                road_type = G[current][next_node][key].get('road_type', 'existing')
                capacity = G[current][next_node][key].get('capacity', 2000)
                traffic_flow = traffic_data.get(time_period.lower(), {}).get((str(current), str(next_node)), capacity)
                
                base_speed = 120  # km/h for cars
                if traffic_flow is not None:
                    traffic_factor = traffic_flow / capacity if capacity > 0 else 1.0
                    traffic_factor = max(0.5, min(traffic_factor, 1.5))
                    speed = base_speed / traffic_factor
                else:
                    speed = base_speed
                
                distance_km = base_distance / 1000
                weight = (distance_km / speed) * 60
                
                total_weight += weight
            current = next_node
        path.reverse()
    
    # Store result in memo
    memo[key] = (path, total_weight)
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return path, total_weight, memo, execution_time
