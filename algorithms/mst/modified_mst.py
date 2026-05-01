"""
Modified Minimum Spanning Tree (MST) Algorithm

This module implements a modified version of the Minimum Spanning Tree algorithm
for optimizing transportation networks with population and facility prioritization.
"""

import networkx as nx
import numpy as np
import time
import matplotlib.pyplot as plt
import io
import base64

def population_weighted_mst(G, neighborhoods_df, facilities_df, alpha=0.7, beta=0.3):
    """
    Implements a modified Kruskal's algorithm that prioritizes connections between
    high-population areas and ensures critical facilities have adequate connectivity.
    
    Parameters:
    -----------
    G : networkx.Graph
        Graph representing the transportation network
    neighborhoods_df : pandas DataFrame
        DataFrame containing information about neighborhoods and their populations
    facilities_df : pandas DataFrame
        DataFrame containing information about critical facilities
    alpha : float, optional
        Weight factor for population (default: 0.7)
    beta : float, optional
        Weight factor for critical facilities (default: 0.3)
    
    Returns:
    --------
    networkx.Graph
        Modified minimum spanning tree
    dict
        Analysis of the MST including cost and connectivity metrics
    float
        Execution time in seconds
    """
    start_time = time.time()
    
    # Create a new graph for the MST
    mst = nx.Graph()
    
    # Extract population data
    population_by_id = {}
    for _, row in neighborhoods_df.iterrows():
        node_id = str(row["ID"]).strip()
        population = float(row["Population"])
        population_by_id[node_id] = population
    
    # Extract critical facilities
    critical_facilities = []
    for _, row in facilities_df.iterrows():
        node_id = str(row["ID"]).strip()
        facility_type = str(row["Type"]).strip().lower()
        
        # Consider hospitals, government centers, airports, etc. as critical
        if any(keyword in facility_type for keyword in ["hospital", "medical", "government", "airport", "police", "fire"]):
            critical_facilities.append(node_id)
    
    # Prepare edges with modified weights
    edges = []
    for u, v, key, data in G.edges(keys=True, data=True):
        if 'distance' not in data:
            continue
            
        distance = data['distance']
        
        # Skip unrealistically long edges
        if distance > 100000:  # >100 km
            continue
        
        # Calculate population factor
        u_pop = population_by_id.get(u, 0)
        v_pop = population_by_id.get(v, 0)
        total_pop = u_pop + v_pop
        
        # Higher population means higher priority (lower weight)
        if total_pop > 0:
            # Normalize population (assuming max population is around 1 million)
            norm_pop = min(1.0, total_pop / 1000000)
            pop_factor = 1 - norm_pop  # Invert so higher population gives lower weight
        else:
            pop_factor = 1.0
        
        # Calculate critical facility factor
        if u in critical_facilities or v in critical_facilities:
            # At least one node is a critical facility
            facility_factor = 0.5  # Lower weight for critical facilities
        else:
            facility_factor = 1.0
        
        # Calculate modified weight
        # Lower weight = higher priority in MST
        modified_weight = distance * (alpha * pop_factor + beta * facility_factor)
        
        # Add edge with modified weight
        edges.append((u, v, {
            'distance': distance,
            'modified_weight': modified_weight,
            'original_data': data
        }))
    
    # Sort edges by modified weight
    edges.sort(key=lambda x: x[2]['modified_weight'])
    
    # Apply Kruskal's algorithm with Union-Find data structure
    parent = {node: node for node in G.nodes}
    rank = {node: 0 for node in G.nodes}
    
    def find(node):
        if parent[node] != node:
            parent[node] = find(parent[node])
        return parent[node]
    
    def union(node1, node2):
        root1 = find(node1)
        root2 = find(node2)
        if root1 != root2:
            if rank[root1] < rank[root2]:
                parent[root1] = root2
            elif rank[root1] > rank[root2]:
                parent[root2] = root1
            else:
                parent[root2] = root1
                rank[root1] += 1
    
    # Build MST
    mst_edges = []
    for u, v, data in edges:
        if find(u) != find(v):
            union(u, v)
            # Add edge to MST with original attributes
            mst.add_edge(u, v, **data['original_data'])
            # Also add the modified weight for analysis
            mst[u][v]['modified_weight'] = data['modified_weight']
            mst_edges.append((u, v, data['original_data']))
    
    # Ensure all nodes are included
    for node in G.nodes:
        if node not in mst:
            mst.add_node(node, **G.nodes[node])
    
    # Ensure critical facilities have adequate connectivity
    # Each critical facility should have at least 2 connections if possible
    for facility in critical_facilities:
        if facility in mst and mst.degree(facility) < 2:
            # Find closest unconnected node
            best_edge = None
            best_weight = float('inf')
            
            for u, v, data in edges:
                if (u == facility or v == facility) and find(u) != find(v):
                    if data['modified_weight'] < best_weight:
                        best_edge = (u, v, data)
                        best_weight = data['modified_weight']
            
            # Add the best edge if found
            if best_edge:
                u, v, data = best_edge
                union(u, v)
                mst.add_edge(u, v, **data['original_data'])
                mst[u][v]['modified_weight'] = data['modified_weight']
                mst_edges.append((u, v, data['original_data']))
    
    # Calculate MST metrics
    total_distance = sum(data['distance'] for _, _, data in mst.edges(data=True))
    
    # Calculate population coverage
    covered_population = 0
    for node in mst.nodes():
        if node in population_by_id:
            covered_population += population_by_id[node]
    
    # Calculate critical facility coverage
    covered_facilities = sum(1 for facility in critical_facilities if facility in mst)
    
    # Calculate average node degree
    avg_degree = sum(dict(mst.degree()).values()) / len(mst)
    
    # Prepare analysis results
    analysis = {
        'total_distance': total_distance,
        'total_distance_km': total_distance / 1000,
        'node_count': len(mst),
        'edge_count': mst.number_of_edges(),
        'covered_population': covered_population,
        'population_coverage_percent': covered_population / sum(population_by_id.values()) * 100 if population_by_id else 0,
        'critical_facilities_count': len(critical_facilities),
        'covered_facilities': covered_facilities,
        'facility_coverage_percent': covered_facilities / len(critical_facilities) * 100 if critical_facilities else 0,
        'average_node_degree': avg_degree
    }
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return mst_edges, analysis, execution_time

def draw_mst(G, mst_edges, title="Minimum Spanning Tree (MST)"):
    """
    Draw the Minimum Spanning Tree of a graph.
    
    Parameters:
    -----------
    G : networkx.Graph
        Original graph
    mst_edges : list
        List of edges in the MST
    title : str, optional
        Title for the plot
    
    Returns:
    --------
    str
        Base64 encoded image of the MST
    """
    plt.figure(figsize=(12, 10))
    
    # Get node positions
    pos = nx.get_node_attributes(G, 'pos')
    if not pos:
        pos = nx.spring_layout(G)
    
    # Create MST graph
    mst = nx.Graph()
    mst.add_nodes_from(G.nodes(data=True))
    for u, v, data in mst_edges:
        mst.add_edge(u, v, **data)
    
    # Draw nodes with green color and labels
    node_colors = ['#00FF00' for _ in G.nodes()]  # Green nodes
    nx.draw_networkx_nodes(G, pos, node_size=300, node_color=node_colors, alpha=0.8)
    
    # Draw node labels
    labels = {node: node for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=10, font_color='black')
    
    # Draw MST edges in green
    nx.draw_networkx_edges(mst, pos, alpha=0.8, edge_color='green', width=2)
    
    # Add facility labels
    facility_labels = {}
    for node in G.nodes():
        if 'type' in G.nodes[node] and G.nodes[node]['type'] in ['hospital', 'government', 'school', 'police', 'fire']:
            facility_labels[node] = f"{node} ({G.nodes[node]['type']})"
    
    # Draw facility labels
    if facility_labels:
        nx.draw_networkx_labels(G, pos, labels=facility_labels, font_size=8, font_color='red')
    
    plt.title(title)
    plt.axis('off')
    
    # Save figure to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    buf.seek(0)
    
    # Encode the image to base64
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return img_str

def budget_constrained_mst(G, budget, existing_roads_df, potential_roads_df):
    """
    Compute a budget-constrained Minimum Spanning Tree for transportation network planning.
    
    Parameters:
    -----------
    G : networkx.Graph
        Graph representing the transportation network
    budget : float
        Available budget in Million EGP
    existing_roads_df : pandas DataFrame
        DataFrame containing information about existing roads
    potential_roads_df : pandas DataFrame
        DataFrame containing information about potential new roads
    
    Returns:
    --------
    list
        List of edges in the MST
    float
        Total cost of the MST
    float
        Execution time in seconds
    """
    start_time = time.time()
    
    # Create a copy of the graph to work with
    H = G.copy()
    
    # Extract existing roads (cost = 0)
    existing_edges = []
    for _, row in existing_roads_df.iterrows():
        from_id = str(row["FromID"]).strip()
        to_id = str(row["ToID"]).strip()
        existing_edges.append((from_id, to_id))
    
    # Extract potential roads with costs
    potential_edges = []
    for _, row in potential_roads_df.iterrows():
        from_id = str(row["FromID"]).strip()
        to_id = str(row["ToID"]).strip()
        cost = float(row["Construction Cost(Million EGP)"])
        potential_edges.append((from_id, to_id, cost))
    
    # Sort potential edges by cost
    potential_edges.sort(key=lambda x: x[2])
    
    # Start with existing roads (they have no cost)
    mst_edges = []
    for u, v in existing_edges:
        if u in H and v in H:
            # Find the edge with minimum distance if there are multiple edges
            min_distance = float('inf')
            best_key = None
            for key, data in G[u][v].items():
                if data.get('road_type') == 'existing' and data.get('distance', float('inf')) < min_distance:
                    min_distance = data.get('distance')
                    best_key = key
            
            if best_key is not None:
                mst_edges.append((u, v, G[u][v][best_key]))
    
    # Create a graph with existing roads
    mst = nx.Graph()
    for u, v, data in mst_edges:
        mst.add_edge(u, v)
    
    # Add nodes that are not connected by existing roads
    for node in G.nodes:
        if node not in mst:
            mst.add_node(node)
    
    # Calculate remaining budget
    remaining_budget = budget
    
    # Add potential roads within budget constraints
    for u, v, cost in potential_edges:
        if u in H and v in H and not nx.has_path(mst, u, v) and cost <= remaining_budget:
            # Find the edge with minimum cost if there are multiple edges
            min_cost = float('inf')
            best_key = None
            for key, data in G[u][v].items():
                if data.get('road_type') == 'potential' and data.get('cost', float('inf')) < min_cost:
                    min_cost = data.get('cost')
                    best_key = key
            
            if best_key is not None:
                mst.add_edge(u, v)
                mst_edges.append((u, v, G[u][v][best_key]))
                remaining_budget -= cost
    
    # Calculate total cost
    total_cost = budget - remaining_budget
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return mst_edges, total_cost, execution_time

def connectivity_based_mst(G, budget, existing_roads_df, potential_roads_df, important_facilities_df):
    """
    Compute a connectivity-based Minimum Spanning Tree that prioritizes connecting important facilities.
    
    Parameters:
    -----------
    G : networkx.Graph
        Graph representing the transportation network
    budget : float
        Available budget in Million EGP
    existing_roads_df : pandas DataFrame
        DataFrame containing information about existing roads
    potential_roads_df : pandas DataFrame
        DataFrame containing information about potential new roads
    important_facilities_df : pandas DataFrame
        DataFrame containing information about important facilities
    
    Returns:
    --------
    list
        List of edges in the MST
    float
        Total cost of the MST
    float
        Execution time in seconds
    """
    start_time = time.time()
    
    # Create a copy of the graph to work with
    H = G.copy()
    
    # Extract existing roads (cost = 0)
    existing_edges = []
    for _, row in existing_roads_df.iterrows():
        from_id = str(row["FromID"]).strip()
        to_id = str(row["ToID"]).strip()
        existing_edges.append((from_id, to_id))
    
    # Extract potential roads with costs
    potential_edges = []
    for _, row in potential_roads_df.iterrows():
        from_id = str(row["FromID"]).strip()
        to_id = str(row["ToID"]).strip()
        cost = float(row["Construction Cost(Million EGP)"])
        potential_edges.append((from_id, to_id, cost))
    
    # Extract important facilities
    important_nodes = []
    for _, row in important_facilities_df.iterrows():
        node_id = str(row["ID"]).strip()
        facility_type = str(row["Type"]).strip().lower()
        if facility_type in ['hospital', 'school', 'government', 'police', 'fire']:
            important_nodes.append(node_id)
    
    # Start with existing roads (they have no cost)
    mst_edges = []
    for u, v in existing_edges:
        if u in H and v in H:
            # Find the edge with minimum distance if there are multiple edges
            min_distance = float('inf')
            best_key = None
            for key, data in G[u][v].items():
                if data.get('road_type') == 'existing' and data.get('distance', float('inf')) < min_distance:
                    min_distance = data.get('distance')
                    best_key = key
            
            if best_key is not None:
                mst_edges.append((u, v, G[u][v][best_key]))
    
    # Create a graph with existing roads
    mst = nx.Graph()
    for u, v, data in mst_edges:
        mst.add_edge(u, v)
    
    # Add nodes that are not connected by existing roads
    for node in G.nodes:
        if node not in mst:
            mst.add_node(node)
    
    # Calculate remaining budget
    remaining_budget = budget
    
    # Prioritize connecting important facilities
    # Sort potential edges by whether they connect important facilities
    def edge_priority(edge):
        u, v, cost = edge
        # Higher priority (lower value) if both nodes are important
        if u in important_nodes and v in important_nodes:
            return (0, cost)
        # Medium priority if one node is important
        elif u in important_nodes or v in important_nodes:
            return (1, cost)
        # Lower priority if neither node is important
        else:
            return (2, cost)
    
    potential_edges.sort(key=edge_priority)
    
    # Add potential roads within budget constraints
    for u, v, cost in potential_edges:
        if u in H and v in H and not nx.has_path(mst, u, v) and cost <= remaining_budget:
            # Find the edge with minimum cost if there are multiple edges
            min_cost = float('inf')
            best_key = None
            for key, data in G[u][v].items():
                if data.get('road_type') == 'potential' and data.get('cost', float('inf')) < min_cost:
                    min_cost = data.get('cost')
                    best_key = key
            
            if best_key is not None:
                mst.add_edge(u, v)
                mst_edges.append((u, v, G[u][v][best_key]))
                remaining_budget -= cost
    
    # Calculate total cost
    total_cost = budget - remaining_budget
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return mst_edges, total_cost, execution_time
