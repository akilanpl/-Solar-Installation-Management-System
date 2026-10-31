import React from 'react';
import './LoadingState.css';

export function LoadingState({
  label = 'Loading SolarOps operations…',
  subtext = 'Synchronizing solar data stream',
}) {
  return (
    <div className="loading-state-container">
      <div className="solar-spinner">
        <div className="solar-spinner-ring" />
        <div className="solar-spinner-inner" />
        <div className="solar-spinner-core" />
      </div>
      <p className="loading-label">{label}</p>
      {subtext && <p className="loading-subtext">{subtext}</p>}
    </div>
  );
}

