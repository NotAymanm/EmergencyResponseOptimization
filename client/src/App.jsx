import { useState, useEffect } from "react";
import { MapContainer, TileLayer } from "react-leaflet";
import MapView from "./components/MapView";
import DispatchForm from "./components/DispatchForm";
import ControlPanel from "./components/ControlPanel";
import FilterControl from "./components/FilterControl";
import "leaflet/dist/leaflet.css";
import "./App.css";

function App() {
  const [vehicles, setVehicles] = useState([]);
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [facilities, setFacilities] = useState([]);
  const [roadNetwork, setRoadNetwork] = useState(null);
  const [tempMarker, setTempMarker] = useState(null); // Temporary marker state
  const [dispatchedMarkers, setDispatchedMarkers] = useState([]); // Dispatched markers state
  const [routes, setRoutes] = useState({});

  const [activeFilters, setActiveFilters] = useState({
    medical: true,
    fire: true,
    police: true,
    roads: false,
  });

  useEffect(() => {
    fetchData();
    fetchStaticData();
    const interval = setInterval(fetchData, 5000);
    return () => {
      clearInterval(interval);
      setRoutes({});
    };
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      // Check all active routes
      Object.keys(routes).forEach(vehicleId => {
        fetchRoute(vehicleId); // Re-validate route status
      });
    }, 5000); // Check every 5 seconds
  
    return () => clearInterval(interval);
  }, [routes]);

  const fetchData = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/vehicles");

      const vehiclesData = await res.json();
      // Update vehicles
      setVehicles(vehiclesData);

      // Check for vehicles that are returning
      setDispatchedMarkers((prevMarkers) => {
        // Filter out markers for vehicles that are returning
        return prevMarkers.filter((marker) => {
          const vehicle = vehiclesData.vehicles.find(
            (v) => v.vehicle_id === marker.vehicleId
          );
          // Keep the marker if the vehicle is still not "returning" or doesn't exist yet
          return vehicle && vehicle.status !== "returning";
        });
      });
    } catch (error) {
      console.error("Error fetching data:", error);
    }
  };

  const fetchStaticData = async () => {
    try {
      const [facilitiesRes, /* roadsRes */] = await Promise.all([
        fetch("http://localhost:8000/api/facilities"),
        // fetch("http://localhost:8000/api/road-network"),
      ]);

      /* if (!roadsRes.ok) throw new Error("Failed to fetch road network");
      const roadData = await roadsRes.json();

      // Validate GeoJSON structure
      if (!roadData.type || !roadData.features) {
        throw new Error("Invalid GeoJSON format");
      }

      setRoadNetwork(roadData); */

      setFacilities(await facilitiesRes.json());
    } catch (error) {
      console.error("Error fetching road network:", error);
      setRoadNetwork({ type: "FeatureCollection", features: [] }); // Fallback empty
    }
  };

  // Function to reset map/simulation
  const reset = async () => {
    setRoutes({});
    setDispatchedMarkers([]);
    setTempMarker(null);
    fetchData();
  };

  // Function to fetch route for a vehicle
  const fetchRoute = async (vehicleId) => {
    console.log("Fetching route for:", vehicleId);
    try {
      const response = await fetch(
        `http://localhost:8000/api/vehicles/${vehicleId}/route`
      );

      if (!response.ok) {
        if (response.status === 404) {
          // Remove invalid vehicle from routes state
          setRoutes((prev) => {
            const newRoutes = { ...prev };
            delete newRoutes[vehicleId];
            return newRoutes;
          });
          return;
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const routeData = await response.json();

      // Auto-remove if route is empty
      if (routeData.features.length === 0) {
        setRoutes((prev) => {
          const newRoutes = { ...prev };
          delete newRoutes[vehicleId];
          return newRoutes;
        });
      } else {
        setRoutes((prev) => ({ ...prev, [vehicleId]: routeData }));
      }
    } catch (error) {
      console.error("Error fetching route:", error);
    }
  };

  return (
    <div className="app-container">
      <div className="map-container">
        <MapContainer
          center={[45.4215, -75.6972]}
          zoom={12}
          style={{ height: "100%", width: "100%" }}
          className="map"
          doubleClickZoom={false}
        >
          <MapView
            vehicles={vehicles}
            facilities={facilities}
            roadNetwork={roadNetwork}
            onVehicleSelect={setSelectedVehicle}
            tempMarker={tempMarker}
            setTempMarker={setTempMarker}
            dispatchedMarkers={dispatchedMarkers}
            routes={routes}
            activeFilters={activeFilters}
          />
        </MapContainer>
      </div>

      <div className="sidebar">
        <ControlPanel onRefresh={reset} vehicles={vehicles} />
        <FilterControl
          activeFilters={activeFilters}
          setActiveFilters={setActiveFilters}
        />
        {selectedVehicle ? (
          {
            /* <VehicleDetails
            vehicle={selectedVehicle}
            onClose={() => setSelectedVehicle(null)}
          /> */
          }
        ) : (
          <>
            <DispatchForm
              fetchData={fetchData}
              tempMarker={tempMarker}
              setDispatchedMarkers={setDispatchedMarkers}
              setTempMarker={setTempMarker}
              fetchRoute={fetchRoute}
            />
          </>
        )}
      </div>
    </div>
  );
}

export default App;
