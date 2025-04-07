// src/components/ControlPanel.jsx
import { useState } from 'react'

const ControlPanel = ({ vehicles, onRefresh }) => {
  const [isResetting, setIsResetting] = useState(false)
  
  // Calculate vehicle counts and status distribution
  const vehicleCounts = {
    fire_truck: 0,
    ambulance: 0,
    police_car: 0,
    total: 0
  }
  
  const statusCounts = {
    idle: 0,
    responding: 0,
    returning: 0,
    patrolling: 0,
    handling: 0,
  }

  if (vehicles.vehicles) {
    vehicles.vehicles.forEach(vehicle => {
      vehicleCounts[vehicle.vehicle_type]++
      vehicleCounts.total++
      statusCounts[vehicle.status]++
    })
  }

  const handleResetSimulation = async () => {
    setIsResetting(true)
    try {
      const response = await fetch('http://localhost:8000/api/reset-simulation', {
        method: 'POST'
      })
      if (!response.ok) throw new Error('Reset failed')
      onRefresh()
    } catch (error) {
      alert(error.message)
    } finally {
      setIsResetting(false)
    }
  }

  return (
    <div className="control-panel">
      <h2>Simulation Controls</h2>
      
      <div className="button-group">
        <button onClick={onRefresh} className="refresh-btn">
          ↻ Refresh Data
        </button>
        <button 
          onClick={handleResetSimulation} 
          disabled={isResetting}
          className="reset-btn"
        >
          {isResetting ? 'Resetting...' : '⟳ Reset Simulation'}
        </button>
      </div>

      <div className="stats-section">
        <h3>Vehicle Overview</h3>
        <div className="vehicle-stats">
          <div className="stat-item fire">
            <span className="stat-label">Fire Trucks</span>
            <span className="stat-value">{vehicleCounts.fire_truck}</span>
          </div>
          <div className="stat-item ambulance">
            <span className="stat-label">Ambulances</span>
            <span className="stat-value">{vehicleCounts.ambulance}</span>
          </div>
          <div className="stat-item police">
            <span className="stat-label">Police Cars</span>
            <span className="stat-value">{vehicleCounts.police_car}</span>
          </div>
          <div className="stat-item total">
            <span className="stat-label">Total Vehicles</span>
            <span className="stat-value">{vehicleCounts.total}</span>
          </div>
        </div>
      </div>

      <div className="status-section">
        <h3>Status Distribution</h3>
        <div className="status-bars">
          {Object.entries(statusCounts).map(([status, count]) => (
            <div key={status} className="status-bar">
              <span className="status-label">{status}</span>
              <div className="bar-container">
                <div 
                  className={`bar ${status}`} 
                  style={{ width: `${(count / vehicleCounts.total) * 100}%` }}
                ></div>
                <span className="count">{count}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default ControlPanel