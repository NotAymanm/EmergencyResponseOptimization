import requests
from shapely import wkt

API_KEY = "..."

def fetch_traffic_data(lat, lon, radius=1000):
    base_url = "https://data.traffic.hereapi.com/v7/flow"
    params = {
        "in": f"circle:{lat},{lon};r={radius}",
        "locationReferencing": "olr",  # or "shape"
        "units": "metric",
        "apiKey": API_KEY
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print("Error fetching traffic data:", response.status_code)
        return None

def compute_delay_factor(traffic_json, default_max=10.0):
    """
    Compute a delay factor from a single traffic result.
    Returns:
      float: The computed delay factor.
    """
    current_flow = traffic_json.get("currentFlow", {})
    current_speed = current_flow.get("speed", 0)
    free_flow = current_flow.get("freeFlow", 0)
    
    if current_speed > 0:
        factor = free_flow / current_speed
    else:
        factor = default_max    # Use a high default if current speed is 0
    
    # Ensure that the delay factor is not less than 1.0 (which would imply a speed faster than free flow)
    if factor < 1.0:
        factor = 1.0
        
    return factor

def compute_midpoint(wkt_geometry):
    """
    Compute the midpoint (latitude, longitude) of a road segment given as WKT.
    """
    line = wkt.loads(wkt_geometry)
    midpoint = line.interpolate(0.5, normalized=True)
    # Return as (lat, lon)
    return midpoint.y, midpoint.x