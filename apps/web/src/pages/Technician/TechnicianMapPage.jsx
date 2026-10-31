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
                preserveAspectRatio="none"
                style={{ transform: `scale(${zoomLevel})`, transition: 'transform 0.25s ease' }}
                xmlns="http://www.w3.org/2000/svg"
              >
                <defs>
                  <filter id="fullNeonGlow" x="-30%" y="-30%" width="160%" height="160%">
                    <feDropShadow dx="0" dy="0" stdDeviation="5" floodColor="#0284c7" floodOpacity="0.85" />
                    <feDropShadow dx="0" dy="0" stdDeviation="10" floodColor="#38bdf8" floodOpacity="0.6" />
                  </filter>

                  <filter id="fullPinShadow" x="-30%" y="-30%" width="160%" height="160%">
                    <feDropShadow dx="0" dy="3" stdDeviation="3" floodColor="#000000" floodOpacity="0.45" />
                  </filter>
                </defs>

                {/* BASE MAP LAYER: The user's city map */}
                <image
                  href="/maps/dispatch-map.jpg"
                  x="0"
                  y="0"
                  width="1024"
                  height="536"
                  preserveAspectRatio="none"
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

                {/* ACTIVE GPS NAVIGATION ROUTE */}
                {activeStop.id === 'stop-1' && (
                  <g>
                    <path
                      d="M 440 400 L 560 335 L 560 200"
                      fill="none"
                      stroke="#38bdf8"
                      strokeWidth="10"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      opacity="0.5"
                      filter="url(#fullNeonGlow)"
                    />
                    <path
                      d="M 440 400 L 560 335 L 560 200"
                      fill="none"
                      stroke="#0284c7"
                      strokeWidth="5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeDasharray="10 6"
                      className="anim-dark-gps-route"
                    />
                  </g>
                )}

                {activeStop.id === 'stop-2' && (
                  <g>
                    <path
                      d="M 440 400 L 680 270 L 710 240"
                      fill="none"
                      stroke="#38bdf8"
                      strokeWidth="10"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      opacity="0.5"
                      filter="url(#fullNeonGlow)"
                    />
                    <path
                      d="M 440 400 L 680 270 L 710 240"
                      fill="none"
                      stroke="#0284c7"
                      strokeWidth="5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeDasharray="10 6"
                      className="anim-dark-gps-route"
                    />
                  </g>
                )}

                {activeStop.id === 'stop-3' && (
                  <g>
                    <path
                      d="M 440 400 L 740 240 L 870 240 L 870 310"
                      fill="none"
                      stroke="#a855f7"
                      strokeWidth="10"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      opacity="0.5"
                      filter="url(#fullNeonGlow)"
                    />
                    <path
                      d="M 440 400 L 740 240 L 870 240 L 870 310"
                      fill="none"
                      stroke="#9333ea"
                      strokeWidth="5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeDasharray="10 6"
                      className="anim-dark-gps-route"
                    />
                  </g>
                )}

                {/* TECHNICIAN BEACON */}
                <g transform="translate(440, 400)" className="dark-beacon-group" filter="url(#fullPinShadow)">
                  <circle cx="0" cy="0" r="26" fill="#0284c7" opacity="0.25" className="beacon-radar-wave" />
                  <circle cx="0" cy="0" r="15" fill="#0369a1" opacity="0.35" />
                  <circle cx="0" cy="0" r="8.5" fill="#0284c7" stroke="#ffffff" strokeWidth="2.5" />
                  <polygon points="0,-12 4,-5 -4,-5" fill="#ffffff" />
                  <rect
                    x="-75"
                    y="-38"
                    width="150"
                    height="24"
                    rx="12"
                    fill="#0f172a"
                    stroke="#0284c7"
                    strokeWidth="1.2"
                    opacity="0.95"
                  />
                  <text x="0" y="-23" fill="#38bdf8" fontSize="11" fontWeight="700" textAnchor="middle">
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
                  <circle cx="0" cy="0" r="24" fill="#ef4444" opacity="0.25" className="marker-sonar-pulse" />
                  <path
                    d="M0 -28 C-10 -28 -18 -20 -18 -10 C-18 4 0 18 0 18 C0 18 18 4 18 -10 C18 -20 10 -28 0 -28 Z"
                    fill="#ef4444"
                    stroke="#ffffff"
                    strokeWidth="2"
                  />
                  <circle cx="0" cy="-10" r="5" fill="#ffffff" />
                  <rect
                    x="-75"
                    y="-60"
                    width="150"
                    height="26"
                    rx="13"
                    fill="#0f172a"
                    stroke="#ef4444"
                    strokeWidth="1.2"
                    opacity="0.95"
                  />
                  <text x="0" y="-43" fill="#ffffff" fontSize="11" fontWeight="800" textAnchor="middle">
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
                  <circle cx="0" cy="0" r="20" fill="#0284c7" opacity="0.22" />
                  <path
                    d="M0 -26 C-9 -26 -16 -19 -16 -10 C-16 3 0 16 0 16 C0 16 16 3 16 -10 C16 -19 9 -26 0 -26 Z"
                    fill="#0284c7"
                    stroke="#ffffff"
                    strokeWidth="2"
                  />
                  <circle cx="0" cy="-10" r="4.5" fill="#ffffff" />
                  <rect
                    x="-70"
                    y="-56"
                    width="140"
                    height="24"
                    rx="12"
                    fill="#0f172a"
                    stroke="#0284c7"
                    strokeWidth="1.2"
                    opacity="0.95"
                  />
                  <text x="0" y="-40" fill="#ffffff" fontSize="10.5" fontWeight="700" textAnchor="middle">
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
                  <circle cx="0" cy="0" r="20" fill="#9333ea" opacity="0.22" />
                  <path
                    d="M0 -26 C-9 -26 -16 -19 -16 -10 C-16 3 0 16 0 16 C0 16 16 3 16 -10 C16 -19 9 -26 0 -26 Z"
                    fill="#9333ea"
                    stroke="#ffffff"
                    strokeWidth="2"
                  />
                  <circle cx="0" cy="-10" r="4.5" fill="#ffffff" />
                  <rect
                    x="-75"
                    y="-56"
                    width="150"
                    height="24"
                    rx="12"
                    fill="#0f172a"
                    stroke="#9333ea"
                    strokeWidth="1.2"
                    opacity="0.95"
                  />
                  <text x="0" y="-40" fill="#ffffff" fontSize="10.5" fontWeight="700" textAnchor="middle">
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
