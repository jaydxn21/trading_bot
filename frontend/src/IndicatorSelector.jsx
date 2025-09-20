// IndicatorSelector.jsx
import React, { useState } from 'react';

const IndicatorSelector = ({ onAddIndicator, onRemoveIndicator, activeIndicators = new Map() }) => {
  const [selectedIndicator, setSelectedIndicator] = useState('rsi');
  const [period, setPeriod] = useState(14);

  const indicatorOptions = [
    { value: 'rsi', label: 'RSI' },
    { value: 'macd', label: 'MACD' },
    { value: 'ema', label: 'EMA' },
    { value: 'sma', label: 'SMA' }
  ];

  const handleAddIndicator = () => {
    const settings = { period };
    onAddIndicator(selectedIndicator, selectedIndicator, settings);
    setPeriod(14);
  };

  return (
    <div style={{ 
      padding: '15px', 
      background: '#374151', 
      borderRadius: '8px',
      marginBottom: '20px'
    }}>
      <h4 style={{ color: '#f9fafb', marginBottom: '10px' }}>📊 Technical Indicators</h4>
      
      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
        <select
          value={selectedIndicator}
          onChange={(e) => setSelectedIndicator(e.target.value)}
          style={{ 
            padding: '8px 12px', 
            borderRadius: '5px', 
            background: '#4b5563', 
            color: '#d1d5db', 
            border: '1px solid #6b7280' 
          }}
        >
          {indicatorOptions.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <input
          type="number"
          placeholder="Period"
          value={period}
          onChange={(e) => setPeriod(Number(e.target.value))}
          min="2"
          max="50"
          style={{ 
            padding: '8px 12px', 
            borderRadius: '5px', 
            background: '#4b5563', 
            color: '#d1d5db', 
            border: '1px solid #6b7280',
            width: '80px'
          }}
        />

        <button
          onClick={handleAddIndicator}
          style={{ 
            padding: '8px 16px', 
            background: '#10b981', 
            color: 'white', 
            border: 'none', 
            borderRadius: '5px', 
            cursor: 'pointer' 
          }}
        >
          Add Indicator
        </button>
      </div>

      {activeIndicators.size > 0 && (
        <div style={{ marginTop: '15px' }}>
          <h5 style={{ color: '#f9fafb', marginBottom: '8px' }}>Active Indicators:</h5>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {Array.from(activeIndicators.entries()).map(([name, indicator]) => (
              <div
                key={name}
                style={{
                  padding: '6px 12px',
                  background: '#4b5563',
                  color: '#d1d5db',
                  borderRadius: '15px',
                  fontSize: '0.9em',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <span>{name} ({indicator.type})</span>
                <button
                  onClick={() => onRemoveIndicator(name)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#ef4444',
                    cursor: 'pointer',
                    fontSize: '1.2em'
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default IndicatorSelector;