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
  ZoomIn,
  ZoomOut,
  Crosshair,
  Radio,
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
      className={`tech-map-dashboard-container ${isStandalone ? 'standalone-mode' : ''}`}
      aria-label="Field Technician Customer Site Map"
    >
      {/* Header Bar matching Dashboard UI Color Theme */}
      <div className="tech-map-header">
        <div className="header-title-column">
          <div className="title-with-badge">
            <div className="map-nav-icon-bubble">
              <Navigation size={18} color="#0284c7" />
            </div>
            <h3 className="tech-map-title">Field Dispatch & Navigation Map</h3>
            <span className="live-road-map-chip">Live City Street Network</span>
          </div>
          <span className="tech-map-subtitle">
            Turn-by-turn street routing to customer premises for on-site diagnosis and fault rectification.
          </span>
        </div>

        <div className="tech-map-actions">
          <div className="map-stats-group">
            <span className="stat-pill-item">
              <Car size={13} color="#0284c7" />
              <span>3 Stops · 23.4 km</span>
            </span>
            <span className="stat-pill-live">
              <span className="live-gps-dot" />
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

      {/* Stop Selection Tabs in Dashboard Theme */}
      <div className="tech-stops-tabs-row" role="tablist">
        {STOPS.map((stop, index) => {
          const isSelected = stop.id === selectedStopId;
          const stopArrived = arrivedStops[stop.id];

          return (
            <button
              key={stop.id}
              type="button"
              role="tab"
              aria-selected={isSelected}
              className={`tech-stop-tab-card ${isSelected ? 'active' : ''} ${
                stopArrived ? 'arrived' : ''
              }`}
              onClick={() => setSelectedStopId(stop.id)}
            >
              <div className="stop-tab-num">
                {stopArrived ? '✓' : index + 1}
              </div>
              <div className="stop-tab-info">
                <span className="stop-tab-area">{stop.area}</span>
                <span className="stop-tab-sub">
                  {stop.customerName.split(' ')[0]} · {stop.distance}
                </span>
              </div>
              {stop.priority === 'Urgent' && (
                <span className="stop-urgent-dot" title="Urgent Inverter Alarm" />
              )}
            </button>
          );
        })}
      </div>

      {/* Map Viewport in True Uncompressed Proportions */}
      <div className="tech-map-viewport">
        {/* Floating Zoom & Recenter Controls */}
        <div className="map-zoom-overlay-controls">
          <button
            type="button"
            className="zoom-tool-btn"
            onClick={() => setZoomLevel((z) => Math.min(z + 0.15, 1.45))}
            title="Zoom In"
          >
            <ZoomIn size={14} />
          </button>
          <button
            type="button"
            className="zoom-tool-btn"
            onClick={() => setZoomLevel((z) => Math.max(z - 0.15, 0.85))}
            title="Zoom Out"
          >
            <ZoomOut size={14} />
          </button>
          <button
            type="button"
            className="zoom-tool-btn"
            onClick={() => setZoomLevel(1)}
            title="Recenter Map"
          >
            <Crosshair size={14} />
          </button>
        </div>

        <svg
          className="tech-vector-map-svg"
          viewBox="0 0 1024 536"
          preserveAspectRatio="xMidYMid meet"
          style={{ transform: `scale(${zoomLevel})`, transition: 'transform 0.25s ease' }}
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            {/* Subtle soft aura for continuous navigation path */}
            <filter id="cleanRouteAura" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="1" stdDeviation="2.5" floodColor="#1a73e8" floodOpacity="0.4" />
            </filter>

            {/* Drop shadow for floating white pin labels */}
            <filter id="cleanCardShadow" x="-20%" y="-20%" width="140%" height="140%">
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
            className="tech-map-raster-base"
          />

          {/* ACTIVE GPS NAVIGATION GUIDE LINES: Thin continuous lines following actual streets */}
          {/* Stop 1: Indiranagar / San Rafael (Continuous thin line along Reforma to Sullivan) */}
          {activeStop.id === 'stop-1' && (
            <g filter="url(#cleanRouteAura)">
              {/* Outer soft aura */}
              <path
                d="M 440 400 L 560 335 L 560 200"
                fill="none"
                stroke="#93c5fd"
                strokeWidth="6"
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity="0.5"
              />
              {/* Thin continuous solid guide line */}
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

          {/* Stop 2: Doddanekkundi / Tabacalera (Continuous thin line along Reforma to Tabacalera) */}
          {activeStop.id === 'stop-2' && (
            <g filter="url(#cleanRouteAura)">
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

          {/* Stop 3: Whitefield / Balderas Hub (Continuous thin line along Reforma to Av. Juárez & Balderas) */}
          {activeStop.id === 'stop-3' && (
            <g filter="url(#cleanRouteAura)">
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

          {/* TECHNICIAN LIVE BEACON (Paseo de la Reforma / Rio Lerma) */}
          <g transform="translate(440, 400)" className="tech-beacon-marker" filter="url(#cleanCardShadow)">
            <circle cx="0" cy="0" r="22" fill="#0284c7" opacity="0.2" className="beacon-pulse-circle" />
            <circle cx="0" cy="0" r="13" fill="#0284c7" opacity="0.3" />
            <circle cx="0" cy="0" r="7.5" fill="#0284c7" stroke="#ffffff" strokeWidth="2.5" />
            <polygon points="0,-10 3.5,-4 -3.5,-4" fill="#ffffff" />
            {/* Clean White Floating Label */}
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

          {/* STOP 1 PIN: INDIRANAGAR / SAN RAFAEL (Arun Kumar - Urgent Inverter E-04) */}
          <g
            transform="translate(560, 200)"
            className={`map-pin-item ${selectedStopId === 'stop-1' ? 'active-pin' : ''}`}
            onClick={() => setSelectedStopId('stop-1')}
            filter="url(#cleanCardShadow)"
          >
            <circle cx="0" cy="0" r="20" fill="#ef4444" opacity="0.22" className="beacon-pulse-circle" />
            <path
              d="M0 -26 C-9 -26 -16 -19 -16 -10 C-16 3 0 16 0 16 C0 16 16 3 16 -10 C16 -19 9 -26 0 -26 Z"
              fill="#ea4335"
              stroke="#ffffff"
              strokeWidth="2"
            />
            <circle cx="0" cy="-10" r="4.5" fill="#ffffff" />
            {/* Clean White Floating Tooltip */}
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

          {/* STOP 2 PIN: DODDANEKKUNDI / TABACALERA (Villa 12) */}
          <g
            transform="translate(710, 240)"
            className={`map-pin-item ${selectedStopId === 'stop-2' ? 'active-pin' : ''}`}
            onClick={() => setSelectedStopId('stop-2')}
            filter="url(#cleanCardShadow)"
          >
            <circle cx="0" cy="0" r="16" fill="#0284c7" opacity="0.2" />
            <path
              d="M0 -24 C-8 -24 -14 -18 -14 -10 C-14 3 0 15 0 15 C0 15 14 3 14 -10 C14 -18 8 -24 0 -24 Z"
              fill="#1a73e8"
              stroke="#ffffff"
              strokeWidth="2"
            />
            <circle cx="0" cy="-10" r="4" fill="#ffffff" />
            <rect
              x="-72"
              y="-52"
              width="144"
              height="22"
              rx="11"
              fill="#ffffff"
              stroke="#1a73e8"
              strokeWidth="1.2"
            />
            <text x="0" y="-37" fill="#1e40af" fontSize="10" fontWeight="700" textAnchor="middle">
              Villa 12 · Structure Markings
            </text>
          </g>

          {/* STOP 3 PIN: WHITEFIELD / BALDERAS HUB (TechSpark) */}
          <g
            transform="translate(870, 310)"
            className={`map-pin-item ${selectedStopId === 'stop-3' ? 'active-pin' : ''}`}
            onClick={() => setSelectedStopId('stop-3')}
            filter="url(#cleanCardShadow)"
          >
            <circle cx="0" cy="0" r="16" fill="#9333ea" opacity="0.2" />
            <path
              d="M0 -24 C-8 -24 -14 -18 -14 -10 C-14 3 0 15 0 15 C0 15 14 3 14 -10 C14 -18 8 -24 0 -24 Z"
              fill="#9333ea"
              stroke="#ffffff"
              strokeWidth="2"
            />
            <circle cx="0" cy="-10" r="4" fill="#ffffff" />
            <rect
              x="-78"
              y="-52"
              width="156"
              height="22"
              rx="11"
              fill="#ffffff"
              stroke="#9333ea"
              strokeWidth="1.2"
            />
            <text x="0" y="-37" fill="#6b21a8" fontSize="10" fontWeight="700" textAnchor="middle">
              TechSpark · 10kW Commercial DB
            </text>
          </g>
        </svg>

        {/* Clean Frost HUD Overlay */}
        <div className="tech-map-hud-row">
          <div className="map-hud-chip">
            <Compass size={14} color="#0284c7" />
            <span>NE · Heading 042° Straight</span>
          </div>
          <div className="map-hud-chip next-step">
            <Navigation size={14} color="#059669" />
            <span>{activeStop.nextTurn}</span>
          </div>
          <div className="map-hud-chip">
            <span className="live-traffic-circle" />
            <span>{activeStop.traffic}</span>
          </div>
          <div className="map-hud-chip speed-chip">
            <span>42 km/h</span>
          </div>
        </div>
      </div>

      {/* Selected Customer Site Action Panel in Dashboard Theme */}
      <div className="tech-map-action-panel">
        <div className="site-details-column">
          <div className="site-badges-row">
            <span className="badge-urgent-tag">
              <AlertTriangle size={12} />
              <span>{activeStop.issueType}</span>
            </span>
            <span className="badge-meta-pill">{activeStop.workOrderId}</span>
            <span className="badge-meta-pill">{activeStop.systemSize}</span>
            <span className="badge-eta-pill">
              <Clock size={12} />
              <span>{activeStop.distance} · {activeStop.eta} away</span>
            </span>
          </div>

          <h4 className="site-customer-heading">
            <span>{activeStop.customerName}</span>
            <span className="slot-subtitle">({activeStop.scheduledSlot})</span>
          </h4>

          <div className="site-address-line">
            <MapPin size={14} color="#64748b" className="flex-shrink-0" />
            <span>{activeStop.address}</span>
          </div>

          <div className="site-directive-card">
            <strong>Rectification Directive:</strong> {activeStop.problemDescription}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="site-actions-column">
          <button
            type="button"
            className="panel-btn primary"
            onClick={() => handleStartNavigation(activeStop)}
          >
            <Navigation size={15} />
            <span>Start GPS Navigation</span>
            <ExternalLink size={13} opacity={0.7} />
          </button>

          <a
            href={`tel:${activeStop.phone}`}
            className="panel-btn secondary"
            title="Call Customer"
          >
            <Phone size={15} />
            <span>Call Customer</span>
          </a>

          <button
            type="button"
            className={`panel-btn ${isArrived ? 'verified' : 'checkin'}`}
            onClick={() => handleMarkArrived(activeStop.id)}
          >
            {isArrived ? (
              <>
                <CheckCircle2 size={15} color="#059669" />
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
