"""
Main Application for Smart City Transportation Project

This module implements the Streamlit web application for the Smart City Transportation Project.
"""

import streamlit as st
import os
import folium
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu
import uuid
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO

# Import utility modules
from src.utils.data_loader import load_data
from src.utils.graph_utils import create_graph, get_available_places

# Import algorithm modules
from algorithms.greedy.dijkstra import dijkstra_with_traffic, simulate_emergency_delay
from algorithms.greedy.a_star import a_star_emergency_routing
from algorithms.mst.modified_mst import population_weighted_mst, budget_constrained_mst, connectivity_based_mst, draw_mst
from algorithms.greedy.dijkstra import get_time_complexity
from algorithms.dynamic_programming.dp_solutions import optimize_public_transport_schedule
from algorithms.transit.transit_integration import optimize_transit_connections, optimize_bus_routes
from src.utils.ml_traffic import get_predictor
from algorithms.greedy.race_visualizer import dijkstra_step_by_step, a_star_step_by_step

# Set page configuration
st.set_page_config(
    page_title="Cairo Transportation Simulator",
    page_icon=":map:",
    layout="wide",
    initial_sidebar_state='collapsed'
)

# Initialize session state
if 'transport_mode' not in st.session_state:
    st.session_state.transport_mode = "car"
if 'start_node' not in st.session_state:
    st.session_state.start_node = None
if 'end_node' not in st.session_state:
    st.session_state.end_node = None

# File paths
data_files = {
    "bus_routes": "data/excel/Current Bus Routes.xlsx",
    "metro_lines": "data/excel/Current Metro Lines.xlsx",
    "facilities": "data/excel/Important Facilities.xlsx",
    "existing_roads": "data/excel/Existing Roads.xlsx",
    "neighborhoods": "data/excel/Neighborhoods and Districts.xlsx",
    "potential_roads": "data/excel/Potential New Roads.xlsx",
    "public_demand": "data/excel/Public Transportation Demand.xlsx",
    "traffic_flow": "data/excel/Traffic Flow Patterns.xlsx"
}

# Speed assumptions (km/h)
SPEEDS = {
    "car": 120,
    "bus": 100,
    "metro": 90,
    "emergency": 100
}

# Sidebar Navigation
with st.sidebar:
    choose = option_menu(None, ["Home", "Graph", "MST", "Transit Scheduling", "ML Traffic Prediction", "Algorithm Comparison", "About"],
                         icons=['house', 'map', 'diagram-3', 'calendar2-week', 'book'],
                         menu_icon="app-indicator",
                         default_index=0,
                         styles={
        "container": {"padding": "5!important", "background-color": "#fafafa"},
        "icon": {"color": '#E0E0EF', "font-size": "25px"},
        "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "#eee"},
        "nav-link-selected": {"background-color": "#02ab21"},
    }
)

# Home Page (Main Simulation)
if choose == "Home":
    st.write('# Cairo Transportation Simulator')
    st.subheader('Simulate transportation routes in Cairo with an interactive map.')

    # Load data and build graph
    if all(os.path.exists(f) for f in data_files.values()):
        try:
            data = load_data(data_files)
            G, bus_stops, metro_stations, traffic_data = create_graph(data)
            
            # Initialize variables
            all_places = {node: G.nodes[node]['name'] for node in G.nodes}
            emergency_places = get_available_places(G, bus_stops, metro_stations, 'emergency')
            emergency_path = None
            emergency_distance = 0

            # Create a simplified Cairo map with Folium
            cairo_center = [30.0444, 31.2357]
            m = folium.Map(location=cairo_center, zoom_start=10, control_scale=True)

            # Add nodes to the map with labels
            for node, data in G.nodes(data=True):
                if 'pos' in data:
                    x, y = data['pos']
                    folium.CircleMarker(
                        location=[y, x],
                        radius=5,
                        color='blue',
                        fill=True,
                        fill_color='blue',
                        popup=f"{data['name']}"
                    ).add_to(m)
                    folium.Marker(
                        location=[y, x],
                        icon=folium.DivIcon(
                            html=f'<div style="font-size: 10pt; color: black; font-weight: bold;">{data["name"]}</div>',
                            icon_size=(150, 36),
                            icon_anchor=(0, 0)
                        )
                    ).add_to(m)

            # Add all edges to the map (full graph)
            for u, v, data in G.edges(data=True):
                if 'pos' in G.nodes[u] and 'pos' in G.nodes[v]:
                    u_pos = G.nodes[u]['pos']
                    v_pos = G.nodes[v]['pos']
                    distance_km = data['distance'] / 1000
                    if distance_km > 100:
                        st.warning(f"Unrealistic distance between {G.nodes[u]['name']} and {G.nodes[v]['name']}: {distance_km:.2f} km. Check the data.")
                        continue
                    folium.PolyLine(
                        locations=[[u_pos[1], u_pos[0]], [v_pos[1], v_pos[0]]],
                        color='gray',
                        weight=1,
                        opacity=0.5,
                        popup=f"Distance: {distance_km:.2f} km"
                    ).add_to(m)

            # Transportation Simulation Section
            st.subheader("Transportation Simulation")
            
            # Use columns to arrange selectboxes side by side (two per row)
            col1, col2 = st.columns(2)
            with col1:
                transport_mode = st.selectbox("Transport Mode", ["car", "bus", "metro", "emergency"], key="transport_mode_select")
                if st.session_state.transport_mode != transport_mode:
                    st.session_state.transport_mode = transport_mode
                    st.session_state.start_node = None
                    st.session_state.end_node = None
            
            with col2:
                available_places = get_available_places(G, bus_stops, metro_stations, transport_mode)
                if not available_places:
                    st.error(f"No places available for {transport_mode.title()} mode. Check your data.")
                    place_options = {}
                    place_names = []
                else:
                    place_options = {name: node for node, name in sorted(available_places.items(), key=lambda x: x[1])}
                    place_names = list(place_options.keys())
                    start_index = place_names.index(st.session_state.start_node) if st.session_state.start_node in place_names else 0
                    start_node = st.selectbox("Start Point", place_names, index=start_index, key="start_node_select")
                    st.session_state.start_node = start_node
                    start_node_id = place_options[start_node]

            col3, col4 = st.columns(2)
            with col3:
                if available_places:
                    end_index = place_names.index(st.session_state.end_node) if st.session_state.end_node in place_names else (1 if len(place_names) > 1 else 0)
                    end_node = st.selectbox("End Point", place_names, index=end_index, key="end_node_select")
                    st.session_state.end_node = end_node
                    end_node_id = place_options[end_node]
            
            with col4:
                time_period = st.selectbox("Time Period", ["morning", "afternoon", "evening", "night"], key="time_period")

            # Emergency Vehicle Simulation Section (only for car mode)
            simulate_emergency = False
            if transport_mode == "car":
                st.subheader("Emergency Vehicle Simulation")
                simulate_emergency = st.checkbox("Run Emergency Vehicle Simulation (affects car route)")

            # Form for simulation submission with centered button
            with st.form(key="simulation_form", clear_on_submit=True):
                st.markdown(
                    """
                    <style>
                    div.stButton > button {
                        width: 200px;
                        margin: 0 auto;
                        display: block;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True
                )
                submit_button = st.form_submit_button("Simulate Route")

                if submit_button:
                    # Run transportation simulation
                    if not available_places:
                        st.error(f"No places available for {transport_mode.title()} mode. Cannot simulate.")
                    elif start_node_id in G.nodes and end_node_id in G.nodes and time_period:
                        if start_node_id == end_node_id:
                            st.error("Start point and end point cannot be the same. Please select different points.")
                        elif transport_mode == 'emergency' and not (start_node_id in emergency_places or end_node_id in emergency_places):
                            st.error("In emergency mode, at least one of the points (start or end) must be a hospital/medical facility.")
                        else:
                            # Calculate the main path based on transport mode
                            execution_time = 0
                            algo_name = ""
                            if transport_mode == 'emergency':
                                path, total_distance, total_travel_time, edge_keys, execution_time = a_star_emergency_routing(G, traffic_data, start_node_id, end_node_id, time_period)
                                algo_name = "a_star_emergency_routing"
                            else:
                                path, total_distance, total_travel_time, edge_keys, execution_time = dijkstra_with_traffic(G, traffic_data, start_node_id, end_node_id, time_period, None, transport_mode, emergency_path, emergency_active=bool(emergency_path))
                                algo_name = "dijkstra_with_traffic"

                            if path:
                                st.success(f"Best Path from {G.nodes[start_node_id]['name']} to {G.nodes[end_node_id]['name']} during {time_period.title()} via {transport_mode.title()}:")
                                path_text = " -> ".join(G.nodes[node]['name'] for node in path)
                                st.write(path_text)

                                distance_km = total_distance / 1000
                                if distance_km > 100:
                                    st.error(f"Unrealistic total distance: {distance_km:.2f} km. The path might be incorrect. Check the graph data.")
                                speed = SPEEDS[transport_mode]
                                travel_time_minutes = total_travel_time
                                st.write(f"Total Distance: {distance_km:.2f} km")
                                st.write(f"Estimated Travel Time: {travel_time_minutes:.2f} minutes")
                                
                                # Display cost information
                                if transport_mode == 'car':
                                    fuel_cost_per_km = 0.5  # EGP per km
                                    fuel_cost = distance_km * fuel_cost_per_km
                                    st.write(f"Estimated Fuel Cost: {fuel_cost:.2f} EGP")
                                elif transport_mode == 'bus':
                                    ticket_cost = 5  # EGP
                                    st.write(f"Bus Ticket Cost: {ticket_cost:.2f} EGP")
                                elif transport_mode == 'metro':
                                    ticket_cost = 10  # EGP
                                    st.write(f"Metro Ticket Cost: {ticket_cost:.2f} EGP")
                                
                                st.write(f"Actual Execution Time: {execution_time:.6f} seconds")
                                st.write(f"Theoretical Time Complexity: {get_time_complexity(algo_name)}")

                                # Run emergency simulation if enabled and transport mode is car
                                if transport_mode == 'car' and simulate_emergency:
                                    emergency_path, emergency_distance, emergency_travel_time, emergency_edge_keys, emergency_execution_time = a_star_emergency_routing(G, traffic_data, start_node_id, end_node_id, time_period)
                                    if emergency_path:
                                        st.success(f"Emergency Path (Simulation) from {G.nodes[start_node_id]['name']} to {G.nodes[end_node_id]['name']} during {time_period.title()}.")
                                        emergency_distance_km = emergency_distance / 1000
                                        st.write(f"Distance: {emergency_distance_km:.2f} km")
                                        emergency_speed = SPEEDS["emergency"]
                                        emergency_time_minutes = emergency_travel_time
                                        st.write(f"Estimated Travel Time: {emergency_time_minutes:.2f} minutes")
                                        st.write(f"Actual Execution Time: {emergency_execution_time:.6f} seconds")
                                        st.write(f"Theoretical Time Complexity: {get_time_complexity('a_star_emergency_routing')}")

                                        # Simulate the impact of the emergency vehicle on the car's path
                                        new_path, delay = simulate_emergency_delay(G, traffic_data, path, emergency_path, time_period, time_period)
                                        if delay > 0:
                                            delay_km = delay / 1000
                                            if delay_km > distance_km * 0.5:
                                                st.warning(f"Unrealistic delay due to Emergency Vehicle: {delay_km:.2f} km. Capping delay to 50% of the original distance.")
                                                delay_km = distance_km * 0.5
                                                delay = delay_km * 1000
                                            delay_time_minutes = (delay_km / speed) * 60
                                            st.warning(f"Delay due to Emergency Vehicle: {delay_km:.2f} km (~{delay_time_minutes:.2f} minutes)")
                                            path = new_path
                                            total_distance += delay
                                            distance_km = total_distance / 1000
                                            travel_time_minutes += delay_time_minutes
                                            st.write(f"Updated Total Distance: {distance_km:.2f} km")
                                            st.write(f"Updated Estimated Travel Time: {travel_time_minutes:.2f} minutes")
                                            
                                            # Update cost information
                                            fuel_cost_per_km = 0.5  # EGP per km
                                            fuel_cost = distance_km * fuel_cost_per_km
                                            st.write(f"Updated Estimated Fuel Cost: {fuel_cost:.2f} EGP")

                                path_coords = [G.nodes[node]['pos'][::-1] for node in path]
                                if path:
                                    folium.PolyLine(locations=path_coords, color='red', weight=3, opacity=0.8, popup="Main Path").add_to(m)
                                    if emergency_path and transport_mode == 'car' and simulate_emergency:
                                        folium.PolyLine(locations=[G.nodes[node]['pos'][::-1] for node in emergency_path], color='green', weight=3, opacity=0.8, dash_array='5', popup="Emergency Path").add_to(m)

                                st.subheader("Cairo Map with Routes")
                                st_folium(m, width="100%")

                            else:
                                st.error(f"No path found between {G.nodes[start_node_id]['name']} and {G.nodes[end_node_id]['name']} using {transport_mode.title()}. Ensure there are valid routes for this mode.")

        except Exception as e:
            st.error(f"Error loading data or building the graph: {str(e)}")
    else:
        st.error("Please upload all required Excel files to proceed.")

# Graph Page
elif choose == "Graph":
    st.write("## Transportation Network Graph")
    st.markdown("This page displays the full transportation graph of Cairo, including all nodes and edges.")

    # Load data and build graph
    if all(os.path.exists(f) for f in data_files.values()):
        try:
            data = load_data(data_files)
            G, bus_stops, metro_stations, traffic_data = create_graph(data)

            # Create a simplified Cairo map with Folium for the graph
            cairo_center = [30.0444, 31.2357]
            m = folium.Map(location=cairo_center, zoom_start=10, control_scale=True)

            # Add nodes to the map with labels
            for node, data in G.nodes(data=True):
                if 'pos' in data:
                    x, y = data['pos']
                    node_type = data.get('type', 'regular')
                    
                    # Use different colors for different node types
                    color = 'blue'
                    if node_type == 'hospital':
                        color = 'red'
                    elif node_type == 'school':
                        color = 'green'
                    elif node_type == 'government':
                        color = 'purple'
                    
                    folium.CircleMarker(
                        location=[y, x],
                        radius=5,
                        color=color,
                        fill=True,
                        fill_color=color,
                        popup=f"{data['name']} ({node_type})"
                    ).add_to(m)
                    
                    # Only add labels for important nodes to avoid clutter
                    if node_type in ['hospital', 'school', 'government']:
                        folium.Marker(
                            location=[y, x],
                            icon=folium.DivIcon(
                                html=f'<div style="font-size: 10pt; color: black; font-weight: bold;">{data["name"]}</div>',
                                icon_size=(150, 36),
                                icon_anchor=(0, 0)
                            )
                        ).add_to(m)

            # Add edges to the map with different colors for different road types
            for u, v, data in G.edges(data=True):
                if 'pos' in G.nodes[u] and 'pos' in G.nodes[v]:
                    u_pos = G.nodes[u]['pos']
                    v_pos = G.nodes[v]['pos']
                    road_type = data.get('road_type', 'existing')
                    
                    # Use different colors for different road types
                    color = 'gray'
                    weight = 1
                    if road_type == 'existing':
                        color = 'gray'
                    elif road_type == 'potential':
                        color = 'orange'
                        weight = 2
                    elif road_type == 'bus':
                        color = 'green'
                    elif road_type == 'metro':
                        color = 'blue'
                    
                    distance_km = data['distance'] / 1000
                    if distance_km > 100:
                        continue  # Skip unrealistic distances
                    
                    folium.PolyLine(
                        locations=[[u_pos[1], u_pos[0]], [v_pos[1], v_pos[0]]],
                        color=color,
                        weight=weight,
                        opacity=0.7,
                        popup=f"Type: {road_type}, Distance: {distance_km:.2f} km"
                    ).add_to(m)

            # Display the map
            st.subheader("Cairo Transportation Network")
            st_folium(m, width="100%")

            # Display graph statistics
            st.subheader("Graph Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Number of Nodes", len(G.nodes))
            with col2:
                st.metric("Number of Edges", len(G.edges))
            with col3:
                st.metric("Number of Bus Stops", len(bus_stops))

            # Display legend
            st.subheader("Legend")
            legend_col1, legend_col2 = st.columns(2)
            with legend_col1:
                st.markdown("**Node Types:**")
                st.markdown("🔵 Regular Node")
                st.markdown("🔴 Hospital")
                st.markdown("🟢 School")
                st.markdown("🟣 Government Building")
            
            with legend_col2:
                st.markdown("**Road Types:**")
                st.markdown("⚫ Existing Road")
                st.markdown("🟠 Potential New Road")
                st.markdown("🟢 Bus Route")
                st.markdown("🔵 Metro Line")

        except Exception as e:
            st.error(f"Error loading data or building the graph: {str(e)}")
    else:
        st.error("Please upload all required Excel files to proceed.")

# MST Page
elif choose == "MST":
    st.write("## Transportation Network Graph")
    st.markdown("This page displays the full transportation graph of Cairo, including all nodes and edges.")

    # Load data and build graph
    if all(os.path.exists(f) for f in data_files.values()):
        try:
            data = load_data(data_files)
            G, bus_stops, metro_stations, traffic_data = create_graph(data)
            
            # Calculate MST
            mst_edges, analysis, execution_time = population_weighted_mst(
                G, 
                data["neighborhoods"], 
                data["facilities"]
            )
            
            # Display MST information
            st.write("## Minimum Spanning Tree (MST)")
            st.markdown("This page displays the full transportation graph of Cairo, including all nodes and edges.")
            
            # Display MST statistics
            st.subheader("MST Weight: {:.2f} km".format(analysis['total_distance_km']))
            st.write("Actual Execution Time: {:.6f} seconds".format(execution_time))
            st.write("Theoretical Time Complexity: O(E log E), where E is the number of edges (due to sorting edges and Union-Find operations)")
            
            # Create a simplified Cairo map with Folium for the MST
            cairo_center = [30.0444, 31.2357]
            m = folium.Map(location=cairo_center, zoom_start=10, control_scale=True)
            
            # Add nodes to the map with green color
            for node, data in G.nodes(data=True):
                if 'pos' in data:
                    x, y = data['pos']
                    folium.CircleMarker(
                        location=[y, x],
                        radius=5,
                        color='green',
                        fill=True,
                        fill_color='green',
                        popup=f"{node}"
                    ).add_to(m)
                    
                    # Add node labels
                    folium.Marker(
                        location=[y, x],
                        icon=folium.DivIcon(
                            html=f'<div style="font-size: 10pt; color: black; font-weight: bold;">{node}</div>',
                            icon_size=(150, 36),
                            icon_anchor=(0, 0)
                        )
                    ).add_to(m)
            
            # Add MST edges in green
            for u, v, data in mst_edges:
                if 'pos' in G.nodes[u] and 'pos' in G.nodes[v]:
                    u_pos = G.nodes[u]['pos']
                    v_pos = G.nodes[v]['pos']
                    
                    folium.PolyLine(
                        locations=[[u_pos[1], u_pos[0]], [v_pos[1], v_pos[0]]],
                        color='green',
                        weight=2,
                        opacity=0.8,
                        popup=f"MST Edge: {u} - {v}"
                    ).add_to(m)
            
            # Display the map
            st.subheader("Minimum Spanning Tree (MST)")
            st_folium(m, width="100%")

        except Exception as e:
            st.error(f"Error calculating or visualizing MST: {str(e)}")
    else:
        st.error("Please upload all required Excel files to proceed.")

# Transit Scheduling Page
elif choose == "Transit Scheduling":
    st.write("## Public Transit Scheduling")
    st.markdown("This page provides optimization for public transportation schedules and routes.")

    # Load data and build graph
    if all(os.path.exists(f) for f in data_files.values()):
        try:
            data = load_data(data_files)
            G, bus_stops, metro_stations, traffic_data = create_graph(data)
            
            # Transit Scheduling Tabs
            tab1, tab2, tab3 = st.tabs(["Schedule Optimization", "Bus Route Optimization", "Transit Connections"])
            
            # Schedule Optimization Tab
            with tab1:
                st.subheader("Public Transportation Schedule Optimization")
                st.markdown("Optimize metro and bus schedules based on demand patterns.")
                
                if st.button("Optimize Schedules"):
                    with st.spinner("Optimizing schedules..."):
                        optimized_schedule, execution_time = optimize_public_transport_schedule(
                            data["metro_lines"],
                            data["bus_routes"],
                            data["public_demand"]
                        )
                        
                        st.success(f"Schedules optimized in {execution_time:.4f} seconds")
                        
                        # Display Metro Schedules
                        st.subheader("Metro Line Schedules")
                        
                        # Create a DataFrame for metro schedules
                        metro_data = []
                        for line_id, periods in optimized_schedule["metro"].items():
                            for period, details in periods.items():
                                metro_data.append({
                                    "Line ID": line_id,
                                    "Time Period": period.capitalize(),
                                    "Trains/Hour": details["trains_per_hour"],
                                    "Headway (min)": details["headway_minutes"],
                                    "Capacity": details["capacity"],
                                    "Expected Demand": f"{details['expected_demand']:.0f}"
                                })
                        
                        metro_df = pd.DataFrame(metro_data)
                        st.dataframe(metro_df)
                        
                        # Display Bus Schedules
                        st.subheader("Bus Route Schedules")
                        
                        # Create a DataFrame for bus schedules
                        bus_data = []
                        for route_id, periods in optimized_schedule["bus"].items():
                            for period, details in periods.items():
                                bus_data.append({
                                    "Route ID": route_id,
                                    "Time Period": period.capitalize(),
                                    "Buses/Hour": details["buses_per_hour"],
                                    "Headway (min)": details["headway_minutes"],
                                    "Capacity": details["capacity"],
                                    "Expected Demand": f"{details['expected_demand']:.0f}"
                                })
                        
                        bus_df = pd.DataFrame(bus_data)
                        st.dataframe(bus_df)
                        
                        # Display cost information
                        st.subheader("Cost Information")
                        
                        # Calculate operational costs
                        metro_cost_per_train_hour = 5000  # EGP
                        bus_cost_per_bus_hour = 500  # EGP
                        
                        # Calculate total trains and buses per day
                        total_train_hours = sum(details["trains_per_hour"] for line in optimized_schedule["metro"].values() for details in line.values())
                        total_bus_hours = sum(details["buses_per_hour"] for route in optimized_schedule["bus"].values() for details in route.values())
                        
                        # Calculate daily costs
                        daily_metro_cost = total_train_hours * metro_cost_per_train_hour
                        daily_bus_cost = total_bus_hours * bus_cost_per_bus_hour
                        total_daily_cost = daily_metro_cost + daily_bus_cost
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Daily Metro Cost", f"{daily_metro_cost:,.2f} EGP")
                        with col2:
                            st.metric("Daily Bus Cost", f"{daily_bus_cost:,.2f} EGP")
                        with col3:
                            st.metric("Total Daily Cost", f"{total_daily_cost:,.2f} EGP")
            
            # Bus Route Optimization Tab
            with tab2:
                st.subheader("Bus Route Optimization")
                st.markdown("Optimize bus routes based on demand and population distribution.")
                
                if st.button("Optimize Bus Routes"):
                    with st.spinner("Optimizing bus routes..."):
                        optimized_routes, execution_time = optimize_bus_routes(
                            G,
                            data["bus_routes"],
                            data["neighborhoods"],
                            data["public_demand"]
                        )
                        
                        st.success(f"Bus routes optimized in {execution_time:.4f} seconds")
                        
                        # Display optimized routes
                        for route_id, route_info in optimized_routes.items():
                            st.subheader(f"Route {route_id}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("**Current Route Information:**")
                                st.write(f"Stops: {', '.join(route_info['original_stops'])}")
                                st.write(f"Buses Assigned: {route_info['original_buses']}")
                                st.write(f"Daily Passengers: {route_info['original_passengers']}")
                                st.write(f"Route Length: {route_info['current_length_meters']/1000:.2f} km")
                            
                            with col2:
                                st.write("**Suggested Improvements:**")
                                if route_info['suggested_additions']:
                                    for from_id, to_id, passengers in route_info['suggested_additions']:
                                        st.write(f"Add connection between {G.nodes[from_id]['name']} and {G.nodes[to_id]['name']} ({passengers} daily passengers)")
                                else:
                                    st.write("No improvements suggested for this route.")
                            
                            # Display cost information
                            st.write("**Cost Information:**")
                            bus_cost_per_km = 2.5  # EGP per km
                            daily_distance = route_info['current_length_meters'] / 1000 * route_info['original_buses'] * 10  # Assume each bus makes 10 trips
                            daily_cost = daily_distance * bus_cost_per_km
                            st.write(f"Estimated Daily Operational Cost: {daily_cost:,.2f} EGP")
                            
                            st.markdown("---")
            
            # Transit Connections Tab
            with tab3:
                st.subheader("Transit Connection Optimization")
                st.markdown("Optimize connections between different transit modes (bus and metro).")
                
                if st.button("Optimize Transit Connections"):
                    with st.spinner("Optimizing transit connections..."):
                        recommended_connections, execution_time = optimize_transit_connections(
                            G,
                            bus_stops,
                            metro_stations,
                            data["neighborhoods"],
                            data["public_demand"]
                        )
                        
                        st.success(f"Transit connections optimized in {execution_time:.4f} seconds")
                        
                        # Display recommended connections
                        st.subheader("Recommended New Connections")
                        
                        # Create a DataFrame for connections
                        connections_data = []
                        for conn in recommended_connections:
                            connections_data.append({
                                "Bus Stop": G.nodes[conn['bus_stop']]['name'],
                                "Metro Station": G.nodes[conn['metro_station']]['name'],
                                "Distance (m)": f"{conn['distance']:.0f}",
                                "Potential Demand": f"{conn['demand']:.0f}",
                                "Score": f"{conn['score']:.4f}"
                            })
                        
                        connections_df = pd.DataFrame(connections_data)
                        st.dataframe(connections_df)
                        
                        # Display on map
                        cairo_center = [30.0444, 31.2357]
                        m = folium.Map(location=cairo_center, zoom_start=10, control_scale=True)
                        
                        # Add bus stops and metro stations
                        for node in bus_stops:
                            if node in G.nodes and 'pos' in G.nodes[node]:
                                x, y = G.nodes[node]['pos']
                                folium.CircleMarker(
                                    location=[y, x],
                                    radius=5,
                                    color='green',
                                    fill=True,
                                    fill_color='green',
                                    popup=f"Bus Stop: {G.nodes[node]['name']}"
                                ).add_to(m)
                        
                        for node in metro_stations:
                            if node in G.nodes and 'pos' in G.nodes[node]:
                                x, y = G.nodes[node]['pos']
                                folium.CircleMarker(
                                    location=[y, x],
                                    radius=5,
                                    color='blue',
                                    fill=True,
                                    fill_color='blue',
                                    popup=f"Metro Station: {G.nodes[node]['name']}"
                                ).add_to(m)
                        
                        # Add recommended connections
                        for conn in recommended_connections:
                            bus_stop = conn['bus_stop']
                            metro_station = conn['metro_station']
                            
                            if bus_stop in G.nodes and metro_station in G.nodes and 'pos' in G.nodes[bus_stop] and 'pos' in G.nodes[metro_station]:
                                bus_pos = G.nodes[bus_stop]['pos']
                                metro_pos = G.nodes[metro_station]['pos']
                                
                                folium.PolyLine(
                                    locations=[[bus_pos[1], bus_pos[0]], [metro_pos[1], metro_pos[0]]],
                                    color='purple',
                                    weight=3,
                                    opacity=0.8,
                                    popup=f"Recommended Connection: {G.nodes[bus_stop]['name']} - {G.nodes[metro_station]['name']}, Distance: {conn['distance']:.0f}m, Demand: {conn['demand']:.0f}"
                                ).add_to(m)
                        
                        # Display the map
                        st.subheader("Recommended Transit Connections Map")
                        st_folium(m, width="100%")
                        
                        # Display cost information
                        st.subheader("Cost Information")
                        
                        # Calculate implementation costs
                        connection_cost_per_meter = 5000 / 1000  # EGP per meter
                        total_distance = sum(conn['distance'] for conn in recommended_connections)
                        total_implementation_cost = total_distance * connection_cost_per_meter
                        
                        st.write(f"Total Connection Distance: {total_distance:.0f} meters")
                        st.write(f"Estimated Implementation Cost: {total_implementation_cost:,.2f} EGP")
                        
                        # Calculate potential revenue
                        total_demand = sum(conn['demand'] for conn in recommended_connections)
                        ticket_price = 5  # EGP
                        daily_revenue = total_demand * ticket_price
                        
                        st.write(f"Total Potential Daily Demand: {total_demand:.0f} passengers")
                        st.write(f"Estimated Daily Revenue: {daily_revenue:,.2f} EGP")
                        
                        # Calculate ROI
                        if total_implementation_cost > 0:
                            days_to_roi = total_implementation_cost / daily_revenue
                            st.write(f"Estimated Days to ROI: {days_to_roi:.0f} days")

        except Exception as e:
            st.error(f"Error optimizing transit schedules: {str(e)}")
    else:
        st.error("Please upload all required Excel files to proceed.")

# ML Traffic Prediction Page
elif choose == "ML Traffic Prediction":
    st.write("## ML-Based Traffic Prediction")
    st.subheader("Predict traffic congestion using Random Forest Regressor")
    
    if all(os.path.exists(f) for f in data_files.values()):
        try:
            data = load_data(data_files)
            predictor = get_predictor(data_files)
            
            st.info("Model trained on historical temporal traffic data (Morning, Afternoon, Evening, Night).")
            
            col1, col2 = st.columns(2)
            with col1:
                roads_df = data["existing_roads"]
                neighborhoods_df = data["neighborhoods"]
                
                road_options = []
                for _, row in roads_df.iterrows():
                    from_id_str = str(row["FromID"])
                    to_id_str = str(row["ToID"])
                    from_name = neighborhoods_df[neighborhoods_df["ID"].astype(str) == from_id_str].iloc[0]["Name"]
                    to_name = neighborhoods_df[neighborhoods_df["ID"].astype(str) == to_id_str].iloc[0]["Name"]
                    road_options.append(f"{from_name} to {to_name} (ID: {from_id_str}-{to_id_str})")
                
                selected_road_str = st.selectbox("Select Road for Prediction", road_options)
                selected_road_idx = road_options.index(selected_road_str)
                selected_road = roads_df.iloc[selected_road_idx]
                
            with col2:
                time_period = st.selectbox("Select Time Period", ["Morning", "Afternoon", "Evening", "Night"], key="ml_time")
            
            if st.button("Predict Traffic Flow"):
                from_id = str(selected_road["FromID"])
                to_id = str(selected_road["ToID"])
                dist = selected_road["Distance(km)"]
                cap = selected_road["Current Capacity(vehicles/hour)"]
                cond = selected_road["Condition(1-10)"]
                from_pop = neighborhoods_df[neighborhoods_df["ID"].astype(str) == from_id].iloc[0]["Population"]
                to_pop = neighborhoods_df[neighborhoods_df["ID"].astype(str) == to_id].iloc[0]["Population"]
                
                prediction = predictor.predict(from_id, to_id, dist, cap, cond, from_pop, to_pop, time_period)
                
                st.metric(label=f"Predicted Traffic Flow ({time_period})", value=f"{prediction:.2f} veh/h")
                
                congestion_level = "Low"
                color = "green"
                ratio = prediction / cap
                if ratio > 0.8:
                    congestion_level = "High"
                    color = "red"
                elif ratio > 0.5:
                    congestion_level = "Moderate"
                    color = "orange"
                
                st.markdown(f"Congestion Level: <span style='color:{color}; font-weight:bold;'>{congestion_level}</span>", unsafe_allow_html=True)
                
                # Show feature importance (simplified)
                st.write("### Model Insights")
                st.write("The model considers distance, capacity, road condition, and population of connected districts to forecast congestion.")

        except Exception as e:
            st.error(f"Error in ML Prediction: {str(e)}")
    else:
        st.error("Please ensure all data files are available.")

# Algorithm Comparison Page
elif choose == "Algorithm Comparison":
    st.write("## Side-by-Side Algorithm Comparison")
    st.subheader("Dijkstra vs A* Race Animation")
    
    if all(os.path.exists(f) for f in data_files.values()):
        try:
            data = load_data(data_files)
            G, bus_stops, metro_stations, traffic_data = create_graph(data)
            
            available_places = {node: G.nodes[node]['name'] for node in G.nodes}
            place_options = {name: node for node, name in sorted(available_places.items(), key=lambda x: x[1])}
            place_names = list(place_options.keys())
            
            col1, col2 = st.columns(2)
            with col1:
                start_node = st.selectbox("Start Point", place_names, key="race_start")
                start_id = place_options[start_node]
            with col2:
                end_node = st.selectbox("End Point", place_names, index=1, key="race_end")
                end_id = place_options[end_node]
            
            if st.button("Start Race!"):
                dijkstra_visited = dijkstra_step_by_step(G, traffic_data, start_id, end_id, "morning")
                a_star_visited = a_star_step_by_step(G, traffic_data, start_id, end_id, "morning")
                
                col_d, col_a = st.columns(2)
                
                with col_d:
                    st.write("### Dijkstra's Algorithm")
                    st.write(f"Nodes Explored: {len(dijkstra_visited)}")
                    # Show progress
                    d_progress = st.progress(0)
                
                with col_a:
                    st.write("### A* Algorithm")
                    st.write(f"Nodes Explored: {len(a_star_visited)}")
                    a_progress = st.progress(0)
                
                # Animation loop
                max_steps = max(len(dijkstra_visited), len(a_star_visited))
                for i in range(max_steps):
                    if i < len(dijkstra_visited):
                        d_progress.progress((i + 1) / len(dijkstra_visited))
                    if i < len(a_star_visited):
                        a_progress.progress((i + 1) / len(a_star_visited))
                    time.sleep(0.05)
                
                st.success("Race Finished!")
                if len(a_star_visited) < len(dijkstra_visited):
                    st.write(f"🏆 **A* won!** It explored {len(dijkstra_visited) - len(a_star_visited)} fewer nodes by using a heuristic.")
                else:
                    st.write("Both algorithms explored similar number of nodes.")
                
                # Visual comparison table
                st.write("### Performance Comparison")
                comparison_data = {
                    "Metric": ["Nodes Explored", "Heuristic Used", "Guaranteed Optimal"],
                    "Dijkstra": [len(dijkstra_visited), "No", "Yes"],
                    "A*": [len(a_star_visited), "Yes (Euclidean)", "Yes (if admissible)"]
                }
                st.table(pd.DataFrame(comparison_data))

        except Exception as e:
            st.error(f"Error in Comparison: {str(e)}")
    else:
        st.error("Please ensure all data files are available.")

# About Page
elif choose == "About":
    st.write("## About the Smart City Transportation Project")
    st.markdown("""
    This application simulates and optimizes transportation networks for smart cities, with a focus on Cairo, Egypt.
    
    ### Features
    - **Multi-modal Transportation**: Simulate routes using cars, buses, metro, or emergency vehicles
    - **Traffic-aware Routing**: Consider traffic conditions at different times of day
    - **Emergency Vehicle Simulation**: Simulate the impact of emergency vehicles on regular traffic
    - **Network Analysis**: View and analyze the transportation network graph
    - **MST Visualization**: Visualize the Minimum Spanning Tree for optimal network design
    - **Transit Scheduling**: Optimize public transportation schedules and routes
    
    ### Algorithms
    The project implements several algorithms for transportation network optimization:
    
    - **Greedy Algorithms**: Dijkstra's Algorithm, A* Algorithm
    - **Dynamic Programming Solutions**: Schedule Optimization, Resource Allocation, Memoized Path Planning
    - **Minimum Spanning Tree (MST) Algorithms**: Population-weighted MST, Budget-constrained MST, Connectivity-based MST
    - **Transit Integration Algorithms**: Multi-modal Path Planning, Transit Connection Optimization, Bus Route Optimization
    
    ### Data Sources
    The application uses several data files for input:
    - Current Bus Routes
    - Current Metro Lines
    - Existing Roads
    - Important Facilities
    - Neighborhoods and Districts
    - Potential New Roads
    - Public Transportation Demand
    - Traffic Flow Patterns
    
    ### Contact
    For more information, please contact the development team.
    """)
