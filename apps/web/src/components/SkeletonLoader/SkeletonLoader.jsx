import React from 'react';
import './SkeletonLoader.css';

export function SkeletonBox({ width, height, borderRadius = '8px', className = '', style = {} }) {
  return (
    <div
      className={`skeleton-shimmer-box ${className}`}
      style={{
        width: width || '100%',
        height: height || '16px',
        borderRadius,
        ...style,
      }}
    />
  );
}

export function SkeletonCircle({ size = 40, className = '' }) {
  return (
    <div
      className={`skeleton-shimmer-box skeleton-circle ${className}`}
      style={{ width: `${size}px`, height: `${size}px`, borderRadius: '50%' }}
    />
  );
}

export function DashboardSkeleton({ role = 'customer' }) {
  return (
    <div className="skeleton-dashboard-wrapper" aria-busy="true" aria-label="Loading dashboard preview">
      {/* 1. Hero Row: Greeting, Weather, and 3 Feature Cards */}
      <div className="skeleton-hero-row">
        {/* Left: Greeting Text Shimmer */}
        <div className="skeleton-greeting-col">
          <SkeletonBox width="65%" height="32px" borderRadius="10px" />
          <SkeletonBox width="85%" height="24px" borderRadius="8px" style={{ marginTop: '8px' }} />
          <SkeletonBox width="95%" height="14px" borderRadius="6px" style={{ marginTop: '14px' }} />
          <SkeletonBox width="75%" height="14px" borderRadius="6px" style={{ marginTop: '6px' }} />
        </div>

        {/* Center: Weather Card Shimmer */}
        <div className="skeleton-weather-card">
          <div className="weather-skeleton-top">
            <SkeletonBox width="60px" height="38px" borderRadius="8px" />
            <SkeletonCircle size={44} />
          </div>
          <div className="weather-skeleton-bottom">
            <SkeletonBox width="80px" height="12px" borderRadius="4px" />
            <SkeletonBox width="50px" height="12px" borderRadius="4px" />
          </div>
        </div>

        {/* Right: 3 Feature KPI Cards */}
        <div className="skeleton-kpi-grid">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton-kpi-card">
              <SkeletonCircle size={32} />
              <div style={{ width: '100%' }}>
                <SkeletonBox width="70%" height="14px" borderRadius="4px" />
                <SkeletonBox width="90%" height="18px" borderRadius="6px" style={{ marginTop: '8px' }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 2. Middle Row: Bento Cards (Charts & Data) */}
      <div className="skeleton-bento-grid">
        {/* Bento Card 1: Chart / Trajectory Card */}
        <div className="skeleton-bento-card large">
          <div className="skeleton-card-header">
            <div>
              <SkeletonBox width="160px" height="16px" borderRadius="6px" />
              <SkeletonBox width="220px" height="11px" borderRadius="4px" style={{ marginTop: '6px' }} />
            </div>
            <SkeletonBox width="70px" height="24px" borderRadius="999px" />
          </div>

          {/* Chart Shimmer Area */}
          <div className="skeleton-chart-area">
            <div className="skeleton-chart-bars">
              {[45, 65, 80, 55, 90, 75, 85, 95, 70, 88, 92, 100].map((h, idx) => (
                <div key={idx} className="chart-bar-col">
                  <div className="skeleton-bar-fill" style={{ height: `${h}%` }} />
                  <SkeletonBox width="20px" height="9px" borderRadius="3px" style={{ marginTop: '6px' }} />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Bento Card 2: Operations / Appointment Card */}
        <div className="skeleton-bento-card">
          <div className="skeleton-card-header">
            <div>
              <SkeletonBox width="130px" height="16px" borderRadius="6px" />
              <SkeletonBox width="180px" height="11px" borderRadius="4px" style={{ marginTop: '6px' }} />
            </div>
            <SkeletonBox width="80px" height="22px" borderRadius="999px" />
          </div>

          {/* Appointment Shimmer Box */}
          <div className="skeleton-appointment-inner">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <SkeletonCircle size={36} />
              <div style={{ flex: 1 }}>
                <SkeletonBox width="110px" height="13px" borderRadius="4px" />
                <SkeletonBox width="140px" height="10px" borderRadius="4px" style={{ marginTop: '4px' }} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
              <SkeletonBox width="48%" height="24px" borderRadius="6px" />
              <SkeletonBox width="48%" height="24px" borderRadius="6px" />
            </div>
          </div>

          {/* Security PIN Box Shimmer */}
          <div className="skeleton-pin-vault">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <SkeletonBox width="140px" height="12px" borderRadius="4px" />
              <SkeletonBox width="60px" height="20px" borderRadius="6px" />
            </div>
            <div className="skeleton-pin-boxes">
              {[1, 2, 3, 4, 5, 6].map((n) => (
                <SkeletonBox key={n} width="32px" height="38px" borderRadius="8px" />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 3. Bottom Row: Table Shimmer */}
      <div className="skeleton-bento-card table-card">
        <div className="skeleton-card-header">
          <div>
            <SkeletonBox width="180px" height="16px" borderRadius="6px" />
            <SkeletonBox width="260px" height="11px" borderRadius="4px" style={{ marginTop: '6px' }} />
          </div>
          <SkeletonBox width="140px" height="32px" borderRadius="10px" />
        </div>

        <div className="skeleton-table">
          <div className="skeleton-table-header">
            {[15, 25, 20, 15, 15].map((w, i) => (
              <SkeletonBox key={i} width={`${w}%`} height="12px" borderRadius="4px" />
            ))}
          </div>
          {[1, 2, 3, 4].map((row) => (
            <div key={row} className="skeleton-table-row">
              <SkeletonBox width="14%" height="13px" borderRadius="4px" />
              <SkeletonBox width="24%" height="13px" borderRadius="4px" />
              <SkeletonBox width="19%" height="13px" borderRadius="4px" />
              <SkeletonBox width="13%" height="18px" borderRadius="999px" />
              <SkeletonBox width="14%" height="13px" borderRadius="4px" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

