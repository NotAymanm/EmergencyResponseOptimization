import { useState } from "react";

const DispatchForm = ({
  fetchData,
  tempMarker,
  setDispatchedMarkers,
  setTempMarker,
  fetchRoute
}) => {
  const [vehicleType, setVehicleType] = useState("");
  const [loading, setLoading] = useState(false);

    // Handle dispatch action
    const handleDispatch = async () => {
      if (!tempMarker) {
        alert("Please select a location on the map first.");
        return;
      }
      if (!vehicleType) {
        alert("Please select a vehicle type first.");
        return;
      }

      setLoading(true);
      try {
        const response = await fetch("http://localhost:8000/api/dispatch-vehicle", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            vehicle_type: vehicleType,
            destination_lon: tempMarker.lng,
            destination_lat: tempMarker.lat,
          }),
        });
  
        if (response.ok) {
          const data = await response.json();
          // Move tempMarker to dispatchedMarkers
          setDispatchedMarkers((prev) => [
            ...prev,
            { ...tempMarker, vehicleType, vehicleId: data.vehicle_id },
          ]);
          // Clear tempMarker
          setTempMarker(null);
          // Refresh data
          fetchData();

          console.log("DISPATCH LOG: ", data);
          fetchRoute(data.vehicle_id);
        } else {
          alert("Failed to dispatch vehicle.");
          throw new Error("Dispatch failed: ", await response.text());
        }
      } catch (error) {
        console.error("Error dispatching vehicle:", error);
      }
      finally {
        setLoading(false);
      }
    };

  return (
    <div className="dispatch-form">
      <h3>Emergency Dispatch</h3>

      <select 
        value={vehicleType}
        onChange={(e) => setVehicleType(e.target.value)}
        disabled={loading}
      >
        <option value="">Select Emergency Service</option>
        <option value="fire_truck">🚒 Fire Department</option>
        <option value="ambulance">🚑 Ambulance</option>
        <option value="police_car">🚓 Police</option>
      </select>

      <button 
        onClick={handleDispatch}
        disabled={loading || !vehicleType}
      >
        {loading ? 'Dispatching...' : 'Call 911'}
      </button>
    </div>
  );
};

export default DispatchForm;
