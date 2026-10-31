import React from 'react';
import { DashboardSkeleton } from '../SkeletonLoader/SkeletonLoader';
import './LoadingState.css';

export function LoadingState({
  label = 'Loading SolarOps operations…',
  subtext = 'Synchronizing solar data stream',
  asSkeleton = true,
}) {
  if (asSkeleton) {
    return (
      <div className="skeleton-loading-container" style={{ width: '100%' }}>
        <div className="skeleton-loading-status-bar">
          <span className="skeleton-live-pulse-dot" />
          <span className="skeleton-loading-text">{label}</span>
          <span className="skeleton-fast-chip">⚡ Sub-50ms Optimized</span>
        </div>
        <DashboardSkeleton />
      </div>
    );
  }

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
