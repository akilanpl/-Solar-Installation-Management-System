import React, { useState } from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from '../../router/Router';
import { TechnicianSiteMap, STOPS } from '../../components/TechnicianSiteMap/TechnicianSiteMap';
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
} from 'lucide-react';
import './TechnicianMapPage.css';

export function TechnicianMapPage() {
  const { user, showToast } = useAuth();
  const { navigate } = useRouter();

  const [activeStopId, setActiveStopId] = useState('stop-1');
  const [arrivedStops, setArrivedStops] = useState({});
  const [zoomLevel, setZoomLevel] = useState(1);
  const [activeLayer, setActiveLayer] = useState('dark_grid');

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
              <Navigation size={22} color="#38bdf8" />
              <h1>Field Route & Live GPS Navigation</h1>
              <span className="live-dispatch-badge">
                <span className="live-dot-green" />
                <span>Live Dispatch Telemetry</span>
              </span>
            </div>
            <p className="page-subtitle">
              Turn-by-turn navigation across Bengaluru for on-site solar inspections, DC ground fault diagnostics, and customer problem rectification.
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

          {/* Right Column: Full-Height Dark Vector City Grid Map */}
          <div className="tech-fullmap-col">
            {/* Map Canvas Toolbars */}
            <div className="map-canvas-controls-bar">
              <div className="map-view-toggles">
                <button
                  type="button"
                  className={`layer-toggle-btn ${activeLayer === 'dark_grid' ? 'active' : ''}`}
                  onClick={() => setActiveLayer('dark_grid')}
                >
                  <Layers size={13} />
                  <span>Dark Street Grid</span>
                </button>
                <button
                  type="button"
                  className={`layer-toggle-btn ${activeLayer === 'traffic' ? 'active' : ''}`}
                  onClick={() => setActiveLayer('traffic')}
                >
                  <Radio size={13} />
                  <span>Live Traffic Flow</span>
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

            {/* Expansive Dark Map Viewport */}
            <div className="standalone-dark-map-viewport">
              <svg
                className="standalone-vector-map-svg"
                viewBox="0 0 1000 520"
                preserveAspectRatio="none"
                style={{ transform: `scale(${zoomLevel})`, transition: 'transform 0.25s ease' }}
                xmlns="http://www.w3.org/2000/svg"
              >
                <defs>
                  <pattern id="full_dark_grid_mesh" width="30" height="30" patternUnits="userSpaceOnUse">
                    <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#131b2c" strokeWidth="0.8" />
                  </pattern>

                  <filter id="fullNeonGlow" x="-30%" y="-30%" width="160%" height="160%">
                    <feDropShadow dx="0" dy="0" stdDeviation="6" floodColor="#38bdf8" floodOpacity="0.9" />
                    <feDropShadow dx="0" dy="0" stdDeviation="12" floodColor="#0284c7" floodOpacity="0.6" />
                  </filter>

                  <filter id="fullOverpassShadow" x="-10%" y="-10%" width="120%" height="120%">
                    <feDropShadow dx="0" dy="4" stdDeviation="4" floodColor="#000000" floodOpacity="0.8" />
                  </filter>
                </defs>

                {/* Dark Base */}
                <rect width="1000" height="520" fill="#0b0f17" />
                <rect width="1000" height="520" fill="url(#full_dark_grid_mesh)" opacity="0.6" />

                {/* City Blocks (Straight Urban Parcels) */}
                <g fill="#101726" stroke="#162035" strokeWidth="1">
                  <rect x="50" y="50" width="100" height="65" rx="3" />
                  <rect x="50" y="135" width="100" height="85" rx="3" />
                  <rect x="50" y="270" width="100" height="95" rx="3" />
                  <rect x="50" y="390" width="100" height="85" rx="3" />

                  {/* Indiranagar Blocks */}
                  <rect x="180" y="50" width="135" height="70" rx="3" />
                  <rect x="180" y="155" width="135" height="65" rx="3" />
                  <rect x="180" y="270" width="135" height="95" rx="3" />
                  <rect x="180" y="390" width="135" height="85" rx="3" />

                  <rect x="360" y="50" width="115" height="70" rx="3" />
                  <rect x="360" y="155" width="115" height="65" rx="3" />
                  <rect x="360" y="270" width="115" height="95" rx="3" />
                  <rect x="360" y="390" width="115" height="85" rx="3" />

                  {/* Central Corridor Blocks */}
                  <rect x="495" y="50" width="105" height="70" rx="3" />
                  <rect x="495" y="155" width="105" height="65" rx="3" />
                  <rect x="495" y="270" width="105" height="95" rx="3" />

                  {/* East Corridor / Doddanekkundi Blocks */}
                  <rect x="640" y="50" width="170" height="80" rx="3" />
                  <rect x="640" y="155" width="170" height="65" rx="3" />
                  <rect x="640" y="270" width="170" height="65" rx="3" />
                  <rect x="640" y="365" width="170" height="110" rx="3" />

                  {/* Whitefield Blocks */}
                  <rect x="860" y="50" width="105" height="75" rx="3" />
                  <rect x="860" y="155" width="105" height="75" rx="3" />
                  <rect x="860" y="270" width="105" height="90" rx="3" />
                  <rect x="860" y="385" width="105" height="90" rx="3" />
                </g>

                {/* Water Bodies */}
                <path
                  d="M 60 55 C 100 45, 140 50, 155 85 C 165 115, 135 140, 95 130 C 65 120, 50 90, 60 55 Z"
                  fill="#0e1726"
                  stroke="#1e2c45"
                  strokeWidth="1.5"
                />
                <text x="85" y="95" fill="#38bdf8" fontSize="10" fontWeight="600" opacity="0.6">
                  Ulsoor Lake
                </text>

                <path
                  d="M 500 380 C 560 370, 650 380, 680 415 C 690 455, 610 475, 550 470 C 480 465, 470 410, 500 380 Z"
                  fill="#0e1726"
                  stroke="#1e2c45"
                  strokeWidth="1.5"
                />
                <text x="545" y="430" fill="#38bdf8" fontSize="10" fontWeight="600" opacity="0.6">
                  Bellandur Lake
                </text>

                {/* Minor Straight Cross-Streets */}
                <g stroke="#1a2438" strokeWidth="2" strokeLinecap="square">
                  <line x1="40" y1="95" x2="960" y2="95" />
                  <line x1="40" y1="185" x2="960" y2="185" />
                  <line x1="40" y1="315" x2="960" y2="315" />
                  <line x1="40" y1="415" x2="960" y2="415" />

                  <line x1="120" y1="40" x2="120" y2="480" />
                  <line x1="240" y1="40" x2="240" y2="480" />
                  <line x1="420" y1="40" x2="420" y2="480" />
                  <line x1="550" y1="40" x2="550" y2="480" />
                  <line x1="720" y1="40" x2="720" y2="480" />
                  <line x1="910" y1="40" x2="910" y2="480" />
                </g>

                {/* MAJOR STRAIGHT ARTERIAL AVENUES */}

                {/* Old Airport Road */}
                <g>
                  <line x1="40" y1="245" x2="960" y2="245" stroke="#162032" strokeWidth="18" />
                  <line x1="40" y1="245" x2="960" y2="245" stroke="#25354e" strokeWidth="9" />
                  <line x1="40" y1="245" x2="960" y2="245" stroke="#0b0f17" strokeWidth="1" strokeDasharray="6 8" />
                </g>

                {/* CMH Road Metro Line */}
                <g>
                  <line x1="140" y1="140" x2="540" y2="140" stroke="#162032" strokeWidth="14" />
                  <line x1="140" y1="140" x2="540" y2="140" stroke="#25354e" strokeWidth="7" />
                </g>

                {/* Indiranagar 100 Feet Road */}
                <g>
                  <line x1="340" y1="40" x2="340" y2="480" stroke="#162032" strokeWidth="16" />
                  <line x1="340" y1="40" x2="340" y2="480" stroke="#2a3d59" strokeWidth="8" />
                  <line x1="340" y1="40" x2="340" y2="480" stroke="#0b0f17" strokeWidth="1" strokeDasharray="6 8" />
                </g>

                {/* Outer Ring Road (ORR) Expressway Overpass */}
                <g filter="url(#fullOverpassShadow)">
                  <line x1="620" y1="40" x2="620" y2="480" stroke="#111a29" strokeWidth="20" />
                  <line x1="620" y1="40" x2="620" y2="480" stroke="#334768" strokeWidth="11" />
                  <line x1="620" y1="40" x2="620" y2="480" stroke="#0b0f17" strokeWidth="1.5" strokeDasharray="8 6" />
                </g>

                {/* ITPL Main Road Whitefield */}
                <g>
                  <line x1="840" y1="40" x2="840" y2="480" stroke="#162032" strokeWidth="16" />
                  <line x1="840" y1="40" x2="840" y2="480" stroke="#25354e" strokeWidth="8" />
                </g>

                {/* Flyover Bridge Cross at Old Airport Road */}
                <rect x="606" y="232" width="28" height="26" fill="#334768" stroke="#475569" strokeWidth="1.5" rx="3" filter="url(#fullOverpassShadow)" />

                {/* Metro Transit Station Badges (M) */}
                <g transform="translate(180, 140)">
                  <circle cx="0" cy="0" r="8" fill="#0b0f17" stroke="#ffffff" strokeWidth="1.5" />
                  <text x="0" y="3.5" fill="#ffffff" fontSize="8" fontWeight="900" textAnchor="middle">M</text>
                  <text x="14" y="3.5" fill="#cbd5e1" fontSize="10.5" fontWeight="600">Halasuru</text>
                </g>

                <g transform="translate(340, 140)">
                  <circle cx="0" cy="0" r="8" fill="#0b0f17" stroke="#ffffff" strokeWidth="1.5" />
                  <text x="0" y="3.5" fill="#ffffff" fontSize="8" fontWeight="900" textAnchor="middle">M</text>
                  <text x="14" y="3.5" fill="#cbd5e1" fontSize="10.5" fontWeight="600">Indiranagar</text>
                </g>

                <g transform="translate(500, 140)">
                  <circle cx="0" cy="0" r="8" fill="#0b0f17" stroke="#ffffff" strokeWidth="1.5" />
                  <text x="0" y="3.5" fill="#ffffff" fontSize="8" fontWeight="900" textAnchor="middle">M</text>
                  <text x="14" y="3.5" fill="#cbd5e1" fontSize="10.5" fontWeight="600">Baiyappanahalli</text>
                </g>

                <g transform="translate(840, 140)">
                  <circle cx="0" cy="0" r="8" fill="#0b0f17" stroke="#ffffff" strokeWidth="1.5" />
                  <text x="0" y="3.5" fill="#ffffff" fontSize="8" fontWeight="900" textAnchor="middle">M</text>
                  <text x="14" y="3.5" fill="#cbd5e1" fontSize="10.5" fontWeight="600">ITPL</text>
                </g>

                {/* Street Labels */}
                <text x="355" y="70" fill="#94a3b8" fontSize="11" fontWeight="700" letterSpacing="0.04em">
                  100 FT RD · INDIRANAGAR
                </text>
                <text x="635" y="75" fill="#94a3b8" fontSize="11" fontWeight="700" letterSpacing="0.04em">
                  OUTER RING ROAD (ORR)
                </text>
                <text x="855" y="75" fill="#94a3b8" fontSize="11" fontWeight="700" letterSpacing="0.04em">
                  ITPL MAIN RD · WHITEFIELD
                </text>

                {/* ACTIVE STRAIGHT GPS ROUTE */}
                {activeStop.id === 'stop-1' && (
                  <path
                    d="M 180 245 L 340 245 L 340 140"
                    fill="none"
                    stroke="#38bdf8"
                    strokeWidth="5.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeDasharray="9 5"
                    className="anim-dark-gps-route"
                    filter="url(#fullNeonGlow)"
                  />
                )}

                {activeStop.id === 'stop-2' && (
                  <path
                    d="M 180 245 L 620 245 L 620 340"
                    fill="none"
                    stroke="#38bdf8"
                    strokeWidth="5.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeDasharray="9 5"
                    className="anim-dark-gps-route"
                    filter="url(#fullNeonGlow)"
                  />
                )}

                {activeStop.id === 'stop-3' && (
                  <path
                    d="M 180 245 L 620 245 L 840 245 L 840 140"
                    fill="none"
                    stroke="#38bdf8"
                    strokeWidth="5.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeDasharray="9 5"
                    className="anim-dark-gps-route"
                    filter="url(#fullNeonGlow)"
                  />
                )}

                {/* TECHNICIAN BEACON */}
                <g transform="translate(180, 245)" className="dark-beacon-group">
                  <circle cx="0" cy="0" r="28" fill="#38bdf8" opacity="0.22" className="beacon-radar-wave" />
                  <circle cx="0" cy="0" r="16" fill="#0284c7" opacity="0.35" />
                  <circle cx="0" cy="0" r="9" fill="#38bdf8" stroke="#ffffff" strokeWidth="2.5" />
                  <rect x="-70" y="-38" width="140" height="24" rx="12" fill="#030712" stroke="#38bdf8" strokeWidth="1" opacity="0.95" />
                  <text x="0" y="-22" fill="#38bdf8" fontSize="10.5" fontWeight="700" textAnchor="middle">
                    Technician Live (Karthik)
                  </text>
                </g>

                {/* DESTINATION PINS */}
                {/* Stop 1 */}
                <g
                  transform="translate(340, 140)"
                  className={`dark-marker-pin ${activeStop.id === 'stop-1' ? 'active-pin' : ''}`}
                  onClick={() => setActiveStopId('stop-1')}
                >
                  <circle cx="0" cy="0" r="24" fill="#ef4444" opacity="0.22" className="marker-sonar-pulse" />
                  <path
                    d="M0 -28 C-10 -28 -18 -20 -18 -10 C-18 2 0 18 0 18 C0 18 18 2 18 -10 C18 -20 10 -28 0 -28 Z"
                    fill="#ef4444"
                    stroke="#ffffff"
                    strokeWidth="2"
                  />
                  <circle cx="0" cy="-10" r="5" fill="#ffffff" />
                  <rect x="-75" y="-60" width="150" height="26" rx="13" fill="#030712" stroke="#ef4444" strokeWidth="1" opacity="0.95" />
                  <text x="0" y="-43" fill="#ffffff" fontSize="11" fontWeight="800" textAnchor="middle">
                    Arun Kumar · E-04 Red LED
                  </text>
                </g>

                {/* Stop 2 */}
                <g
                  transform="translate(620, 340)"
                  className={`dark-marker-pin ${activeStop.id === 'stop-2' ? 'active-pin' : ''}`}
                  onClick={() => setActiveStopId('stop-2')}
                >
                  <circle cx="0" cy="0" r="20" fill="#38bdf8" opacity="0.18" />
                  <path
                    d="M0 -26 C-9 -26 -16 -19 -16 -10 C-16 2 0 16 0 16 C0 16 16 2 16 -10 C16 -19 9 -26 0 -26 Z"
                    fill="#0284c7"
                    stroke="#ffffff"
                    strokeWidth="2"
                  />
                  <circle cx="0" cy="-10" r="4.5" fill="#ffffff" />
                  <rect x="-70" y="-56" width="140" height="24" rx="12" fill="#030712" stroke="#0284c7" strokeWidth="1" opacity="0.92" />
                  <text x="0" y="-40" fill="#ffffff" fontSize="10.5" fontWeight="700" textAnchor="middle">
                    Villa 12 · Anchor Pull Test
                  </text>
                </g>

                {/* Stop 3 */}
                <g
                  transform="translate(840, 140)"
                  className={`dark-marker-pin ${activeStop.id === 'stop-3' ? 'active-pin' : ''}`}
                  onClick={() => setActiveStopId('stop-3')}
                >
                  <circle cx="0" cy="0" r="20" fill="#a855f7" opacity="0.18" />
                  <path
                    d="M0 -26 C-9 -26 -16 -19 -16 -10 C-16 2 0 16 0 16 C0 16 16 2 16 -10 C16 -19 9 -26 0 -26 Z"
                    fill="#9333ea"
                    stroke="#ffffff"
                    strokeWidth="2"
                  />
                  <circle cx="0" cy="-10" r="4.5" fill="#ffffff" />
                  <rect x="-75" y="-56" width="150" height="24" rx="12" fill="#030712" stroke="#9333ea" strokeWidth="1" opacity="0.92" />
                  <text x="0" y="-40" fill="#ffffff" fontSize="10.5" fontWeight="700" textAnchor="middle">
                    TechSpark · 10kW 3-Phase
                  </text>
                </g>
              </svg>

              {/* HUD Overlay */}
              <div className="standalone-hud-overlay">
                <div className="standalone-hud-chip">
                  <Compass size={14} color="#38bdf8" />
                  <span>North · Heading 000° Straight</span>
                </div>
                <div className="standalone-hud-chip next-step">
                  <Navigation size={14} color="#10b981" />
                  <span>In 250m: Turn North onto 100 Feet Rd</span>
                </div>
                <div className="standalone-hud-chip">
                  <span className="traffic-live-dot" />
                  <span>{activeStop.traffic}</span>
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
