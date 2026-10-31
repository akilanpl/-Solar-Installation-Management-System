import React, { useState } from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from '../../router/Router';
import { STOPS } from '../../components/TechnicianSiteMap/TechnicianSiteMap';
import {
  Navigation,
  MapPin,
  Phone,
  Clock,
  AlertTriangle,
  CheckCircle2,
  ShieldCheck,
  ArrowLeft,
  Car,
  Compass,
  Wrench,
  Radio,
  ExternalLink,
  Layers,
  ZoomIn,
  ZoomOut,
  Crosshair,
  Sun,
  Moon,
} from 'lucide-react';
import './TechnicianMapPage.css';

export function TechnicianMapPage() {
  const { user, showToast } = useAuth();
  const { navigate } = useRouter();

  const [activeStopId, setActiveStopId] = useState('stop-1');
  const [arrivedStops, setArrivedStops] = useState({});
  const [zoomLevel, setZoomLevel] = useState(1);
  const [activeLayer, setActiveLayer] = useState('street'); // 'street' | 'night' | 'traffic'

  const activeStop = STOPS.find((s) => s.id === activeStopId) || STOPS[0];
  const isArrived = !!arrivedStops[activeStop.id];

  const handleStartNavigation = (stop) => {
    const url = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(
      stop.address
    )}`;
    window.open(url, '_blank', 'noopener,noreferrer');
    if (showToast) {
      showToast({
        type: 'info',
        title: 'GPS Turn-by-Turn Opened',
        message: `Routing to ${stop.customerName} in ${stop.area} (${stop.distance}, ${stop.eta}).`,
      });
    }
  };

  const handleCheckIn = (stopId) => {
    setArrivedStops((prev) => ({ ...prev, [stopId]: true }));
    if (showToast) {
      showToast({
        type: 'success',
        title: 'Customer Site Verified',
        message: `Arrival logged for ${activeStop.customerName}. Customer OTP verified for check-in.`,
      });
    }
  };

  return (
    <AppShell requiredRole="technician">
      <div className="tech-map-page-wrapper">
        {/* Page Top Banner */}
        <div className="tech-map-page-header">
          <div className="header-left-col">
            <button
              type="button"
              className="back-to-dash-btn"
              onClick={() => navigate('/technician')}
            >
              <ArrowLeft size={16} />
              <span>Back to Dashboard</span>
            </button>
            <div className="page-title-row">
              <Navigation size={22} color="#0284c7" />
              <h1>Field Route & Live GPS Navigation</h1>
              <span className="live-dispatch-badge">
                <span className="live-dot-green" />
                <span>Live Dispatch Telemetry</span>
              </span>
            </div>
            <p className="page-subtitle">
              Turn-by-turn navigation across city corridors for on-site solar inspections, DC ground fault diagnostics, and customer problem rectification.
            </p>
          </div>

          <div className="header-right-stats">
            <div className="dispatch-stat-box">
              <span className="stat-label">TODAY'S ITINERARY</span>
              <span className="stat-value">3 Customer Sites</span>
            </div>
            <div className="dispatch-stat-box">
              <span className="stat-label">TOTAL DISTANCE</span>
              <span className="stat-value">23.4 km</span>
            </div>
            <div className="dispatch-stat-box">
              <span className="stat-label">TECHNICIAN STATUS</span>
              <span className="stat-value" style={{ color: '#34d399' }}>On-Duty · Active</span>
            </div>
          </div>
        </div>

        {/* 2-Column Dedicated Map Layout */}
        <div className="tech-map-page-body">
          {/* Left Column: Itinerary Stops & Problem Rectification Directives */}
          <div className="tech-itinerary-col">
            <h3 className="itinerary-heading">Today's Stop Schedule</h3>

            <div className="stops-itinerary-list">
              {STOPS.map((stop, index) => {
                const isSelected = stop.id === activeStopId;
                const stopDone = arrivedStops[stop.id];

                return (
                  <div
                    key={stop.id}
                    className={`itinerary-stop-card ${isSelected ? 'active' : ''} ${
                      stopDone ? 'done' : ''
                    }`}
                    onClick={() => setActiveStopId(stop.id)}
                  >
                    <div className="stop-card-top">
                      <div className="stop-badge-row">
                        <span className="stop-index-pill">
                          {stopDone ? '✓' : `Stop ${index + 1}`}
                        </span>
                        <span className={`priority-tag ${stop.priority.toLowerCase()}`}>
                          {stop.priority}
                        </span>
                        <span className="distance-pill">{stop.distance} · {stop.eta}</span>
                      </div>
                      <span className="traffic-indicator">{stop.traffic}</span>
                    </div>

                    <h4 className="stop-customer-name">{stop.customerName}</h4>
                    <div className="stop-issue-title">
                      <AlertTriangle size={13} color="#f87171" />
                      <span>{stop.issueType}</span>
                    </div>

                    <div className="stop-address-text">
                      <MapPin size={13} color="#94a3b8" className="flex-shrink-0" />
                      <span>{stop.address}</span>
                    </div>

                    <div className="stop-card-footer">
                      <span className="time-slot-tag">
                        <Clock size={11} />
                        <span>{stop.scheduledSlot}</span>
                      </span>
                      <span className="system-tag">{stop.systemSize}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Active Directive & Action Panel */}
            <div className="active-stop-action-panel">
              <div className="panel-header-row">
                <span className="directive-badge">Action Directive</span>
                <span className="order-id-badge">{activeStop.workOrderId}</span>
              </div>

              <h4 className="directive-customer">{activeStop.customerName} ({activeStop.area})</h4>
              <p className="directive-desc">
                <strong>Problem Rectification:</strong> {activeStop.problemDescription}
              </p>

              <div className="panel-action-buttons">
                <button
                  type="button"
                  className="page-nav-btn primary"
                  onClick={() => handleStartNavigation(activeStop)}
                >
                  <Navigation size={15} />
                  <span>Start Turn-by-Turn GPS</span>
                  <ExternalLink size={13} opacity={0.7} />
                </button>

                <a
                  href={`tel:${activeStop.phone}`}
                  className="page-nav-btn secondary"
                >
                  <Phone size={15} />
                  <span>Call Customer ({activeStop.phone})</span>
                </a>

                <button
                  type="button"
                  className={`page-nav-btn ${isArrived ? 'verified' : 'checkin'}`}
                  onClick={() => handleCheckIn(activeStop.id)}
                >
                  {isArrived ? (
                    <>
                      <CheckCircle2 size={15} color="#34d399" />
                      <span>On-Site Check-in Verified</span>
                    </>
                  ) : (
                    <>
                      <ShieldCheck size={15} />
                      <span>Arrived at Customer Site (Verify OTP)</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Right Column: Full-Height Map Viewport */}
          <div className="tech-fullmap-col">
            {/* Map Canvas Toolbars */}
            <div className="map-canvas-controls-bar">
              <div className="map-view-toggles">
                <button
                  type="button"
                  className={`layer-toggle-btn ${activeLayer === 'street' ? 'active' : ''}`}
                  onClick={() => setActiveLayer('street')}
                >
                  <Sun size={13} />
                  <span>Street Map</span>
                </button>
                <button
                  type="button"
                  className={`layer-toggle-btn ${activeLayer === 'night' ? 'active' : ''}`}
                  onClick={() => setActiveLayer('night')}
                >
                  <Moon size={13} />
                  <span>Night Vision</span>
                </button>
                <button
                  type="button"
                  className={`layer-toggle-btn ${activeLayer === 'traffic' ? 'active' : ''}`}
                  onClick={() => setActiveLayer('traffic')}
                >
                  <Radio size={13} />
                  <span>Traffic Flow</span>
                </button>
              </div>

              <div className="map-zoom-buttons">
                <button
                  type="button"
                  className="zoom-btn"
                  onClick={() => setZoomLevel((z) => Math.min(z + 0.15, 1.45))}
                  title="Zoom In"
                >
                  <ZoomIn size={15} />
                </button>
                <button
                  type="button"
                  className="zoom-btn"
                  onClick={() => setZoomLevel((z) => Math.max(z - 0.15, 0.85))}
                  title="Zoom Out"
                >
                  <ZoomOut size={15} />
                </button>
                <button
                  type="button"
                  className="zoom-btn"
                  onClick={() => setZoomLevel(1)}
                  title="Recenter on Technician"
                >
                  <Crosshair size={15} />
                </button>
              </div>
            </div>

            {/* Expansive Map Viewport */}
            <div className={`standalone-dark-map-viewport layer-mode-${activeLayer}`}>
              <svg
                className="standalone-vector-map-svg"
                viewBox="0 0 1024 536"
                preserveAspectRatio="xMidYMid meet"
                style={{ transform: `scale(${zoomLevel})`, transition: 'transform 0.25s ease' }}
                xmlns="http://www.w3.org/2000/svg"
              >
                <defs>
                  {/* Soft aura for continuous navigation guide line */}
                  <filter id="fullRouteAura" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="1" stdDeviation="2.5" floodColor="#1a73e8" floodOpacity="0.4" />
                  </filter>

                  {/* Clean card shadow for floating white pin labels */}
                  <filter id="fullPinShadow" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#0f172a" floodOpacity="0.18" />
                  </filter>
                </defs>

                {/* BASE MAP LAYER: Uncompressed 1024x536 Real City Map */}
                <image
                  href="/maps/dispatch-map.jpg"
                  x="0"
                  y="0"
                  width="1024"
                  height="536"
                  preserveAspectRatio="xMidYMid meet"
                  className={`fullmap-raster-base ${activeLayer === 'night' ? 'night-filter' : ''}`}
                />

                {/* Night Mode Subtle Tint Overlay */}
                {activeLayer === 'night' && (
                  <rect width="1024" height="536" fill="#0b0f19" opacity="0.25" pointerEvents="none" />
                )}

                {/* Traffic Flow Overlay */}
                {activeLayer === 'traffic' && (
                  <g pointerEvents="none">
                    {/* Green Light Traffic Corridors */}
                    <line x1="220" y1="520" x2="880" y2="195" stroke="#10b981" strokeWidth="6" opacity="0.4" strokeLinecap="round" />
                    {/* Moderate Yellow Segments */}
                    <line x1="560" y1="335" x2="560" y2="200" stroke="#f59e0b" strokeWidth="6" opacity="0.45" strokeLinecap="round" />
                  </g>
                )}

                {/* ACTIVE GPS NAVIGATION GUIDE LINES: Thin continuous lines following actual streets */}
                {activeStop.id === 'stop-1' && (
                  <g filter="url(#fullRouteAura)">
                    <path
                      d="M 440 400 L 560 335 L 560 200"
                      fill="none"
                      stroke="#93c5fd"
                      strokeWidth="6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      opacity="0.5"
                    />
                    <path
                      d="M 440 400 L 560 335 L 560 200"
                      fill="none"
                      stroke="#1d4ed8"
                      strokeWidth="2.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </g>
                )}

                {activeStop.id === 'stop-2' && (
                  <g filter="url(#fullRouteAura)">
                    <path
                      d="M 440 400 L 680 270 L 710 240"
                      fill="none"
                      stroke="#93c5fd"
                      strokeWidth="6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      opacity="0.5"
                    />
                    <path
                      d="M 440 400 L 680 270 L 710 240"
                      fill="none"
                      stroke="#1d4ed8"
                      strokeWidth="2.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </g>
                )}

                {activeStop.id === 'stop-3' && (
                  <g filter="url(#fullRouteAura)">
                    <path
                      d="M 440 400 L 740 240 L 870 240 L 870 310"
                      fill="none"
                      stroke="#c084fc"
                      strokeWidth="6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      opacity="0.45"
                    />
                    <path
                      d="M 440 400 L 740 240 L 870 240 L 870 310"
                      fill="none"
                      stroke="#7e22ce"
                      strokeWidth="2.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </g>
                )}

                {/* TECHNICIAN BEACON (Paseo de la Reforma / Rio Lerma) */}
                <g transform="translate(440, 400)" className="tech-beacon-marker" filter="url(#fullPinShadow)">
                  <circle cx="0" cy="0" r="22" fill="#0284c7" opacity="0.2" className="beacon-pulse-circle" />
                  <circle cx="0" cy="0" r="13" fill="#0284c7" opacity="0.3" />
                  <circle cx="0" cy="0" r="7.5" fill="#0284c7" stroke="#ffffff" strokeWidth="2.5" />
                  <polygon points="0,-10 3.5,-4 -3.5,-4" fill="#ffffff" />
                  <rect
                    x="-75"
                    y="-36"
                    width="150"
                    height="22"
                    rx="11"
                    fill="#ffffff"
                    stroke="#0284c7"
                    strokeWidth="1.2"
                  />
                  <text x="0" y="-21" fill="#0369a1" fontSize="10.5" fontWeight="700" textAnchor="middle">
                    Technician Live (Karthik)
                  </text>
                </g>

                {/* DESTINATION PINS */}
                {/* Stop 1 */}
                <g
                  transform="translate(560, 200)"
                  className={`dark-marker-pin ${activeStop.id === 'stop-1' ? 'active-pin' : ''}`}
                  onClick={() => setActiveStopId('stop-1')}
                  filter="url(#fullPinShadow)"
                >
                  <circle cx="0" cy="0" r="20" fill="#ef4444" opacity="0.22" className="beacon-pulse-circle" />
                  <path
                    d="M0 -26 C-9 -26 -16 -19 -16 -10 C-16 3 0 16 0 16 C0 16 16 3 16 -10 C16 -19 9 -26 0 -26 Z"
                    fill="#ea4335"
                    stroke="#ffffff"
                    strokeWidth="2"
                  />
                  <circle cx="0" cy="-10" r="4.5" fill="#ffffff" />
                  <rect
                    x="-78"
                    y="-56"
                    width="156"
                    height="24"
                    rx="12"
                    fill="#ffffff"
                    stroke="#ea4335"
                    strokeWidth="1.5"
                  />
                  <text x="0" y="-40" fill="#991b1b" fontSize="10.5" fontWeight="800" textAnchor="middle">
                    Arun Kumar · E-04 Red LED
                  </text>
                </g>

                {/* Stop 2 */}
                <g
                  transform="translate(710, 240)"
                  className={`dark-marker-pin ${activeStop.id === 'stop-2' ? 'active-pin' : ''}`}
                  onClick={() => setActiveStopId('stop-2')}
                  filter="url(#fullPinShadow)"
                >
                  <circle cx="0" cy="0" r="18" fill="#0284c7" opacity="0.22" />
                  <path
                    d="M0 -26 C-9 -26 -16 -19 -16 -10 C-16 3 0 16 0 16 C0 16 16 3 16 -10 C16 -19 9 -26 0 -26 Z"
                    fill="#1a73e8"
                    stroke="#ffffff"
                    strokeWidth="2"
                  />
                  <circle cx="0" cy="-10" r="4.5" fill="#ffffff" />
                  <rect
                    x="-72"
                    y="-56"
                    width="144"
                    height="24"
                    rx="12"
                    fill="#ffffff"
                    stroke="#1a73e8"
                    strokeWidth="1.5"
                  />
                  <text x="0" y="-40" fill="#1e40af" fontSize="10" fontWeight="700" textAnchor="middle">
                    Villa 12 · Structure Markings
                  </text>
                </g>

                {/* Stop 3 */}
                <g
                  transform="translate(870, 310)"
                  className={`dark-marker-pin ${activeStop.id === 'stop-3' ? 'active-pin' : ''}`}
                  onClick={() => setActiveStopId('stop-3')}
                  filter="url(#fullPinShadow)"
                >
                  <circle cx="0" cy="0" r="18" fill="#9333ea" opacity="0.22" />
                  <path
                    d="M0 -26 C-9 -26 -16 -19 -16 -10 C-16 3 0 16 0 16 C0 16 16 3 16 -10 C16 -19 9 -26 0 -26 Z"
                    fill="#9333ea"
                    stroke="#ffffff"
                    strokeWidth="2"
                  />
                  <circle cx="0" cy="-10" r="4.5" fill="#ffffff" />
                  <rect
                    x="-82"
                    y="-56"
                    width="164"
                    height="24"
                    rx="12"
                    fill="#ffffff"
                    stroke="#9333ea"
                    strokeWidth="1.5"
                  />
                  <text x="0" y="-40" fill="#6b21a8" fontSize="10" fontWeight="700" textAnchor="middle">
                    TechSpark · 10kW Commercial DB
                  </text>
                </g>
              </svg>

              {/* HUD Overlay */}
              <div className="standalone-hud-overlay">
                <div className="standalone-hud-chip">
                  <Compass size={14} color="#0284c7" />
                  <span>NE · Heading 042° Straight</span>
                </div>
                <div className="standalone-hud-chip next-step">
                  <Navigation size={14} color="#10b981" />
                  <span>{activeStop.nextTurn}</span>
                </div>
                <div className="standalone-hud-chip">
                  <span className="traffic-live-dot" />
                  <span>{activeStop.traffic}</span>
                </div>
                <div className="standalone-hud-chip" style={{ background: 'rgba(2, 132, 199, 0.85)', color: '#ffffff', fontWeight: 700 }}>
                  <span>42 km/h</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

export default TechnicianMapPage;
