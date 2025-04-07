from shapely.geometry import LineString, Point
import geopandas as gpd
import pandas as pd

import sys
from pathlib import Path
# Add the parent directory (server) to the Python path
sys.path.append(str(Path(__file__).parent.parent))
from traffic import compute_midpoint, fetch_traffic_data, compute_delay_factor
from data_processing import create_road_network_graph

def test_compute_midpoint():
    # Create a simple line from (0, 0) to (10, 10)
    line = LineString([(0, 0), (10, 10)])
    wkt_geom = line.wkt
    mid_lat, mid_lon = compute_midpoint(wkt_geom)
    # The midpoint should be (5, 5)
    assert abs(mid_lat - 5) < 0.0001
    assert abs(mid_lon - 5) < 0.0001
    print("Midpoint test passed.")

def test_fetch_traffic_data():
    # Use coordinates from your area (e.g., Ottawa)
    data = fetch_traffic_data(45.4215, -75.6972)
    assert data is not None, "No data returned."
    print("Traffic data fetched:", data)


def test_compute_delay_factor():
    # Test case 1: When current speed equals free flow, factor should be 1.0.
    traffic_result1 = {
        "currentFlow": {
            "speed": 15.555556,
            "freeFlow": 15.555556
        }
    }
    factor1 = compute_delay_factor(traffic_result1)
    assert abs(factor1 - 1.0) < 1e-6, f"Test 1 failed: Expected 1.0, got {factor1}"
    
    # Test case 2: When current speed is lower than free flow.
    # For example, freeFlow = 14.444445, speed = 11.388889, expected factor ≈ 1.268.
    traffic_result2 = {
        "currentFlow": {
            "speed": 11.388889,
            "freeFlow": 14.444445
        }
    }
    factor2 = compute_delay_factor(traffic_result2)
    expected2 = 14.444445 / 11.388889  # ≈ 1.268
    assert abs(factor2 - expected2) < 1e-6, f"Test 2 failed: Expected {expected2}, got {factor2}"
    
    # Test case 3: When current speed is zero, function should return default_max (default is 10.0).
    traffic_result3 = {
        "currentFlow": {
            "speed": 0,
            "freeFlow": 10.0
        }
    }
    factor3 = compute_delay_factor(traffic_result3)
    expected3 = 10.0
    assert abs(factor3 - expected3) < 1e-6, f"Test 3 failed: Expected {expected3}, got {factor3}"
    
    # Test case 4: When current speed is faster than free flow, factor should not drop below 1.0.
    traffic_result4 = {
        "currentFlow": {
            "speed": 16.0,
            "freeFlow": 15.0
        }
    }
    factor4 = compute_delay_factor(traffic_result4)
    expected4 = 1.0  # because factor should be at least 1.0
    assert abs(factor4 - expected4) < 1e-6, f"Test 4 failed: Expected {expected4}, got {factor4}"
    
    print("All tests passed.")


def create_sample_data():
    # Create a sample road as a simple LineString with the correct field 'speed_limit'
    road_data = {
        'ROADCLASS': ['A'],
        'speed_limit': [40],  # Updated field name to match expected key
        'traffic_direction': ['Both directions'],
        'NBRLANES': [2],
        'geometry': [LineString([(0, 0), (10, 10)])]
    }
    roads_gdf = gpd.GeoDataFrame(road_data, crs="EPSG:4326")
    
    # Create a sample junction with a point
    junction_data = {
        'node_id': [1],
        'JUNCTYPE': ['TypeA'],
        'geometry': [Point(0, 0)]
    }
    junctions_gdf = gpd.GeoDataFrame(junction_data, crs="EPSG:4326")
    
    return roads_gdf, junctions_gdf


if __name__ == "__main__":
    test_compute_midpoint()
    # test_fetch_traffic_data()
    # test_compute_delay_factor()
    
    
    # roads_gdf, junctions_gdf = create_sample_data()
    # # Call your function
    # graph = create_road_network_graph(roads_gdf, junctions_gdf)
    
    # # Inspect an edge
    # for u, v, data in graph.edges(data=True):
    #     travel_time_minutes = data['travel_time']
    #     whole_minutes = int(travel_time_minutes)
    #     seconds = (travel_time_minutes - whole_minutes) * 60
    #     print(f"Edge from {u} to {v}:")
    #     print(f"  Speed (km/h): {data['speed']}")
    #     print(f"  Travel time: {whole_minutes} minute(s) and {seconds:.0f} second(s)")
    #     print(f"  Geometry: {data['geometry']}")