import geopandas as gpd
import networkx as nx
import numpy as np
from shapely.geometry import Point, LineString
import os
from traffic import fetch_traffic_data, compute_delay_factor, compute_midpoint

def load_and_process_data(facilities_path, roads_path, junctions_path):
    """
    Load and process Ottawa's road network and facility data.
    
    Args:
        facilities_path: Path to protective facilities shapefile
        roads_path: Path to road network shapefile
        junctions_path: Path to road junctions shapefile
        
    Returns:
        facilities_gdf: GeoDataFrame of facilities
        road_network_graph: NetworkX graph of road network
        junctions_gdf: GeoDataFrame of road junctions
    """
    print("Loading facilities data...")
    facilities_gdf = gpd.read_file(facilities_path)
    # Keep only relevant columns
    facilities_gdf = facilities_gdf[['BUILDING_T', 'FACILITY_G', 'BUILDING_D', 'FULLNAME', 'geometry']]
    # Rename columns for clarity
    facilities_gdf = facilities_gdf.rename(columns={
        'BUILDING_T': 'type',
        'FACILITY_G': 'group',
        'BUILDING_D': 'description',
        'FULLNAME': 'address'
    })
    
    print("Loading road network data...")
    roads_gdf = gpd.read_file(roads_path)
    # Keep only relevant columns for road network
    roads_gdf = roads_gdf[['ROADCLASS', 'SPEED', 'NBRLANES', 'TRAFFICDIR', 'geometry']]
    # Rename columns for clarity
    roads_gdf = roads_gdf.rename(columns={
        'ROADCLASS': 'road_class',
        'SPEED': 'speed_limit',
        'NBRLANES': 'num_lanes',
        'TRAFFICDIR': 'traffic_direction'
    })
    
    print("Loading junctions data...")
    junctions_gdf = gpd.read_file(junctions_path)
    
    # Create unique node ID from existing columns
    if 'NID' in junctions_gdf.columns:
        # Use NID as the unique node identifier
        junctions_gdf['node_id'] = junctions_gdf['NID']
    elif 'OBJECTID' in junctions_gdf.columns:
        # Fallback to OBJECTID if NID doesn't exist
        junctions_gdf['node_id'] = 'junction_' + junctions_gdf['OBJECTID'].astype(str)
    else:
        # Generate unique IDs from geometry
        junctions_gdf['node_id'] = junctions_gdf.apply(
            lambda row: f"{row.geometry.x:.6f}_{row.geometry.y:.6f}", 
            axis=1
        )
    
    # Keep only relevant columns
    junctions_gdf = junctions_gdf[['node_id', 'JUNCTYPE', 'geometry']]
    # Rename columns for clarity
    junctions_gdf = junctions_gdf.rename(columns={
        'JUNCTYPE': 'junction_type'
    })
    
    print(f"Facilities CRS: {facilities_gdf.crs}")
    print(f"Roads CRS: {roads_gdf.crs}")
    print(f"Junctions CRS: {junctions_gdf.crs}")
    
    
    print("Converting road network to graph...")
    # Reproject all data to UTM (Ottawa is in UTM zone)
    utm_crs = "EPSG:32618"  # UTM zone for Ottawa
    facilities_gdf = facilities_gdf.to_crs(utm_crs)
    roads_gdf = roads_gdf.to_crs(utm_crs)
    junctions_gdf = junctions_gdf.to_crs(utm_crs)
    
    # Convert road network to NetworkX graph
    road_network_graph = create_road_network_graph(roads_gdf, junctions_gdf)
    
    return facilities_gdf, road_network_graph, junctions_gdf, roads_gdf

def create_road_network_graph(roads_gdf, junctions_gdf):
    """Build a graph where edges follow exact road geometries with improved efficiency."""
    G = nx.DiGraph()
    
    # 1. Pre-process junctions and add them to the graph
    print("Adding junctions to graph...")
    junction_points = {}  # Store junction geometries for fast lookup
    for _, junction in junctions_gdf.iterrows():
        node_id = f"J_{junction['node_id']}"
        x, y = junction.geometry.x, junction.geometry.y
        G.add_node(node_id, x=x, y=y, type="junction")
        # Store using rounded coordinates as key for fuzzy matching
        junction_points[(round(x, 2), round(y, 2))] = node_id
    
    # 2. Create a spatial index for junctions once
    print("Creating spatial index for junctions...")
    junction_coords = np.array([(j.geometry.x, j.geometry.y) for _, j in junctions_gdf.iterrows()])
    
    # Use scikit-learn's KDTree for faster spatial queries
    from sklearn.neighbors import KDTree
    junction_tree = KDTree(junction_coords)
    junction_tolerance = 1.0  # meters
    
    # 3. Process roads in batches to improve memory efficiency
    print("Processing roads...")
    node_counter = 0
    batch_size = 1000
    
    for batch_start in range(0, len(roads_gdf), batch_size):
        batch_end = min(batch_start + batch_size, len(roads_gdf))
        batch = roads_gdf.iloc[batch_start:batch_end]
        
        for road_id, road in batch.iterrows():
            if not isinstance(road.geometry, LineString):
                continue
            
            coords = list(road.geometry.coords)
            if len(coords) < 2:
                continue
            
            # 4. Process start and end points more carefully
            road_nodes = []
            
            for i, (x, y) in enumerate(coords):
                # Key decision points (start, end) or significant turns should be nodes
                is_endpoint = (i == 0 or i == len(coords) - 1)
                
                # Try to match with existing junction using KDTree
                rounded_key = (round(x, 2), round(y, 2))
                
                # First check exact matches in our dictionary
                if rounded_key in junction_points:
                    node_id = junction_points[rounded_key]
                else:
                    # Use KDTree for nearest neighbor search
                    distances, indices = junction_tree.query([[x, y]], k=1)
                    if distances[0][0] <= junction_tolerance:
                        # Use existing junction
                        junction_idx = indices[0][0]
                        junction = junctions_gdf.iloc[junction_idx]
                        node_id = f"J_{junction['node_id']}"
                    else:
                        # Only create new nodes for endpoints or significant geometry points
                        if is_endpoint or i % max(1, len(coords) // 10) == 0:  # Sample ~10% of points
                            node_id = f"R_{node_counter}"
                            node_counter += 1
                            G.add_node(node_id, x=x, y=y, type="road_vertex")
                            junction_points[rounded_key] = node_id
                        else:
                            # Skip adding intermediate points as nodes
                            continue
                
                road_nodes.append((node_id, (x, y)))
            
            # 5. Create edges between nodes with accurate geometry
            if len(road_nodes) < 2:
                continue
                
            for i in range(len(road_nodes) - 1):
                start_id, start_coords = road_nodes[i]
                end_id, end_coords = road_nodes[i + 1]
                
                # Skip self-loops
                if start_id == end_id:
                    continue
                
                # Calculate segment length
                dx = end_coords[0] - start_coords[0]
                dy = end_coords[1] - start_coords[1]
                segment_length = (dx**2 + dy**2)**0.5
                
                # Get the correct geometry between these points
                if i == 0 and i + 1 == len(road_nodes) - 1:
                    # The entire linestring between first and last node
                    segment_geom = road.geometry
                else:
                    # Find the sub-linestring between these nodes
                    segment_geom = LineString([start_coords, end_coords])
                
                # Calculate realistic travel time based on speed
                speed_kph = road['speed_limit'] if road['speed_limit'] and road['speed_limit'] > 0 else 40.0
                travel_time = (segment_length / 1000) / (speed_kph / 60)  # minutes
                
                
                # # Compute the midpoint of the segment using the WKT geometry
                # mid_lat, mid_lon = compute_midpoint(segment_geom.wkt)
                # # Fetch traffic data at this midpoint
                # traffic_data = fetch_traffic_data(mid_lat, mid_lon)
                # if traffic_data:
                #     delay_factor = compute_delay_factor(traffic_data, speed_kph)
                #     travel_time *= delay_factor  # Update travel time using the delay factor
                
                # Add edge with road metadata
                G.add_edge(start_id, end_id,
                          road_id=road_id,
                          length=segment_length,
                          speed=speed_kph,
                          travel_time=travel_time,
                          geometry=segment_geom.wkt)
                
                # Add reverse edge for bidirectional roads
                if road['traffic_direction'] == 'Both directions':
                    G.add_edge(end_id, start_id, **G[start_id][end_id])
    
    # 6. Check graph connectivity and report
    print(f"Created graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    
    if not nx.is_strongly_connected(G):
        print("Warning: The graph is not strongly connected.")
        largest_cc = max(nx.strongly_connected_components(G), key=len)
        print(f"Largest strongly connected component has {len(largest_cc)} nodes ({len(largest_cc)/G.number_of_nodes():.1%} of graph)")
    
    return G

def save_processed_data(facilities_gdf, road_network_graph, junctions_gdf, roads_gdf, output_dir="processed_data"):
    """
    Save processed data for later use.
    
    Args:
        facilities_gdf: GeoDataFrame of facilities
        road_network_graph: NetworkX graph of road network
        junctions_gdf: GeoDataFrame of road junctions
        roads_gdf: GeoDataFrame of roads
        output_dir: Directory to save processed data
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Save GeoDataFrames to GeoJSON
    junctions_gdf['node_id'] = junctions_gdf['node_id'].astype(str)
    junctions_gdf.to_file(os.path.join(output_dir, "junctions.geojson"), driver="GeoJSON")
    facilities_gdf.to_file(os.path.join(output_dir, "facilities.geojson"), driver="GeoJSON")
    roads_gdf.to_file(os.path.join(output_dir, "roads.geojson"), driver="GeoJSON")
    
    # Save graph as GraphML
    nx.write_graphml(road_network_graph, os.path.join(output_dir, "road_network.graphml"))
    
    print(f"Processed data saved to {output_dir}/")

if __name__ == "__main__":
    # Paths to data files
    FACILITIES_PATH = "data/Protective_facilities.shp"
    ROADS_PATH = "data/Road_Network_Ottawa.shp"
    JUNCTIONS_PATH = "data/Road_Junctions_Ottawa.shp"
    
    # Load and process data
    facilities_gdf, road_network_graph, junctions_gdf, roads_gdf = load_and_process_data(
        FACILITIES_PATH, ROADS_PATH, JUNCTIONS_PATH
    )
    
    # Print summary statistics
    print("\nSummary Statistics:")
    print(f"Number of facilities: {len(facilities_gdf)}")
    print(f"Number of road segments: {len(roads_gdf)}")
    print(f"Number of junctions: {len(junctions_gdf)}")
    print(f"Road network graph: {road_network_graph.number_of_nodes()} nodes, {road_network_graph.number_of_edges()} edges")
    
    # Save processed data
    save_processed_data(facilities_gdf, road_network_graph, junctions_gdf, roads_gdf)