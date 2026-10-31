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
} from 'lucide-react';
import { useRouter } from '../../router/Router';
import './TechnicianSiteMap.css';

export const STOPS = [
  {
    id: 'stop-1',
    customerName: 'Arun Kumar',
    systemSize: '5 kW Hybrid Bifacial',
    area: 'Indiranagar',
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
    lat: 12.9784,
    lng: 77.6408,
    status: 'en_route',
  },
  {
    id: 'stop-2',
    customerName: 'Arun Kumar (Villa)',
    systemSize: '3 kW Hybrid System',
    area: 'Doddanekkundi',
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
    lat: 12.9698,
    lng: 77.6984,
    status: 'scheduled',
  },
  {
    id: 'stop-3',
    customerName: 'TechSpark Innovation Labs (Rajesh Mehra)',
    systemSize: '10 kW Commercial 3-Phase',
    area: 'Whitefield',
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
    lat: 12.9863,
    lng: 77.7346,
    status: 'scheduled',
  },
];

export function TechnicianSiteMap({ onCheckIn, onToast, isStandalone = false }) {
  const { navigate } = useRouter();
  const [selectedStopId, setSelectedStopId] = useState('stop-1');
  const [arrivedStops, setArrivedStops] = useState({});

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
      className={`tech-map-dark-container ${isStandalone ? 'standalone-mode' : ''}`}
      aria-label="Field Technician Customer Site Map"
    >
      {/* Header Bar */}
      <div className="tech-dark-header">
        <div>
          <div className="tech-dark-title-row">
            <Navigation size={18} color="#38bdf8" />
            <h3 className="tech-dark-title">Field Dispatch & Navigation Map</h3>
            <span className="dark-theme-badge">Dark Grid Navigation</span>
          </div>
          <span className="tech-dark-subtitle">
            Turn-by-turn street routing to customer premises for on-site diagnosis and fault rectification.
          </span>
        </div>

        <div className="tech-dark-header-actions">
          <div className="tech-dark-stats">
            <span className="dark-stat-chip">
              <Car size={13} color="#38bdf8" />
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

      {/* Dark Theme Vector Map Canvas */}
      <div className="tech-dark-map-viewport">
        <svg
          className="tech-dark-vector-map-svg"
          viewBox="0 0 1000 460"
          preserveAspectRatio="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            {/* Dark background pattern */}
            <pattern id="dark_grid_mesh" width="30" height="30" patternUnits="userSpaceOnUse">
              <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#131b2c" strokeWidth="0.8" />
            </pattern>

            {/* Glowing route stroke filter */}
            <filter id="neonRouteGlow" x="-30%" y="-30%" width="160%" height="160%">
              <feDropShadow dx="0" dy="0" stdDeviation="5" floodColor="#38bdf8" floodOpacity="0.85" />
              <feDropShadow dx="0" dy="0" stdDeviation="10" floodColor="#0284c7" floodOpacity="0.5" />
            </filter>

            {/* Bridge shadow */}
            <filter id="overpassShadow" x="-10%" y="-10%" width="120%" height="120%">
              <feDropShadow dx="0" dy="3" stdDeviation="3" floodColor="#000000" floodOpacity="0.7" />
            </filter>
          </defs>

          {/* Deep Navy/Black Canvas Base */}
          <rect width="1000" height="460" fill="#0b0f17" />
          <rect width="1000" height="460" fill="url(#dark_grid_mesh)" opacity="0.6" />

          {/* Urban Landuse & City Blocks (Straight Orthogonal Blocks) */}
          <g fill="#101726" stroke="#162035" strokeWidth="1">
            <rect x="50" y="50" width="100" height="55" rx="3" />
            <rect x="50" y="125" width="100" height="75" rx="3" />
            <rect x="50" y="240" width="100" height="85" rx="3" />
            <rect x="50" y="345" width="100" height="75" rx="3" />

            {/* Indiranagar Blocks */}
            <rect x="180" y="50" width="135" height="60" rx="3" />
            <rect x="180" y="145" width="135" height="55" rx="3" />
            <rect x="180" y="240" width="135" height="85" rx="3" />
            <rect x="180" y="345" width="135" height="75" rx="3" />

            <rect x="360" y="50" width="115" height="60" rx="3" />
            <rect x="360" y="145" width="115" height="55" rx="3" />
            <rect x="360" y="240" width="115" height="85" rx="3" />
            <rect x="360" y="345" width="115" height="75" rx="3" />

            {/* Central Corridor Blocks */}
            <rect x="495" y="50" width="105" height="60" rx="3" />
            <rect x="495" y="145" width="105" height="55" rx="3" />
            <rect x="495" y="240" width="105" height="85" rx="3" />

            {/* East Corridor / Doddanekkundi Blocks */}
            <rect x="640" y="50" width="170" height="70" rx="3" />
            <rect x="640" y="140" width="170" height="60" rx="3" />
            <rect x="640" y="240" width="170" height="55" rx="3" />
            <rect x="640" y="325" width="170" height="95" rx="3" />

            {/* Whitefield Blocks */}
            <rect x="860" y="50" width="105" height="65" rx="3" />
            <rect x="860" y="145" width="105" height="65" rx="3" />
            <rect x="860" y="235" width="105" height="80" rx="3" />
            <rect x="860" y="335" width="105" height="85" rx="3" />
          </g>

          {/* Water Bodies (Deep Navy/Slate Reservoirs with Subtle Edge) */}
          {/* Ulsoor Lake */}
          <path
            d="M 60 55 C 100 45, 140 50, 155 85 C 165 115, 135 140, 95 130 C 65 120, 50 90, 60 55 Z"
            fill="#0e1726"
            stroke="#1e2c45"
            strokeWidth="1.5"
          />
          <text x="85" y="95" fill="#38bdf8" fontSize="10" fontWeight="600" opacity="0.6">
            Ulsoor Lake
          </text>

          {/* Bellandur Lake */}
          <path
            d="M 500 340 C 560 330, 650 340, 680 375 C 690 415, 610 435, 550 430 C 480 425, 470 370, 500 340 Z"
            fill="#0e1726"
            stroke="#1e2c45"
            strokeWidth="1.5"
          />
          <text x="545" y="390" fill="#38bdf8" fontSize="10" fontWeight="600" opacity="0.6">
            Bellandur Lake
          </text>

          {/* STRAIGHT CITY STREET NETWORK */}

          {/* Minor Straight Cross-Streets (Dark Slate Grid) */}
          <g stroke="#1a2438" strokeWidth="2" strokeLinecap="square">
            <line x1="40" y1="90" x2="960" y2="90" />
            <line x1="40" y1="175" x2="960" y2="175" />
            <line x1="40" y1="270" x2="960" y2="270" />
            <line x1="40" y1="365" x2="960" y2="365" />

            <line x1="120" y1="40" x2="120" y2="420" />
            <line x1="240" y1="40" x2="240" y2="420" />
            <line x1="420" y1="40" x2="420" y2="420" />
            <line x1="550" y1="40" x2="550" y2="420" />
            <line x1="720" y1="40" x2="720" y2="420" />
            <line x1="910" y1="40" x2="910" y2="420" />
          </g>

          {/* MAJOR STRAIGHT ARTERIAL CORRIDORS (Dual Lines with Dark Divider) */}

          {/* 1. Old Airport Road (Straight Horizontal East-West Trunk Route) */}
          <g>
            <line x1="40" y1="220" x2="960" y2="220" stroke="#162032" strokeWidth="16" />
            <line x1="40" y1="220" x2="960" y2="220" stroke="#25354e" strokeWidth="8" />
            <line x1="40" y1="220" x2="960" y2="220" stroke="#0b0f17" strokeWidth="1" strokeDasharray="6 8" />
          </g>

          {/* 2. CMH Road / Metro Line (Straight Horizontal East-West) */}
          <g>
            <line x1="140" y1="130" x2="540" y2="130" stroke="#162032" strokeWidth="12" />
            <line x1="140" y1="130" x2="540" y2="130" stroke="#25354e" strokeWidth="6" />
          </g>

          {/* 3. Indiranagar 100 Feet Road (Straight Orthogonal Vertical North-South) */}
          <g>
            <line x1="340" y1="40" x2="340" y2="420" stroke="#162032" strokeWidth="14" />
            <line x1="340" y1="40" x2="340" y2="420" stroke="#2a3d59" strokeWidth="7" />
            <line x1="340" y1="40" x2="340" y2="420" stroke="#0b0f17" strokeWidth="1" strokeDasharray="6 8" />
          </g>

          {/* 4. Outer Ring Road (ORR) Expressway (Straight Vertical North-South Elevated Corridor) */}
          <g filter="url(#overpassShadow)">
            <line x1="620" y1="40" x2="620" y2="420" stroke="#111a29" strokeWidth="18" />
            <line x1="620" y1="40" x2="620" y2="420" stroke="#334768" strokeWidth="10" />
            <line x1="620" y1="40" x2="620" y2="420" stroke="#0b0f17" strokeWidth="1.5" strokeDasharray="8 6" />
          </g>

          {/* 5. ITPL Main Road Whitefield (Straight Vertical North-South) */}
          <g>
            <line x1="840" y1="40" x2="840" y2="420" stroke="#162032" strokeWidth="14" />
            <line x1="840" y1="40" x2="840" y2="420" stroke="#25354e" strokeWidth="7" />
          </g>

          {/* 6. HAL Varthur Main Road (Straight Horizontal Link) */}
          <g>
            <line x1="340" y1="310" x2="960" y2="310" stroke="#162032" strokeWidth="12" />
            <line x1="340" y1="310" x2="960" y2="310" stroke="#25354e" strokeWidth="6" />
          </g>

          {/* ORR Flyover Overpass Intersection at Old Airport Road */}
          <rect x="608" y="208" width="24" height="24" fill="#334768" stroke="#475569" strokeWidth="1.5" rx="3" filter="url(#overpassShadow)" />

          {/* Directional One-Way Flow Arrows on Streets */}
          <g fill="#475569" fontSize="9" fontWeight="700">
            <text x="220" y="217">&gt;</text>
            <text x="280" y="217">&gt;</text>
            <text x="440" y="217">&gt;</text>
            <text x="520" y="217">&gt;</text>
            <text x="740" y="217">&gt;</text>

            <text x="337" y="100">^</text>
            <text x="337" y="170">^</text>
            <text x="337" y="260">v</text>
            <text x="337" y="350">v</text>

            <text x="617" y="110">^</text>
            <text x="617" y="160">^</text>
            <text x="617" y="280">v</text>
            <text x="617" y="360">v</text>
          </g>

          {/* Street & Landmark Text Labels (Muted Slate) */}
          <text x="355" y="70" fill="#94a3b8" fontSize="11" fontWeight="700" letterSpacing="0.04em">
            100 FT RD · INDIRANAGAR
          </text>
          <text x="635" y="75" fill="#94a3b8" fontSize="11" fontWeight="700" letterSpacing="0.04em">
            OUTER RING ROAD (ORR)
          </text>
          <text x="855" y="75" fill="#94a3b8" fontSize="11" fontWeight="700" letterSpacing="0.04em">
            ITPL MAIN RD · WHITEFIELD
          </text>
          <text x="180" y="210" fill="#64748b" fontSize="10" fontWeight="600">
            Old Airport Road
          </text>
          <text x="635" y="300" fill="#64748b" fontSize="10" fontWeight="600">
            Doddanekkundi
          </text>

          {/* Transit Metro Station Tokens (M) matching the reference (T) icon badges */}
          <g transform="translate(180, 130)">
            <circle cx="0" cy="0" r="7.5" fill="#0b0f17" stroke="#ffffff" strokeWidth="1.5" />
            <text x="0" y="3" fill="#ffffff" fontSize="7.5" fontWeight="900" textAnchor="middle">M</text>
            <text x="12" y="3" fill="#cbd5e1" fontSize="10" fontWeight="600">Halasuru</text>
          </g>

          <g transform="translate(340, 130)">
            <circle cx="0" cy="0" r="7.5" fill="#0b0f17" stroke="#ffffff" strokeWidth="1.5" />
            <text x="0" y="3" fill="#ffffff" fontSize="7.5" fontWeight="900" textAnchor="middle">M</text>
            <text x="12" y="3" fill="#cbd5e1" fontSize="10" fontWeight="600">Indiranagar</text>
          </g>

          <g transform="translate(500, 130)">
            <circle cx="0" cy="0" r="7.5" fill="#0b0f17" stroke="#ffffff" strokeWidth="1.5" />
            <text x="0" y="3" fill="#ffffff" fontSize="7.5" fontWeight="900" textAnchor="middle">M</text>
            <text x="12" y="3" fill="#cbd5e1" fontSize="10" fontWeight="600">Baiyappanahalli</text>
          </g>

          <g transform="translate(840, 130)">
            <circle cx="0" cy="0" r="7.5" fill="#0b0f17" stroke="#ffffff" strokeWidth="1.5" />
            <text x="0" y="3" fill="#ffffff" fontSize="7.5" fontWeight="900" textAnchor="middle">M</text>
            <text x="12" y="3" fill="#cbd5e1" fontSize="10" fontWeight="600">ITPL</text>
          </g>

          {/* ACTIVE GPS NAVIGATION ROUTE (Clean, straight street routing with 90-degree corner turns!) */}
          {activeStop.id === 'stop-1' && (
            <path
              d="M 180 220 L 340 220 L 340 130"
              fill="none"
              stroke="#38bdf8"
              strokeWidth="5"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="9 5"
              className="anim-dark-gps-route"
              filter="url(#neonRouteGlow)"
            />
          )}

          {activeStop.id === 'stop-2' && (
            <path
              d="M 180 220 L 620 220 L 620 310"
              fill="none"
              stroke="#38bdf8"
              strokeWidth="5"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="9 5"
              className="anim-dark-gps-route"
              filter="url(#neonRouteGlow)"
            />
          )}

          {activeStop.id === 'stop-3' && (
            <path
              d="M 180 220 L 620 220 L 840 220 L 840 130"
              fill="none"
              stroke="#38bdf8"
              strokeWidth="5"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="9 5"
              className="anim-dark-gps-route"
              filter="url(#neonRouteGlow)"
            />
          )}

          {/* TECHNICIAN LIVE GPS BEACON (At Base / Indiranagar Old Airport Rd) */}
          <g transform="translate(180, 220)" className="dark-beacon-group">
            <circle cx="0" cy="0" r="26" fill="#38bdf8" opacity="0.22" className="beacon-radar-wave" />
            <circle cx="0" cy="0" r="15" fill="#0284c7" opacity="0.35" />
            <circle cx="0" cy="0" r="8.5" fill="#38bdf8" stroke="#ffffff" strokeWidth="2.5" />
            <rect x="-70" y="-36" width="140" height="22" rx="11" fill="#030712" stroke="#38bdf8" strokeWidth="1" opacity="0.95" />
            <text x="0" y="-22" fill="#38bdf8" fontSize="10" fontWeight="700" textAnchor="middle">
              Technician Live (Karthik)
            </text>
          </g>

          {/* STOP 1 PIN: INDIRANAGAR (Arun Kumar - Urgent Inverter E-04) */}
          <g
            transform="translate(340, 130)"
            className={`dark-marker-pin ${selectedStopId === 'stop-1' ? 'active-pin' : ''}`}
            onClick={() => setSelectedStopId('stop-1')}
          >
            <circle cx="0" cy="0" r="22" fill="#ef4444" opacity="0.22" className="marker-sonar-pulse" />
            <path
              d="M0 -26 C-9 -26 -16 -19 -16 -10 C-16 2 0 16 0 16 C0 16 16 2 16 -10 C16 -19 9 -26 0 -26 Z"
              fill="#ef4444"
              stroke="#ffffff"
              strokeWidth="2"
            />
            <circle cx="0" cy="-10" r="4.5" fill="#ffffff" />
            <rect x="-72" y="-56" width="144" height="24" rx="12" fill="#030712" stroke="#ef4444" strokeWidth="1" opacity="0.95" />
            <text x="0" y="-40" fill="#ffffff" fontSize="10.5" fontWeight="800" textAnchor="middle">
              Arun Kumar · E-04 Red LED
            </text>
          </g>

          {/* STOP 2 PIN: DODDANEKKUNDI (Villa 12 - Pre-Install Survey) */}
          <g
            transform="translate(620, 310)"
            className={`dark-marker-pin ${selectedStopId === 'stop-2' ? 'active-pin' : ''}`}
            onClick={() => setSelectedStopId('stop-2')}
          >
            <circle cx="0" cy="0" r="18" fill="#38bdf8" opacity="0.18" />
            <path
              d="M0 -24 C-8 -24 -14 -18 -14 -10 C-14 2 0 15 0 15 C0 15 14 2 14 -10 C14 -18 8 -24 0 -24 Z"
              fill="#0284c7"
              stroke="#ffffff"
              strokeWidth="2"
            />
            <circle cx="0" cy="-10" r="4" fill="#ffffff" />
            <rect x="-65" y="-52" width="130" height="22" rx="11" fill="#030712" stroke="#0284c7" strokeWidth="1" opacity="0.92" />
            <text x="0" y="-37" fill="#ffffff" fontSize="10" fontWeight="700" textAnchor="middle">
              Villa 12 · Anchor Pull Test
            </text>
          </g>

          {/* STOP 3 PIN: WHITEFIELD (TechSpark - Commercial 3-Phase DB) */}
          <g
            transform="translate(840, 130)"
            className={`dark-marker-pin ${selectedStopId === 'stop-3' ? 'active-pin' : ''}`}
            onClick={() => setSelectedStopId('stop-3')}
          >
            <circle cx="0" cy="0" r="18" fill="#a855f7" opacity="0.18" />
            <path
              d="M0 -24 C-8 -24 -14 -18 -14 -10 C-14 2 0 15 0 15 C0 15 14 2 14 -10 C14 -18 8 -24 0 -24 Z"
              fill="#9333ea"
              stroke="#ffffff"
              strokeWidth="2"
            />
            <circle cx="0" cy="-10" r="4" fill="#ffffff" />
            <rect x="-70" y="-52" width="140" height="22" rx="11" fill="#030712" stroke="#9333ea" strokeWidth="1" opacity="0.92" />
            <text x="0" y="-37" fill="#ffffff" fontSize="10" fontWeight="700" textAnchor="middle">
              TechSpark · 10kW 3-Phase
            </text>
          </g>
        </svg>

        {/* Live Navigation Heads-Up Display (Dark Glassmorphic HUD) */}
        <div className="tech-dark-hud-overlay">
          <div className="dark-hud-chip">
            <Compass size={14} color="#38bdf8" />
            <span>North · Heading 000° Straight</span>
          </div>
          <div className="dark-hud-chip next-step">
            <Navigation size={14} color="#10b981" />
            <span>In 250m: Turn North onto 100 Feet Rd</span>
          </div>
          <div className="dark-hud-chip">
            <span className="traffic-live-dot" />
            <span>{activeStop.traffic}</span>
          </div>
        </div>
      </div>

      {/* Selected Customer Site Action Panel (Dark Theme) */}
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
            <MapPin size={14} color="#94a3b8" className="flex-shrink-0" />
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
