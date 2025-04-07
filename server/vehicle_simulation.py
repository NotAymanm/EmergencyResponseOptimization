import json
import os
import random
import time
import networkx as nx
import geopandas as gpd
from shapely.geometry import Point
import threading
from datetime import datetime
from typing import List, Tuple

class EmergencyVehicle:
    def __init__(self, vehicle_id, vehicle_type, facility_id, facility_name, facility_location):
        """
        Base class for all emergency vehicles.
        
        Args:
            vehicle_id: Unique identifier for the vehicle
            vehicle_type: Type of vehicle (fire_truck, ambulance, police_car)
            facility_id: ID of the home facility
            facility_name: Name of the home facility
            facility_location: (x, y) coordinates of the home facility
        """
        self.vehicle_id = vehicle_id
        self.vehicle_type = vehicle_type
        self.facility_id = facility_id
        self.facility_name = facility_name
        self.facility_location = facility_location
        
        # Current state and location
        self.status = "idle"  # idle, responding, returning, handling, patrolling
        self.current_location = facility_location  # Start at home facility
        self.destination = None
        self.route_nodes = []  # Store node IDs for the current route
        self.route_geometry = []  # Store (lon, lat) coordinates for visualization
        self.route_index = 0
        self.last_updated = datetime.now()
        
        # Vehicle characteristics (can be customized per type)
        self.max_speed = 0  # Will be set by subclasses
        self.current_speed = 0
    
    def get_state(self):
        """Return the current state of the vehicle as a dictionary."""
        return {
            "vehicle_id": self.vehicle_id,
            "vehicle_type": self.vehicle_type,
            "facility_id": self.facility_id,
            "facility_name": self.facility_name,
            "status": self.status,
            "location": {
                "x": self.current_location[0],
                "y": self.current_location[1]
            },
            "speed": self.current_speed,
            "last_updated": self.last_updated.isoformat(),
            "route_nodes": self.route_nodes
        }
    
    def update_location(self, new_location):
        """Update the vehicle's location."""
        self.current_location = new_location
        self.last_updated = datetime.now()
    
    def start_response(self, destination: Tuple[float, float], route_nodes: List[str], graph: nx.Graph):
        """Start responding to an emergency call."""
        self.status = "responding"
        self.destination = destination
        self.route_nodes = route_nodes
        self.route_index = 0
        self.current_speed = self.max_speed
        self._update_route_geometry(graph)
    
    def return_to_facility(self, route_nodes: List[str], graph: nx.Graph):
        """Return to home facility after completing a call."""
        self.status = "returning"
        self.destination = self.facility_location
        self.route_nodes = route_nodes
        self.route_index = 0
        self.current_speed = self.max_speed * 0.7  # Return at reduced speed
        self._update_route_geometry(graph)
    
    def _update_route_geometry(self, graph: nx.Graph):
        """Convert node IDs to coordinates for visualization"""
        self.route_geometry = []
        for node in self.route_nodes:
            data = graph.nodes[node]
            self.route_geometry.append((data['x'], data['y']))
    
    def update_movement(self, graph: nx.Graph, simulated_time_step, current_simulated_time):
        """Move along the node-based route"""
        if self.status not in ["responding", "returning"] or not self.route_nodes:
            return

        if self.route_index >= len(self.route_geometry):
            self.arrive_at_destination()
            return

        # Get current target position
        target_pos = self.route_geometry[self.route_index]
        
        # Calculate movement
        max_distance = (self.current_speed * 1000 / 3600) * simulated_time_step
        dx = target_pos[0] - self.current_location[0]
        dy = target_pos[1] - self.current_location[1]
        distance = (dx**2 + dy**2)**0.5

        if distance <= max_distance:
            self.current_location = target_pos
            self.route_index += 1
        else:
            ratio = max_distance / distance
            self.current_location = (
                self.current_location[0] + dx * ratio,
                self.current_location[1] + dy * ratio
            )

        self.last_updated = datetime.now()

        # Check if reached final node
        if self.route_index >= len(self.route_geometry):
            self.arrive_at_destination(current_simulated_time)
        
    def arrive_at_destination(self, current_simulated_time):
        if self.status == "responding":
            self.status = "handling"
            self.handling_start_time = current_simulated_time
            self.handling_duration = 600 # 10 minutes in seconds
            self.current_speed = 0
            # Clear route data
            self.route_nodes = []
            self.route_geometry = []
        elif self.status == "returning":
            self.arrive_at_facility()
    
    def arrive_at_facility(self):
        """Vehicle has returned to its home facility."""
        self.status = "idle"
        self.current_location = self.facility_location
        self.destination = None
        self.route_nodes = []
        self.route_geometry = []
        self.current_speed = 0


class FireTruck(EmergencyVehicle):
    def __init__(self, vehicle_id, facility_id, facility_name, facility_location):
        super().__init__(vehicle_id, "fire_truck", facility_id, facility_name, facility_location)
        self.max_speed = 80  # km/h


class Ambulance(EmergencyVehicle):
    def __init__(self, vehicle_id, facility_id, facility_name, facility_location):
        super().__init__(vehicle_id, "ambulance", facility_id, facility_name, facility_location)
        self.max_speed = 90  # km/h


class PoliceCar(EmergencyVehicle):
    def __init__(self, vehicle_id, facility_id, facility_name, facility_location):
        super().__init__(vehicle_id, "police_car", facility_id, facility_name, facility_location)
        self.max_speed = 120  # km/h
        
        # Patrol-specific attributes
        self.patrol_nodes = []
        self.patrol_geometry = []
        self.patrol_index = 0
        self.patrol_speed = 40  # km/h during patrol
    
    def start_patrol(self, patrol_nodes: List[str], graph: nx.Graph):
        """Start patrolling around the assigned area."""
        if self.status == "idle":
            self.status = "patrolling"
            self.patrol_nodes = patrol_nodes
            self._update_patrol_geometry(graph)
            # self.patrol_index = 0
            self.current_speed = self.patrol_speed
            
    def _update_patrol_geometry(self, graph: nx.Graph):
        self.patrol_geometry = []
        for node in self.patrol_nodes:
            data = graph.nodes[node]
            self.patrol_geometry.append((data['x'], data['y']))
    
    def update_patrol(self, graph: nx.Graph, simulated_time_step):
        """Update the patrol position along the patrol route."""
        if self.status == "patrolling" and self.patrol_geometry:
            # Calculate distance moved at current speed
            max_distance = (self.current_speed * 1000 / 3600) * simulated_time_step
            
            # Move towards next patrol point
            target_pos = self.patrol_geometry[self.patrol_index]
            dx = target_pos[0] - self.current_location[0]
            dy = target_pos[1] - self.current_location[1]
            distance = (dx**2 + dy**2)**0.5
            
            if distance <= max_distance:
                self.current_location = target_pos
                self.patrol_index = (self.patrol_index + 1) % len(self.patrol_geometry)
            else:
                ratio = max_distance / distance
                new_x = self.current_location[0] + dx * ratio
                new_y = self.current_location[1] + dy * ratio
                self.current_location = (new_x, new_y)
            
            self.last_updated = datetime.now()
    
    def end_patrol(self):
        """End the patrol and return to idle state at current location."""
        self.status = "idle"
        self.patrol_nodes = []
        self.patrol_geometry = []
        self.current_speed = 0


class VehicleSimulator:
    def __init__(self, road_network_graph, facilities_data, db_path="vehicles.json"):
        """
        Simulator for emergency vehicles.
        
        Args:
            road_network_graph: NetworkX graph of the road network
            facilities_data: GeoDataFrame of emergency facilities
            db_path: Path to the JSON file for storing vehicle states
        """
        self.graph = road_network_graph
        self.facilities = facilities_data
        self.db_path = db_path
        self.vehicles = []
        self.simulation_running = False
        self.simulation_thread = None
        self.simulated_time = 0  # Simulated time in seconds
        self.real_time_step = 1  # Default real-world update interval in seconds
        self.simulation_speed = 100  # Default speed 1(1x real time)
        
        # Initialize the database file if it doesn't exist
        if not os.path.exists(db_path):
            with open(db_path, 'w') as f:
                    json.dump([], f)
    
    def initialize_vehicles(self):
        """Initialize vehicles based on facility type and assign them to facilities."""
        vehicle_id = 1
        
        for _, facility in self.facilities.iterrows():
            facility_id = int(facility.name)  # Use the index as facility ID
            facility_name = facility['description'] if 'description' in facility else facility['type']
            facility_point = facility.geometry
            facility_location = (facility_point.x, facility_point.y)
            facility_type = facility['type']
            
            # Assign vehicles based on facility type
            if "Fire" in facility_type:
                # Assign 1 fire trucks per fire station
                for i in range(1):
                    truck = FireTruck(f"FT-{vehicle_id}", facility_id, facility_name, facility_location)
                    self.vehicles.append(truck)
                    vehicle_id += 1
            
            elif "Ambulance" in facility_type or "Paramedic" in facility_type:
                # Assign 4 ambulances per ambulance facility
                for i in range(4):
                    ambulance = Ambulance(f"AMB-{vehicle_id}", facility_id, facility_name, facility_location)
                    self.vehicles.append(ambulance)
                    vehicle_id += 1
            
            elif "Police" in facility_type:
                # Assign 5 police cars per police station
                for i in range(5):
                    police = PoliceCar(f"POL-{vehicle_id}", facility_id, facility_name, facility_location)
                    self.vehicles.append(police)
                    vehicle_id += 1
                    
                    # Generate and assign initial patrol routes
                    patrol_nodes = self.generate_patrol_route(facility_location)
                    police.start_patrol(patrol_nodes, self.graph)
        
        # Save initial vehicle states to database
        self.save_vehicle_states()
        
        print(f"Initialized {len(self.vehicles)} vehicles across {len(self.facilities)} facilities")
    
    def generate_patrol_route(self, start_location: Tuple[float, float], max_nodes=10) -> List[str]:
        nodes = []
        current_node = self.find_nearest_node(Point(start_location))
        for _ in range(max_nodes):
            neighbors = list(self.graph.neighbors(current_node))
            if not neighbors:
                break
            current_node = random.choice(neighbors)
            nodes.append(current_node)
        return nodes
    
    def save_vehicle_states(self):
        """Save current states of all vehicles to the database."""
        states = [vehicle.get_state() for vehicle in self.vehicles]
        with open(self.db_path, 'w') as f:
            json.dump(states, f, indent=2)
    
    def load_vehicle_states(self):
        """Load vehicle states from the database."""
        try:
            with open(self.db_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def start_simulation(self):
        """Start the vehicle simulation in a separate thread."""
        if self.simulation_running:
            print("Simulation already running")
            return
        
        self.simulation_running = True
        self.simulation_thread = threading.Thread(target=self.simulation_loop)
        self.simulation_thread.daemon = True
        self.simulation_thread.start()
        print("Vehicle simulation started")
    
    def stop_simulation(self):
        """Stop the vehicle simulation."""
        self.simulation_running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=5)
        print("Vehicle simulation stopped")
    
    def simulation_loop(self):
        """Main simulation loop running in a separate thread."""
        last_save_time = time.time()
        
        while self.simulation_running:
            current_time = time.time()
            
            # Calculate simulated time step based on simulation_speed
            simulated_time_step = self.real_time_step * self.simulation_speed
            
            # Update all vehicle movements
            for vehicle in self.vehicles:
                if vehicle.status in ["responding", "returning"]:
                    vehicle.update_movement(self.graph, simulated_time_step, self.simulated_time)
                elif isinstance(vehicle, PoliceCar) and vehicle.status == "patrolling":
                    vehicle.update_patrol(self.graph, simulated_time_step)
                elif vehicle.status == "handling":
                    if self.simulated_time >= vehicle.handling_start_time + vehicle.handling_duration:
                        current_node = self.find_nearest_node(Point(vehicle.current_location))
                        facility_node = self.find_nearest_node(Point(vehicle.facility_location))
                        route_back = nx.shortest_path(self.graph, source=current_node, target=facility_node, weight="travel_time")
                        vehicle.return_to_facility(route_back, self.graph)
                elif vehicle.status == "idle" and isinstance(vehicle, PoliceCar):
                    patrol_nodes = self.generate_patrol_route(vehicle.facility_location)
                    vehicle.start_patrol(patrol_nodes, self.graph)
            
            # Save vehicle states every 5 seconds (real time)
            if current_time - last_save_time >= 5:
                self.save_vehicle_states()
                last_save_time = current_time
            
            # Advance simulated time
            self.simulated_time += simulated_time_step
            
            # Sleep for the specified time step
            time.sleep(self.real_time_step)
    
    def update_police_patrols(self):
        """Update positions of all patrolling police cars."""
        for vehicle in self.vehicles:
            if isinstance(vehicle, PoliceCar) and vehicle.status == "patrolling":
                vehicle.update_patrol()
    
    def get_vehicle_by_id(self, vehicle_id):
        """Get a vehicle by its ID."""
        for vehicle in self.vehicles:
            if vehicle.vehicle_id == vehicle_id:
                return vehicle
        return None
    
    def get_vehicles_by_type(self, vehicle_type):
        """Get all vehicles of a specific type."""
        return [v for v in self.vehicles if v.vehicle_type == vehicle_type]
    
    def get_vehicles_by_facility(self, facility_id):
        """Get all vehicles assigned to a specific facility."""
        return [v for v in self.vehicles if v.facility_id == facility_id]
    
    def get_available_vehicles(self, vehicle_type=None, facility_id=None):
        """Get all available (idle) vehicles, optionally filtered by type or facility."""
        vehicles = self.vehicles
        
        if vehicle_type:
            vehicles = [v for v in vehicles if v.vehicle_type == vehicle_type]
        
        if facility_id:
            vehicles = [v for v in vehicles if v.facility_id == facility_id]
        
        return [v for v in vehicles if v.status not in ["responding", "handling"]]
    
    def find_nearest_node(self, point):
        """Find nearest road network node to a Shapely Point"""
        min_distance = float('inf')
        nearest_node = None
        
        for node, data in self.graph.nodes(data=True):
            node_point = Point(data['x'], data['y'])
            distance = point.distance(node_point)
            
            if distance < min_distance:
                min_distance = distance
                nearest_node = node
                
        return nearest_node


def create_vehicle_simulator(road_network_graph_path, facilities_geojson_path):
    """
    Create and initialize a vehicle simulator using data from files.
    
    Args:
        road_network_graph_path: Path to the GraphML file with the road network
        facilities_geojson_path: Path to the GeoJSON file with facilities data
        
    Returns:
        Initialized VehicleSimulator object
    """
    # Load the road network graph
    road_network = nx.read_graphml(road_network_graph_path)
    
    # Load facilities data
    facilities = gpd.read_file(facilities_geojson_path)
    
    # Create and initialize the simulator
    simulator = VehicleSimulator(road_network, facilities)
    simulator.initialize_vehicles()
    
    return simulator


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python vehicle_simulation.py <road_network_path> <facilities_path>")
        sys.exit(1)
    
    road_network_path = sys.argv[1]
    facilities_path = sys.argv[2]
    
    simulator = create_vehicle_simulator(road_network_path, facilities_path)
    simulator.start_simulation()
    
    try:
        # Run for 1 minute
        print("Simulation running. Press Ctrl+C to stop.")
        time.sleep(60)
    except KeyboardInterrupt:
        print("Stopping simulation...")
    finally:
        simulator.stop_simulation()
