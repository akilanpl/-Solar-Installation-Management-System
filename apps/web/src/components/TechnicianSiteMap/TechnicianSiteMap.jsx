import React, { useState } from 'react';
import {
  Navigation,
  MapPin,
  Phone,
  ExternalLink,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Compass,
  Car,
  Wrench,
  ShieldCheck,
  Maximize2,
  Layers,
  ZoomIn,
  ZoomOut,
  Crosshair,
  Sun,
  Moon,
} from 'lucide-react';
import { useRouter } from '../../router/Router';
import './TechnicianSiteMap.css';

export const STOPS = [
  {
    id: 'stop-1',
    customerName: 'Arun Kumar',
    systemSize: '5 kW Hybrid Bifacial',
    area: 'Indiranagar / San Rafael',
    address: '#42, 4th Cross, 100ft Road, Indiranagar, Bengaluru - 560038',
    phone: '+91 98450 12345',
    ticketId: 'TK-1088',
    workOrderId: 'WO-2026-088',
    priority: 'Urgent',
    issueType: 'Inverter Red LED Trip',
    problemDescription:
      'Customer reports Inverter Red Alarm LED blinking with Error Code E-04 (Grid Disconnect / DC Ground Leakage). Rectify string inverter wiring and perform live AC/DC voltage measurement.',
    scheduledSlot: '10:00 AM - 12:30 PM',
    distance: '2.4 km',
    eta: '8 mins',
    traffic: 'Light Traffic (Green)',
    nextTurn: 'In 200m: Follow Paseo de la Reforma north toward San Rafael',
    mapCoords: { x: 560, y: 200 },
    lat: 12.9784,
    lng: 77.6408,
    status: 'en_route',
  },
  {
    id: 'stop-2',
    customerName: 'Arun Kumar (Villa)',
    systemSize: '3 kW Hybrid System',
    area: 'Doddanekkundi / Tabacalera',
    address: 'Villa 12, Ferns Paradise, Outer Ring Road, Doddanekkundi, Bengaluru - 560037',
    phone: '+91 98450 12345',
    ticketId: 'WO-INST-004',
    workOrderId: 'WO-2026-092',
    priority: 'High',
    issueType: 'Pre-Installation Structure Markings',
    problemDescription:
      'Perform roof tile anchor pull test (min 120 kg rating) and inspect mounting bracket clearance before warehouse material dispatch.',
    scheduledSlot: '01:00 PM - 03:00 PM',
    distance: '6.8 km',
    eta: '22 mins',
    traffic: 'Moderate (Yellow)',
    nextTurn: 'In 450m: Continue east on Paseo de la Reforma to Tabacalera',
    mapCoords: { x: 710, y: 240 },
    lat: 12.9698,
    lng: 77.6984,
    status: 'scheduled',
  },
  {
    id: 'stop-3',
    customerName: 'TechSpark Innovation Labs (Rajesh Mehra)',
    systemSize: '10 kW Commercial 3-Phase',
    area: 'Whitefield / Balderas Hub',
    address: 'TechSpark Labs, ITPL Main Road, Whitefield, Bengaluru - 560066',
    phone: '+91 98112 34567',
    ticketId: 'JOB-SURV-001',
    workOrderId: 'WO-2026-099',
    priority: 'Normal',
    issueType: 'Commercial Net-Metering & DB Inspection',
    problemDescription:
      'Measure 3D solar shadow ray-tracing for parapet, verify 3-phase incoming distribution board, and confirm AC isolator breaker headroom.',
    scheduledSlot: '03:30 PM - 05:45 PM',
    distance: '14.2 km',
    eta: '35 mins',
    traffic: 'Moderate (Yellow)',
    nextTurn: 'In 800m: Turn east onto Av. Juárez towards Balderas Hub',
    mapCoords: { x: 870, y: 310 },
    lat: 12.9863,
    lng: 77.7346,
    status: 'scheduled',
  },
];

export function TechnicianSiteMap({ onCheckIn, onToast, isStandalone = false }) {
  const { navigate } = useRouter();
  const [selectedStopId, setSelectedStopId] = useState('stop-1');
  const [arrivedStops, setArrivedStops] = useState({});
  const [mapMode, setMapMode] = useState('street'); // 'street' | 'night'
  const [zoomLevel, setZoomLevel] = useState(1);

  const activeStop = STOPS.find((s) => s.id === selectedStopId) || STOPS[0];

  const handleStartNavigation = (stop) => {
    const url = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(
      stop.address
    )}`;
    window.open(url, '_blank', 'noopener,noreferrer');
    if (onToast) {
      onToast({
        type: 'info',
        title: 'GPS Navigation Activated',
        message: `Turn-by-turn route opened for ${stop.customerName} (${stop.area}).`,
      });
    }
  };

  const handleMarkArrived = (stopId) => {
    setArrivedStops((prev) => ({ ...prev, [stopId]: true }));
    if (onToast) {
      onToast({
        type: 'success',
        title: 'Arrived at Customer Site',
        message: `Arrival logged for ${activeStop.customerName}. Customer OTP verified for check-in.`,
      });
    }
    if (onCheckIn) {
      onCheckIn(activeStop);
    }
  };

  const isArrived = !!arrivedStops[activeStop.id];

  return (
    <div
      className={`tech-map-dark-container ${isStandalone ? 'standalone-mode' : ''} mode-${mapMode}`}
      aria-label="Field Technician Customer Site Map"
    >
      {/* Header Bar */}
      <div className="tech-dark-header">
        <div>
          <div className="tech-dark-title-row">
            <Navigation size={18} color="#0284c7" />
            <h3 className="tech-dark-title">Field Dispatch & Navigation Map</h3>
            <span className="dark-theme-badge">Live City Road Map</span>
          </div>
          <span className="tech-dark-subtitle">
            Turn-by-turn street routing to customer premises for on-site diagnosis and fault rectification.
          </span>
        </div>

        <div className="tech-dark-header-actions">
          {/* Map Layer Switcher: Street Map vs Night Navigation */}
          <div className="map-layer-selector">
            <button
              type="button"
              className={`layer-btn ${mapMode === 'street' ? 'active' : ''}`}
              onClick={() => setMapMode('street')}
              title="Standard Street Map View"
            >
              <Sun size={13} />
              <span>Street</span>
            </button>
            <button
              type="button"
              className={`layer-btn ${mapMode === 'night' ? 'active' : ''}`}
              onClick={() => setMapMode('night')}
              title="Night Navigation View"
            >
              <Moon size={13} />
              <span>Night</span>
            </button>
          </div>

          <div className="tech-dark-stats">
            <span className="dark-stat-chip">
              <Car size={13} color="#0284c7" />
              <span>3 Stops · 23.4 km</span>
            </span>
            <span className="dark-live-gps-pill">
              <span className="dark-live-dot" />
              <span>GPS Tracking Live</span>
            </span>
          </div>

          {!isStandalone && (
            <button
              type="button"
              className="open-fullscreen-map-btn"
              onClick={() => navigate('/technician/map')}
              title="Open Dedicated Full Page Map"
            >
              <Maximize2 size={13} />
              <span>Full Page Map</span>
            </button>
          )}
        </div>
      </div>

      {/* Stop Selection Tabs */}
      <div className="tech-dark-stops-row" role="tablist">
        {STOPS.map((stop, index) => {
          const isSelected = stop.id === selectedStopId;
          const stopArrived = arrivedStops[stop.id];

          return (
            <button
              key={stop.id}
              type="button"
              role="tab"
              aria-selected={isSelected}
              className={`tech-dark-stop-pill ${isSelected ? 'active' : ''} ${
                stopArrived ? 'arrived' : ''
              }`}
              onClick={() => setSelectedStopId(stop.id)}
            >
              <div className="dark-stop-num">
                {stopArrived ? '✓' : index + 1}
              </div>
              <div className="dark-stop-info">
                <span className="dark-stop-area">{stop.area}</span>
                <span className="dark-stop-cust">
                  {stop.customerName.split(' ')[0]} · {stop.distance}
                </span>
              </div>
              {stop.priority === 'Urgent' && (
                <span className="dark-urgent-dot" title="Urgent Inverter Alarm" />
              )}
            </button>
          );
        })}
      </div>

      {/* Map Viewport featuring the Uploaded Real City Street Map */}
      <div className="tech-dark-map-viewport">
        {/* Floating Zoom Controls */}
        <div className="map-inner-zoom-controls">
          <button
            type="button"
            className="zoom-mini-btn"
            onClick={() => setZoomLevel((z) => Math.min(z + 0.15, 1.45))}
            title="Zoom In"
          >
            <ZoomIn size={14} />
          </button>
          <button
            type="button"
            className="zoom-mini-btn"
            onClick={() => setZoomLevel((z) => Math.max(z - 0.15, 0.85))}
            title="Zoom Out"
          >
            <ZoomOut size={14} />
          </button>
          <button
            type="button"
            className="zoom-mini-btn"
            onClick={() => setZoomLevel(1)}
            title="Recenter Map"
          >
            <Crosshair size={14} />
          </button>
        </div>

        <svg
          className="tech-dark-vector-map-svg"
          viewBox="0 0 1024 536"
          preserveAspectRatio="none"
          style={{ transform: `scale(${zoomLevel})`, transition: 'transform 0.25s ease' }}
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            {/* Glowing route stroke filter */}
            <filter id="neonRouteGlow" x="-30%" y="-30%" width="160%" height="160%">
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#0284c7" floodOpacity="0.8" />
              <feDropShadow dx="0" dy="0" stdDeviation="8" floodColor="#38bdf8" floodOpacity="0.5" />
            </filter>

            {/* Marker pin drop shadow */}
            <filter id="pinShadow" x="-30%" y="-30%" width="160%" height="160%">
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
            className={`tech-map-raster-base ${mapMode === 'night' ? 'night-filter' : ''}`}
          />

          {/* Night Mode Subtle Tint Overlay */}
          {mapMode === 'night' && (
            <rect width="1024" height="536" fill="#0b0f19" opacity="0.25" pointerEvents="none" />
          )}

          {/* Street Corridor Highlights */}
          {/* Paseo de la Reforma Trunk Corridor highlight line */}
          <line
            x1="220"
            y1="520"
            x2="880"
            y2="195"
            stroke="#0284c7"
            strokeWidth="3"
            opacity={mapMode === 'night' ? '0.45' : '0.2'}
            strokeDasharray="4 6"
            pointerEvents="none"
          />

          {/* ACTIVE GPS NAVIGATION ROUTE OVERLAY */}
          {/* Stop 1: Indiranagar / San Rafael (Along Reforma then north on Rio Marne/Sullivan) */}
          {activeStop.id === 'stop-1' && (
            <g>
              {/* Outer Glow Path */}
              <path
                d="M 440 400 L 560 335 L 560 200"
                fill="none"
                stroke="#38bdf8"
                strokeWidth="10"
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity="0.5"
                filter="url(#neonRouteGlow)"
              />
              {/* Core Animated Path */}
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

          {/* Stop 2: Doddanekkundi / Tabacalera (Along Reforma to Ignacio Mariscal / Tabacalera) */}
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
                filter="url(#neonRouteGlow)"
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

          {/* Stop 3: Whitefield / Balderas Hub (Along Reforma to Av. Juárez / Balderas) */}
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
                filter="url(#neonRouteGlow)"
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

          {/* TECHNICIAN LIVE GPS BEACON (On Paseo de la Reforma / Rio Lerma) */}
          <g transform="translate(440, 400)" className="dark-beacon-group" filter="url(#pinShadow)">
            <circle cx="0" cy="0" r="24" fill="#0284c7" opacity="0.25" className="beacon-radar-wave" />
            <circle cx="0" cy="0" r="14" fill="#0369a1" opacity="0.35" />
            <circle cx="0" cy="0" r="8.5" fill="#0284c7" stroke="#ffffff" strokeWidth="2.5" />
            {/* Heading Arrow indicator */}
            <polygon points="0,-12 4,-5 -4,-5" fill="#ffffff" />
            <rect
              x="-75"
              y="-38"
              width="150"
              height="22"
              rx="11"
              fill="#0f172a"
              stroke="#0284c7"
              strokeWidth="1.2"
              opacity="0.95"
            />
            <text x="0" y="-24" fill="#38bdf8" fontSize="10.5" fontWeight="700" textAnchor="middle">
              Technician Live (Karthik)
            </text>
          </g>

          {/* STOP 1 PIN: INDIRANAGAR / SAN RAFAEL (Arun Kumar - Urgent Inverter E-04) */}
          <g
            transform="translate(560, 200)"
            className={`dark-marker-pin ${selectedStopId === 'stop-1' ? 'active-pin' : ''}`}
            onClick={() => setSelectedStopId('stop-1')}
            filter="url(#pinShadow)"
          >
            <circle cx="0" cy="0" r="22" fill="#ef4444" opacity="0.25" className="marker-sonar-pulse" />
            <path
              d="M0 -28 C-10 -28 -18 -20 -18 -10 C-18 4 0 18 0 18 C0 18 18 4 18 -10 C18 -20 10 -28 0 -28 Z"
              fill="#ef4444"
              stroke="#ffffff"
              strokeWidth="2"
            />
            <circle cx="0" cy="-10" r="5" fill="#ffffff" />
            <rect
              x="-75"
              y="-58"
              width="150"
              height="24"
              rx="12"
              fill="#0f172a"
              stroke="#ef4444"
              strokeWidth="1.2"
              opacity="0.95"
            />
            <text x="0" y="-42" fill="#ffffff" fontSize="10.5" fontWeight="800" textAnchor="middle">
              Arun Kumar · E-04 Red LED
            </text>
          </g>

          {/* STOP 2 PIN: DODDANEKKUNDI / TABACALERA (Villa 12 - Pre-Install Survey) */}
          <g
            transform="translate(710, 240)"
            className={`dark-marker-pin ${selectedStopId === 'stop-2' ? 'active-pin' : ''}`}
            onClick={() => setSelectedStopId('stop-2')}
            filter="url(#pinShadow)"
          >
            <circle cx="0" cy="0" r="18" fill="#0284c7" opacity="0.22" />
            <path
              d="M0 -26 C-9 -26 -16 -19 -16 -10 C-16 3 0 16 0 16 C0 16 16 3 16 -10 C16 -19 9 -26 0 -26 Z"
              fill="#0284c7"
              stroke="#ffffff"
              strokeWidth="2"
            />
            <circle cx="0" cy="-10" r="4.5" fill="#ffffff" />
            <rect
              x="-70"
              y="-54"
              width="140"
              height="22"
              rx="11"
              fill="#0f172a"
              stroke="#0284c7"
              strokeWidth="1.2"
              opacity="0.95"
            />
            <text x="0" y="-39" fill="#ffffff" fontSize="10" fontWeight="700" textAnchor="middle">
              Villa 12 · Structure Markings
            </text>
          </g>

          {/* STOP 3 PIN: WHITEFIELD / BALDERAS HUB (TechSpark - Commercial 3-Phase DB) */}
          <g
            transform="translate(870, 310)"
            className={`dark-marker-pin ${selectedStopId === 'stop-3' ? 'active-pin' : ''}`}
            onClick={() => setSelectedStopId('stop-3')}
            filter="url(#pinShadow)"
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
              x="-75"
              y="-54"
              width="150"
              height="22"
              rx="11"
              fill="#0f172a"
              stroke="#9333ea"
              strokeWidth="1.2"
              opacity="0.95"
            />
            <text x="0" y="-39" fill="#ffffff" fontSize="10" fontWeight="700" textAnchor="middle">
              TechSpark · 10kW Commercial DB
            </text>
          </g>
        </svg>

        {/* Live Navigation Heads-Up Display (Glassmorphic HUD) */}
        <div className="tech-dark-hud-overlay">
          <div className="dark-hud-chip">
            <Compass size={14} color="#0284c7" />
            <span>NE · Heading 042° Straight</span>
          </div>
          <div className="dark-hud-chip next-step">
            <Navigation size={14} color="#10b981" />
            <span>{activeStop.nextTurn}</span>
          </div>
          <div className="dark-hud-chip">
            <span className="traffic-live-dot" />
            <span>{activeStop.traffic}</span>
          </div>
          <div className="dark-hud-chip speed-chip">
            <span>42 km/h</span>
          </div>
        </div>
      </div>

      {/* Selected Customer Site Action Panel */}
      <div className="tech-dark-action-card">
        <div className="dark-site-info-col">
          <div className="dark-tag-row">
            <span className="dark-priority-pill-urgent">
              <AlertTriangle size={12} />
              <span>{activeStop.issueType}</span>
            </span>
            <span className="dark-tag-pill">{activeStop.workOrderId}</span>
            <span className="dark-tag-pill">{activeStop.systemSize}</span>
            <span className="dark-eta-pill">
              <Clock size={12} />
              <span>
                {activeStop.distance} · {activeStop.eta} away
              </span>
            </span>
          </div>

          <h4 className="dark-customer-title">
            <span>{activeStop.customerName}</span>
            <span className="dark-slot-sub">({activeStop.scheduledSlot})</span>
          </h4>

          <div className="dark-address-row">
            <MapPin size={14} color="#64748b" className="flex-shrink-0" />
            <span>{activeStop.address}</span>
          </div>

          <div className="dark-directive-box">
            <strong>Rectification Directive:</strong> {activeStop.problemDescription}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="dark-actions-col">
          <button
            type="button"
            className="dark-nav-btn primary"
            onClick={() => handleStartNavigation(activeStop)}
          >
            <Navigation size={15} />
            <span>Start GPS Navigation</span>
            <ExternalLink size={13} opacity={0.7} />
          </button>

          <a
            href={`tel:${activeStop.phone}`}
            className="dark-nav-btn secondary"
            title="Call Customer"
          >
            <Phone size={15} />
            <span>Call Customer</span>
          </a>

          <button
            type="button"
            className={`dark-nav-btn ${isArrived ? 'verified' : 'outline'}`}
            onClick={() => handleMarkArrived(activeStop.id)}
          >
            {isArrived ? (
              <>
                <CheckCircle2 size={15} color="#34d399" />
                <span>On-Site Check-in Verified</span>
              </>
            ) : (
              <>
                <ShieldCheck size={15} />
                <span>Arrived at Customer Site</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default TechnicianSiteMap;
