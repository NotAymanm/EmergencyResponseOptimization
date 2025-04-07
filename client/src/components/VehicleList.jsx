const VehicleList = ({ vehicles, onSelect }) => {
    return (
      <div className="vehicle-list">
        <h3>Emergency Vehicles</h3>
        <div className="list-container">
          {vehicles.vehicles?.map(vehicle => (
            <div 
              key={vehicle.vehicle_id}
              className={`vehicle-item ${vehicle.status}`}
              onClick={() => onSelect(vehicle)}
            >
              <div className="vehicle-id">{vehicle.vehicle_id}</div>
              <div className="vehicle-type">{vehicle.vehicle_type}</div>
              <div className="vehicle-status">{vehicle.status}</div>
            </div>
          ))}
        </div>
      </div>
    )
  }
  
  export default VehicleList