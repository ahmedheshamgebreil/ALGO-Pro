import heapq
import time
import math

def dijkstra_step_by_step(G, traffic_data, start, end, time_period, transport_mode='car'):
    """
    Dijkstra's algorithm that yields visited nodes for animation.
    """
    distances = {node: float('inf') for node in G.nodes}
    distances[start] = 0
    pq = [(0, start)]
    visited_order = []
    
    while pq:
        current_distance, current_node = heapq.heappop(pq)
        
        if current_node in [v for v, _ in visited_order]:
            continue
            
        visited_order.append((current_node, current_distance))
        
        if current_node == end:
            break
            
        for neighbor, edges in G[current_node].items():
            for key, data in edges.items():
                base_distance = data.get('distance', 1000)
                # Simplified weight calculation for race
                weight = base_distance / 1000 # Just distance for simplicity in race
                
                distance = distances[current_node] + weight
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    heapq.heappush(pq, (distance, neighbor))
                    
    return visited_order

def heuristic(G, node, goal):
    if 'pos' in G.nodes[node] and 'pos' in G.nodes[goal]:
        x1, y1 = G.nodes[node]['pos']
        x2, y2 = G.nodes[goal]['pos']
        return math.sqrt((x2-x1)**2 + (y2-y1)**2) * 100 # Scaled Euclidean
    return 0

def a_star_step_by_step(G, traffic_data, start, end, time_period, transport_mode='car'):
    """
    A* algorithm that yields visited nodes for animation.
    """
    g_scores = {node: float('inf') for node in G.nodes}
    g_scores[start] = 0
    pq = [(heuristic(G, start, end), 0, start)]
    visited_order = []
    
    while pq:
        f_score, current_g, current_node = heapq.heappop(pq)
        
        if current_node in [v for v, _ in visited_order]:
            continue
            
        visited_order.append((current_node, current_g))
        
        if current_node == end:
            break
            
        for neighbor, edges in G[current_node].items():
            for key, data in edges.items():
                base_distance = data.get('distance', 1000)
                weight = base_distance / 1000
                
                tentative_g = g_scores[current_node] + weight
                if tentative_g < g_scores[neighbor]:
                    g_scores[neighbor] = tentative_g
                    f = tentative_g + heuristic(G, neighbor, end)
                    heapq.heappush(pq, (f, tentative_g, neighbor))
                    
    return visited_order
