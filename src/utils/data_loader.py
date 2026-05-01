"""
Data Loader Utility for Smart City Transportation Project

This module provides functions for loading and processing data from Excel files.
"""

import pandas as pd
from collections import defaultdict

def load_data(file_paths):
    """
    Load data from Excel files and organize it for use in the transportation network.
    
    Parameters:
    -----------
    file_paths : dict
        Dictionary containing paths to Excel files
    
    Returns:
    --------
    dict
        Dictionary containing loaded and processed data
    """
    try:
        bus_routes_df = pd.read_excel(file_paths["bus_routes"])
        metro_lines_df = pd.read_excel(file_paths["metro_lines"])
        facilities_df = pd.read_excel(file_paths["facilities"])
        existing_roads_df = pd.read_excel(file_paths["existing_roads"])
        neighborhoods_df = pd.read_excel(file_paths["neighborhoods"])
        potential_roads_df = pd.read_excel(file_paths["potential_roads"])
        public_demand_df = pd.read_excel(file_paths["public_demand"])
        traffic_flow_df = pd.read_excel(file_paths["traffic_flow"])
        
        # Organize traffic data
        traffic_data = {}
        for _, row in traffic_flow_df.iterrows():
            road_id = row["RoadID"]
            if "-" in road_id:
                from_id, to_id = road_id.split("-")
                traffic_data.setdefault("morning", {}).setdefault((from_id, to_id), row["MorningPeak(veh/h)"])
                traffic_data.setdefault("afternoon", {}).setdefault((from_id, to_id), row["Afternoon(veh/h)"])
                traffic_data.setdefault("evening", {}).setdefault((from_id, to_id), row["Evening Peak(veh/h)"])
                traffic_data.setdefault("night", {}).setdefault((from_id, to_id), row["Night(veh/h)"])
        
        return {
            "bus_routes": bus_routes_df,
            "metro_lines": metro_lines_df,
            "facilities": facilities_df,
            "existing_roads": existing_roads_df,
            "neighborhoods": neighborhoods_df,
            "potential_roads": potential_roads_df,
            "public_demand": public_demand_df,
            "traffic_data": traffic_data
        }
    except Exception as e:
        raise Exception(f"Error loading data: {str(e)}")
