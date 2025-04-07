import requests

# Base URL
base_url = "http://localhost:8000"

# # Get all vehicles
# response = requests.get(f"{base_url}/api/vehicles")
# print(response.json())

# # Filter by vehicle type
# response = requests.get(f"{base_url}/api/vehicles", params={"vehicle_type": "ambulance"})
# print(response.json())

# # Filter by status
# response = requests.get(f"{base_url}/api/vehicles", params={"status": "idle"})
# print(response.json())

# Get Vehicle by ID
# vehicle_id = "AMB-1"
# response = requests.get(f"{base_url}/api/vehicles/{vehicle_id}")
# print(response.json())

# Get Number of Vehicle Types and Total
# response = requests.get(f"{base_url}/api/vehicle-types")
# print(response.json())


# # Get Police Patrols
# response = requests.get(f"{base_url}/api/police-patrols")
# print(response.json())

# Dispatch Vehicle
payload = {
    "vehicle_type": "ambulance",  # Replace with a valid idle vehicle ID
    "destination_lat": 45.386328,    # Example: latitude of Ottawa
    "destination_lon": -75.974498,  # Example: longitude of Ottawa
}
response = requests.post(f"{base_url}/api/dispatch-vehicle", json=payload)
print(response.json())


# # Reset Simulation
# response = requests.post(f"{base_url}/api/reset-simulation")
# print(response.json())


# # Get Vehicle History
# vehicle_id = "AMB-1"  # Replace with a valid vehicle ID
# response = requests.get(f"{base_url}/api/history/{vehicle_id}", params={"hours": 2})
# print(response.json())