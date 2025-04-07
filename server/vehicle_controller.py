import json
import time
import threading
import os
from datetime import datetime

class VehicleController:
    """
    Monitor and control emergency vehicles.
    This class serves as an interface between the simulator and the API.
    """
    
    def __init__(self, simulator, db_path="vehicle_status.json"):
        """
        Initialize the vehicle controller.
        
        Args:
            simulator: VehicleSimulator instance
            db_path: Path to JSON file for storing vehicle status history
        """
        self.lock = threading.Lock()
        self.simulator = simulator
        self.db_path = db_path
        self.monitoring = False
        self.monitor_thread = None
        self.status_history = self._load_status_history()
        
        # Initialize history file if it doesn't exist
        if not os.path.exists(db_path):
            with open(db_path, 'w') as f:
                json.dump([], f)
    
    def _load_status_history(self):
        """Load vehicle status history from the database."""
        try:
            with open(self.db_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _save_status_history(self):
        """Save vehicle status history to the database."""
        with open(self.db_path, 'w') as f:
            json.dump(self.status_history, f, indent=2)
    
    def start_monitoring(self, interval=60):
        """
        Start monitoring vehicle status at regular intervals.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self.monitoring:
            print("Already monitoring vehicles")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            args=(interval,)
        )
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print(f"Started monitoring vehicles every {interval} seconds")
    
    def stop_monitoring(self):
        """Stop monitoring vehicle status."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("Stopped monitoring vehicles")
    
    def dispatch_vehicle(self, vehicle_id, destination, route):
        """Dispatch a vehicle to an emergency location."""
        vehicle = self.simulator.get_vehicle_by_id(vehicle_id)
        if not vehicle:
            raise ValueError(f"Vehicle {vehicle_id} not found")
        
        if vehicle.status in ["responding", "handling"]:
            raise ValueError(f"Vehicle {vehicle_id} is not available")
        
        vehicle.start_response(destination, route, self.simulator.graph)
        self._capture_status()  # Log dispatch event
    
    def _monitor_loop(self, interval):
        """
        Monitor loop that captures vehicle status at regular intervals.
        
        Args:
            interval: Monitoring interval in seconds
        """
        while self.monitoring:
            # Capture current status of all vehicles
            self._capture_status()
            
            # Sleep until next capture
            time.sleep(interval)
    
    def _capture_status(self):
        """Capture current status of all vehicles and add to history."""
        with self.lock:
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            # Get current status of all vehicles
            vehicle_states = []
            for vehicle in self.simulator.vehicles:
                state = vehicle.get_state()
                vehicle_states.append(state)
            
            # Add to history
            entry = {
                "timestamp": timestamp,
                "vehicles": vehicle_states
            }
            self.status_history.append(entry)
            
            # Keep only last 24 hours of data (1440 minutes / 1-minute intervals)
            if len(self.status_history) > 1440:
                self.status_history = self.status_history[-1440:]
                
            # Save to database
            self._save_status_history()