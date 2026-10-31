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

                  {/* Clean drop shadow for 3D map pins */}
                  <filter id="cleanPinDropShadow" x="-30%" y="-30%" width="160%" height="160%">
                    <feDropShadow dx="0" dy="3" stdDeviation="3.5" floodColor="#0f172a" floodOpacity="0.22" />
                  </filter>

                  {/* Vibrant gradients for modern 3D map pins */}
                  <linearGradient id="pinGradRed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#ef4444" />
                    <stop offset="100%" stopColor="#b91c1c" />
                  </linearGradient>

                  <linearGradient id="pinGradBlue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2563eb" />
                    <stop offset="100%" stopColor="#1d4ed8" />
                  </linearGradient>

                  <linearGradient id="pinGradPurple" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#9333ea" />
                    <stop offset="100%" stopColor="#6b21a8" />
                  </linearGradient>
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

                {/* TECHNICIAN LIVE GPS NAVIGATION PUCK (Paseo de la Reforma / Rio Lerma) */}
                <g transform="translate(440, 400)" className="tech-beacon-marker" filter="url(#cleanPinDropShadow)">
                  <ellipse cx="0" cy="1" rx="8" ry="2.8" fill="#0f172a" opacity="0.25" />
                  <circle cx="0" cy="0" r="18" fill="#38bdf8" className="tech-gps-halo" />
                  <circle cx="0" cy="0" r="11" fill="#0284c7" stroke="#ffffff" strokeWidth="2.5" />
                  <polygon points="0,-6 4,4 0,1.5 -4,4" fill="#ffffff" />

                  <g transform="translate(0, -20)">
                    <polygon points="0,0 -4.5,-6 4.5,-6" fill="#ffffff" />
                    <polygon points="0,0 -4.5,-6 4.5,-6" fill="none" stroke="#0284c7" strokeWidth="1" />
                    <rect
                      x="-74"
                      y="-28"
                      width="148"
                      height="22"
                      rx="6"
                      fill="#ffffff"
                      stroke="#0284c7"
                      strokeWidth="1.2"
                    />
                    <polygon points="0,-1 -4,-6 4,-6" fill="#ffffff" />
                    <circle cx="-62" cy="-17" r="3.5" fill="#10b981" />
                    <text x="-52" y="-13.5" fill="#0369a1" fontSize="9.5" fontWeight="800" textAnchor="start">
                      Technician Live (Karthik)
                    </text>
                  </g>
                </g>

                {/* DESTINATION PINS */}
                {/* Stop 1 */}
                <g
                  transform="translate(560, 200)"
                  className={`tech-map-pin ${activeStop.id === 'stop-1' ? 'active-pin' : ''}`}
                  onClick={() => setActiveStopId('stop-1')}
                  filter="url(#cleanPinDropShadow)"
                >
                  <ellipse cx="0" cy="1" rx="9" ry="3.2" fill="#0f172a" opacity="0.35" />
                  <path
                    d="M 0 0 C -3.5 -5.5, -15 -18, -15 -29 A 15 15 0 1 1 15 -29 C 15 -18, 3.5 -5.5, 0 0 Z"
                    fill="url(#pinGradRed)"
                    stroke="#ffffff"
                    strokeWidth="2.2"
                    strokeLinejoin="round"
                  />
                  <circle cx="0" cy="-29" r="9" fill="#ffffff" />
                  <text x="0" y="-25.2" fill="#b91c1c" fontSize="11" fontWeight="900" textAnchor="middle">
                    1
                  </text>

                  <g transform="translate(0, -45)">
                    <polygon points="0,0 -5.5,-8 5.5,-8" fill="#ffffff" />
                    <polygon points="0,0 -5.5,-8 5.5,-8" fill="none" stroke="#e2e8f0" strokeWidth="1" />
                    <rect
                      x="-88"
                      y="-32"
                      width="176"
                      height="26"
                      rx="6"
                      fill="#ffffff"
                      stroke="#e2e8f0"
                      strokeWidth="1.2"
                    />
                    <polygon points="0,-1 -5,-8 5,-8" fill="#ffffff" />
                    <circle cx="-75" cy="-19" r="3.5" fill="#ef4444" />
                    <text x="-64" y="-15.5" fill="#0f172a" fontSize="10.5" fontWeight="800" textAnchor="start">
                      Arun Kumar
                    </text>
                    <text x="2" y="-15.5" fill="#dc2626" fontSize="9.5" fontWeight="700" textAnchor="start">
                      · E-04 Red LED
                    </text>
                  </g>
                </g>

                {/* Stop 2 */}
                <g
                  transform="translate(710, 240)"
                  className={`tech-map-pin ${activeStop.id === 'stop-2' ? 'active-pin' : ''}`}
                  onClick={() => setActiveStopId('stop-2')}
                  filter="url(#cleanPinDropShadow)"
                >
                  <ellipse cx="0" cy="1" rx="8" ry="2.8" fill="#0f172a" opacity="0.3" />
                  <path
                    d="M 0 0 C -3 -5, -14 -17, -14 -27 A 14 14 0 1 1 14 -27 C 14 -17, 3 -5, 0 0 Z"
                    fill="url(#pinGradBlue)"
                    stroke="#ffffff"
                    strokeWidth="2"
                    strokeLinejoin="round"
                  />
                  <circle cx="0" cy="-27" r="8.5" fill="#ffffff" />
                  <text x="0" y="-23.5" fill="#1d4ed8" fontSize="10.5" fontWeight="900" textAnchor="middle">
                    2
                  </text>

                  <g transform="translate(0, -42)">
                    <polygon points="0,0 -5,-7 5,-7" fill="#ffffff" />
                    <polygon points="0,0 -5,-7 5,-7" fill="none" stroke="#e2e8f0" strokeWidth="1" />
                    <rect
                      x="-75"
                      y="-30"
                      width="150"
                      height="24"
                      rx="6"
                      fill="#ffffff"
                      stroke="#e2e8f0"
                      strokeWidth="1.2"
                    />
                    <polygon points="0,-1 -4.5,-7 4.5,-7" fill="#ffffff" />
                    <circle cx="-63" cy="-18" r="3.5" fill="#2563eb" />
                    <text x="-53" y="-14.5" fill="#0f172a" fontSize="10" fontWeight="800" textAnchor="start">
                      Villa 12
                    </text>
                    <text x="-12" y="-14.5" fill="#64748b" fontSize="9" fontWeight="600" textAnchor="start">
                      · 3kW Survey
                    </text>
                  </g>
                </g>

                {/* Stop 3 */}
                <g
                  transform="translate(870, 310)"
                  className={`tech-map-pin ${activeStop.id === 'stop-3' ? 'active-pin' : ''}`}
                  onClick={() => setActiveStopId('stop-3')}
                  filter="url(#cleanPinDropShadow)"
                >
                  <ellipse cx="0" cy="1" rx="8" ry="2.8" fill="#0f172a" opacity="0.3" />
                  <path
                    d="M 0 0 C -3 -5, -14 -17, -14 -27 A 14 14 0 1 1 14 -27 C 14 -17, 3 -5, 0 0 Z"
                    fill="url(#pinGradPurple)"
                    stroke="#ffffff"
                    strokeWidth="2"
                    strokeLinejoin="round"
                  />
                  <circle cx="0" cy="-27" r="8.5" fill="#ffffff" />
                  <text x="0" y="-23.5" fill="#7e22ce" fontSize="10.5" fontWeight="900" textAnchor="middle">
                    3
                  </text>

                  <g transform="translate(0, -42)">
                    <polygon points="0,0 -5,-7 5,-7" fill="#ffffff" />
                    <polygon points="0,0 -5,-7 5,-7" fill="none" stroke="#e2e8f0" strokeWidth="1" />
                    <rect
                      x="-80"
                      y="-30"
                      width="160"
                      height="24"
                      rx="6"
                      fill="#ffffff"
                      stroke="#e2e8f0"
                      strokeWidth="1.2"
                    />
                    <polygon points="0,-1 -4.5,-7 4.5,-7" fill="#ffffff" />
                    <circle cx="-68" cy="-18" r="3.5" fill="#9333ea" />
                    <text x="-58" y="-14.5" fill="#0f172a" fontSize="10" fontWeight="800" textAnchor="start">
                      TechSpark
                    </text>
                    <text x="-3" y="-14.5" fill="#64748b" fontSize="9" fontWeight="600" textAnchor="start">
                      · 10kW Wiring
                    </text>
                  </g>
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
