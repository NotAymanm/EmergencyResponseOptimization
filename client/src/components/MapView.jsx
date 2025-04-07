import {
  GeoJSON,
  Marker,
  Tooltip,
  TileLayer,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import {
  AmbulanceIcon,
  FireStationIcon,
  FireTruckIcon,
  GreenPoint,
  RedPoint,
  HospitalIcon,
  PoliceCarIcon,
  PoliceStationIcon,
} from "../assets/icons";

const filterMapping = {
  medical: {
    facilities: ["Ambulance Facility"],
    vehicles: ["ambulance"],
  },
  fire: {
    facilities: ["Fire Station"],
    vehicles: ["fire_truck"],
  },
  police: {
    facilities: ["Police Station"],
    vehicles: ["police_car"],
  },
};

const MapView = ({
  vehicles,
  facilities,
  roadNetwork,
  onVehicleSelect,
  tempMarker,
  setTempMarker,
  dispatchedMarkers,
  routes,
  activeFilters,
}) => {
  const vehicleIcon = (type) => {
    const icons = {
      ambulance: AmbulanceIcon,
      fire_truck: FireTruckIcon,
      police_car: PoliceCarIcon,
    };
    return L.divIcon({
      html: icons[type],
      iconSize: [32, 32],
      className: "vehicle-marker",
    });
  };

  const stationIcon = (type) => {
    switch (type) {
      case "Fire Station":
        type = "fireStation";
        break;
      case "Police Station":
        type = "policeStation";
        break;
      case "Ambulance Facility":
        type = "hospital";
        break;
      default:
        break;
    }

    const icons = {
      hospital: HospitalIcon,
      fireStation: FireStationIcon,
      policeStation: PoliceStationIcon,
    };
    return L.divIcon({
      html: icons[type],
      iconSize: [32, 32],
      className: "station-marker",
    });
  };

  // Handle map events
  useMapEvents({
    dblclick: (e) => {
      const { lat, lng } = e.latlng;
      setTempMarker({ lat, lng });
    },
  });

  const tempIcon = L.divIcon({
    html: RedPoint,
    iconSize: [32, 32],
    className: "temp-marker",
  });

  const dispatchedIcon = L.divIcon({
    html: GreenPoint,
    iconSize: [32, 32],
    className: "dispatched-marker",
  });

  return (
    <>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Render temporary marker */}
      {tempMarker && (
        <Marker position={[tempMarker.lat, tempMarker.lng]} icon={tempIcon}>
          <Tooltip>Next Dispatch Point?</Tooltip>
        </Marker>
      )}

      {/* Render dispatched markers */}
      {dispatchedMarkers.map((marker, index) => (
        <Marker
          key={index}
          position={[marker.lat, marker.lng]}
          icon={dispatchedIcon}
        >
          <Tooltip>Vehicle {marker.vehicleId} dispatched here</Tooltip>
        </Marker>
      ))}

      {vehicles.vehicles
        ?.filter((vehicle) => {
          return Object.entries(activeFilters).some(([key, isActive]) => {
            if (key === "roads") return false;
            return (
              isActive &&
              filterMapping[key].vehicles.includes(vehicle.vehicle_type)
            );
          });
        })
        .map((vehicle) => {
          const routeData = routes[vehicle.vehicle_id];
          const eta = routeData?.features?.[0]?.properties?.estimated_time;
          const minutes = eta ? Math.floor(eta) : 0;
          const seconds = eta ? Math.round((eta % 1) * 60) : 0;
          return (
            <Marker
              key={vehicle.vehicle_id}
              position={[vehicle.location.lat, vehicle.location.lng]}
              icon={vehicleIcon(vehicle.vehicle_type)}
            >
              <Tooltip>
                {vehicle.vehicle_id}
                <br />
                Status: {vehicle.status}
                {eta !== undefined && (
                  <>
                    <br />
                    ETA: {minutes}m {seconds}s
                  </>
                )}
              </Tooltip>
            </Marker>
          );
        })}

      {facilities.features
        ?.filter((feature) => {
          return Object.entries(activeFilters).some(([key, isActive]) => {
            if (key === "roads") return false;
            return (
              isActive &&
              filterMapping[key].facilities.includes(feature.properties.type)
            );
          });
        })
        .map((feature, index) => {
          return (
            <Marker
              key={feature.properties.id || feature.properties.address + index}
              position={[
                feature.geometry.coordinates[1],
                feature.geometry.coordinates[0],
              ]}
              icon={stationIcon(feature.properties.type)}
            >
              <Tooltip>{feature.properties.type}</Tooltip>
            </Marker>
          );
        })}

      {Object.entries(routes).map(([vehicleId, routeData]) => {
        if (!routeData?.features?.[0]) return null;

        return (
          <GeoJSON
            key={vehicleId}
            data={routeData}
            style={{ color: "#FF6B6B", weight: 4 }}
          />
        );
      })}

      {activeFilters.roads && roadNetwork && roadNetwork.features && (
        <GeoJSON
          key="road-network"
          data={roadNetwork}
          style={{
            color: "#4a4a4a",
            weight: 2,
            opacity: 0.7,
            lineJoin: "round",
          }}
        />
      )}
    </>
  );
};

export default MapView;
