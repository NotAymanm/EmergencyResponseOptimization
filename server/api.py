from fastapi import FastAPI, HTTPException, Depends
from starlette.middleware.cors import CORSMiddleware
import geopandas as gpd
import networkx as nx
import json
import os
from shapely.geometry import LineString, Point
from shapely import wkt
from typing import Optional
from pydantic import BaseModel
from pyproj import Transformer

from vehicle_simulation import VehicleSimulator, create_vehicle_simulator
from vehicle_controller import VehicleController

app = FastAPI(title="Ottawa Emergency Services API")

class DispatchRequest(BaseModel):
    vehicle_type: str
    destination_lon: float
    destination_lat: float

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
PROCESSED_DATA_DIR = "processed_data"
vehicle_simulator = None
vehicle_controller = None

transformer_to_wgs84 = Transformer.from_crs("EPSG:32618", "EPSG:4326", always_xy=True)
transformer_to_proj = Transformer.from_crs("EPSG:4326", "EPSG:32618", always_xy=True)

def convert_location_to_wgs84(location):
    """Convert a location from projected CRS to WGS84."""
    lon, lat = transformer_to_wgs84.transform(location['x'], location['y'])
    return {"lat": lat, "lng": lon}

# Dependency for getting the simulator
def get_simulator():
    global vehicle_simulator
    if vehicle_simulator is None:
        # Initialize the simulator
        road_network_path = os.path.join(PROCESSED_DATA_DIR, "road_network.graphml")
        facilities_path = os.path.join(PROCESSED_DATA_DIR, "facilities.geojson")
        vehicle_simulator = create_vehicle_simulator(road_network_path, facilities_path)
        vehicle_simulator.start_simulation()
    return vehicle_simulator

# Dependency for getting the controller
def get_controller():
    global vehicle_controller
    return vehicle_controller

@app.on_event("startup")
async def startup_event():
    # Check if processed data exists
    if not os.path.exists(PROCESSED_DATA_DIR):
        raise Exception(f"Processed data directory '{PROCESSED_DATA_DIR}' not found. Run the data preprocessing script first.")
    
    # Check if all required files exist
    required_files = ["facilities.geojson", "junctions.geojson", "roads.geojson", "road_network.graphml"]
    for file in required_files:
        if not os.path.exists(os.path.join(PROCESSED_DATA_DIR, file)):
            raise Exception(f"Required file '{file}' not found in processed data directory.")

    # Initialize the vehicle simulator
    global vehicle_simulator
    road_network_path = os.path.join(PROCESSED_DATA_DIR, "road_network.graphml")
    facilities_path = os.path.join(PROCESSED_DATA_DIR, "facilities.geojson")
    vehicle_simulator = create_vehicle_simulator(road_network_path, facilities_path)
    vehicle_simulator.start_simulation()
    
    global vehicle_controller
    vehicle_controller = VehicleController(vehicle_simulator)
    vehicle_controller.start_monitoring(interval=60)

@app.on_event("shutdown")
async def shutdown_event():
    # Stop the vehicle simulator
    global vehicle_simulator
    if vehicle_simulator:
        vehicle_simulator.stop_simulation()
    if vehicle_controller:
        vehicle_controller.stop_monitoring()

# Helper functions
def load_facilities():
    """Load the processed facilities data"""
    return gpd.read_file(os.path.join(PROCESSED_DATA_DIR, "facilities.geojson"))

def load_road_network():
    """Load the processed road network graph"""
    return nx.read_graphml(os.path.join(PROCESSED_DATA_DIR, "road_network.graphml"))

def load_roads():
    """Load the processed roads data"""
    return gpd.read_file(os.path.join(PROCESSED_DATA_DIR, "roads.geojson"))

def load_junctions():
    """Load the processed junctions data"""
    return gpd.read_file(os.path.join(PROCESSED_DATA_DIR, "junctions.geojson"))

def geodataframe_to_geojson(gdf):
    """Convert a GeoDataFrame to GeoJSON"""
    # Convert to GeoJSON
    geojson = json.loads(gdf.to_json())
    return geojson

# API endpoints
@app.get("/")
async def root():
    return {"message": "Ottawa Emergency Services API."}

@app.get("/api/facilities")
async def get_facilities():
    """
    Returns locations of all emergency facilities (fire stations, ambulance facilities, and police stations).
    """
    try:
        facilities_gdf = load_facilities()
        if facilities_gdf.crs != "EPSG:4326":
            facilities_gdf = facilities_gdf.to_crs("EPSG:4326")
        return geodataframe_to_geojson(facilities_gdf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading facilities data: {str(e)}")

@app.get("/api/road-network")
async def get_road_network():
    """
    Return road network graph edges as GeoJSON FeatureCollection
    """
    try:
        graph = load_road_network()
        features = []
        
        for u, v, data in graph.edges(data=True):
            if 'geometry' in data:
                try:
                    # Parse WKT geometry and convert coordinates
                    line = wkt.loads(data['geometry'])
                    transformed_coords = []
                    
                    # Convert each coordinate to WGS84
                    for x, y in line.coords:
                        lon, lat = transformer_to_wgs84.transform(x, y)
                        transformed_coords.append([lon, lat])
                    
                    # Create GeoJSON feature
                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": transformed_coords
                        },
                        "properties": {
                            "road_id": data.get('road_id', ''),
                            "length": data.get('length', 0),
                            "speed": data.get('speed', 40),
                            "travel_time": data.get('travel_time', 0)
                        }
                    }
                    features.append(feature)
                    
                except Exception as e:
                    print(f"Error processing edge {u}-{v}: {str(e)}")

        return {
            "type": "FeatureCollection",
            "features": features
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading road network: {str(e)}")

# New Vehicle API endpoints
@app.get("/api/vehicles")
async def get_all_vehicles(
    simulator: VehicleSimulator = Depends(get_simulator),
    vehicle_type: Optional[str] = None,
    facility_id: Optional[int] = None,
    status: Optional[str] = None
):
    """
    Returns all vehicles, optionally filtered by type, facility, or status.
    
    Parameters:
    - vehicle_type: Filter by vehicle type (fire_truck, ambulance, police_car)
    - facility_id: Filter by assigned facility ID
    - status: Filter by status (idle, responding, returning, patrolling)
    """
    try:
        # Get vehicles from simulator
        vehicles = simulator.vehicles
        
        # Apply filters
        if vehicle_type:
            vehicles = [v for v in vehicles if v.vehicle_type == vehicle_type]
        
        if facility_id:
            vehicles = [v for v in vehicles if v.facility_id == facility_id]
        
        if status:
            vehicles = [v for v in vehicles if v.status == status]
        
        # Convert vehicle locations to WGS84
        vehicle_states = []
        for vehicle in vehicles:
            state = vehicle.get_state()
            state['location'] = convert_location_to_wgs84(state['location'])
            vehicle_states.append(state)
        
        return {"vehicles": vehicle_states}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting vehicles: {str(e)}")

@app.get("/api/vehicles/{vehicle_id}")
async def get_vehicle_by_id(
    vehicle_id: str,
    simulator: VehicleSimulator = Depends(get_simulator)
):
    """
    Returns information about a specific vehicle.
    
    Parameters:
    - vehicle_id: ID of the vehicle
    """
    try:
        vehicle = simulator.get_vehicle_by_id(vehicle_id)
        if not vehicle:
            raise HTTPException(status_code=404, detail=f"Vehicle with ID '{vehicle_id}' not found")
        
        state = vehicle.get_state()
        state['location'] = convert_location_to_wgs84(state['location'])
        
        return state
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting vehicle: {str(e)}")

@app.post("/api/dispatch-vehicle")
async def dispatch_vehicle(
    request: DispatchRequest,
    simulator: VehicleSimulator = Depends(get_simulator),
    controller: VehicleController = Depends(get_controller)
):
    """Dispatch a vehicle to specific coordinates"""
    try:
         # Transform destination to projected CRS
        x, y = transformer_to_proj.transform(request.destination_lon, request.destination_lat)
        dest_point_proj = Point(x, y)
        
        # Get available vehicles of the specified type
        available_vehicles = simulator.get_available_vehicles(vehicle_type=request.vehicle_type)
        if not available_vehicles:
            raise HTTPException(
                status_code=404,
                detail=f"No available {request.vehicle_type} vehicles"
            )
        
        # Find closest vehicle using Euclidean distance
        closest_vehicle = min(
            available_vehicles,
            key=lambda v: (
                (v.current_location[0] - x)**2 + 
                (v.current_location[1] - y)**2
            )**0.5
        )

        # Find nearest nodes for routing
        origin_node = simulator.find_nearest_node(Point(closest_vehicle.current_location))
        nearest_node = simulator.find_nearest_node(dest_point_proj)
        
        # Calculate route
        try:
            route = nx.shortest_path(
                simulator.graph, 
                source=origin_node,
                target=nearest_node,
                weight="travel_time"
            )
        except nx.NetworkXNoPath:
            raise HTTPException(status_code=400, detail="No path available")
        
       # Dispatch the closest vehicle
        controller.dispatch_vehicle(
            closest_vehicle.vehicle_id, 
            (x, y), 
            route
        )
        
        return {
            "message": f"Closest {request.vehicle_type} ({closest_vehicle.vehicle_id}) dispatched",
            "vehicle_id": closest_vehicle.vehicle_id,
            "route_length": len(route),
            "estimated_time": sum(
                simulator.graph.edges[route[i], route[i+1]]['travel_time']
                for i in range(len(route)-1)
            )
        }
    
    except HTTPException:
        raise  # Re-raise HTTPException to avoid catching it in the general except block
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vehicles/{vehicle_id}/route")
async def get_vehicle_route(
    vehicle_id: str,
    simulator: VehicleSimulator = Depends(get_simulator)
):
    """Returns the vehicle's current route as GeoJSON LineString"""
    try:
        # Get the vehicle from the simulator
        vehicle = simulator.get_vehicle_by_id(vehicle_id)
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        
        # Get the route nodes from the vehicle
        route_nodes = getattr(vehicle, 'route_nodes', [])
        if not route_nodes:
            return {"type": "FeatureCollection", "features": []}
        
        # Extract coordinates from the graph
        route_points = []
        total_travel_time = 0.0
        for node_id in route_nodes:
            if node_id in simulator.graph:
                x = simulator.graph.nodes[node_id]['x']
                y = simulator.graph.nodes[node_id]['y']
                # Transform UTM coordinates to WGS84 (longitude, latitude)
                lon, lat = transformer_to_wgs84.transform(x, y)
                route_points.append([lon, lat])
            else:
                print(f"Warning: Node {node_id} not found in graph")
        
        # Ensure there are enough points to form a LineString
        if len(route_points) < 2:
            return {"type": "FeatureCollection", "features": []}
        
        # Calculate total travel time by summing edge travel times
        for i in range(len(route_nodes) - 1):
            u = route_nodes[i]
            v = route_nodes[i+1]
            edge_data = simulator.graph.edges.get((u, v), {})
            total_travel_time += edge_data.get('travel_time', 0.0)
        
        # Create a LineString from the route points
        route_line = LineString(route_points)
        
        # Construct the GeoJSON feature
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": route_line.coords[:]
            },
            "properties": {
                "vehicle_id": vehicle_id,
                "status": vehicle.status,
                "estimated_time": total_travel_time
            }
        }
        
        return {"type": "FeatureCollection", "features": [feature]}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Route error for {vehicle_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/reset-simulation")
async def reset_simulation(
    simulator: VehicleSimulator = Depends(get_simulator)
):
    """
    Reset the vehicle simulation, returning all vehicles to their home facilities.
    """
    try:
        # Stop current simulation
        simulator.stop_simulation()
        
        # Reinitialize vehicles
        simulator.vehicles = []
        simulator.initialize_vehicles()
        
        # Restart simulation
        simulator.start_simulation()
        
        return {"message": "Simulation reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting simulation: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=8000)