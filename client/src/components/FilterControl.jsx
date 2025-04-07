import React from 'react';

const FilterControl = ({ activeFilters, setActiveFilters }) => {
  const filters = [
    { key: 'medical', label: '🚑 Medical (Ambulances & Hospitals)' },
    { key: 'fire', label: '🚒 Fire (Fire Trucks & Fire Stations)' },
    { key: 'police', label: '🚓 Police (Police Cars & Stations)' },
    { key: 'roads', label: '🛣️ Roads' },
  ];

  const handleFilterChange = (filterKey) => {
    setActiveFilters(prev => ({
      ...prev,
      [filterKey]: !prev[filterKey],
    }));
  };

  return (
    <div className="filter-control">
      <h4>Filter by Category:</h4>
      {filters.map((filter) => (
        <label key={filter.key} className="filter-option">
          <input
            type="checkbox"
            checked={activeFilters[filter.key]}
            onChange={() => handleFilterChange(filter.key)}
          />
          <span className="filter-label">{filter.label}</span>
        </label>
      ))}
    </div>
  );
};

export default FilterControl;