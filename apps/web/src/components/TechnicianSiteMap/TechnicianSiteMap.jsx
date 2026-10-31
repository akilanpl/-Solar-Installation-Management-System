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
} from 'lucide-react';
import './TechnicianSiteMap.css';

const STOPS = [
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
    coordinates: { x: 38, y: 44 }, // Percentage coordinates on vector map
    lat: 12.9784,
    lng: 77.6408,
    status: 'en_route', // 'en_route' | 'on_site' | 'completed'
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
    coordinates: { x: 62, y: 55 },
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
    coordinates: { x: 86, y: 35 },
    lat: 12.9863,
    lng: 77.7346,
    status: 'scheduled',
  },
];

export function TechnicianSiteMap({ onCheckIn, onToast }) {
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
        title: 'GPS Turn-by-Turn Activated',
        message: `Routing to ${stop.customerName} in ${stop.area} (${stop.distance}, ${stop.eta}).`,
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
    <div className="bento-card tech-map-container" aria-label="Field Technician Customer Site Map">
      {/* Header Bar */}
      <div className="tech-map-header">
        <div>
          <div className="tech-map-title-row">
            <Navigation size={18} color="#2563eb" />
            <h3 className="bento-card-title">Field Dispatch & Customer Site Map</h3>
          </div>
          <span className="tech-map-subtitle">
            Real-time GPS routing to customer premises for on-site surveys and fault rectification.
          </span>
        </div>

        <div className="tech-map-stats-badges">
          <span className="route-stat-chip">
            <Car size={13} color="#2563eb" />
            <span>3 Stops Today · 23.4 km</span>
          </span>
          <span className="live-gps-pill">
            <span className="live-dot" />
            <span>GPS Tracking Live</span>
          </span>
        </div>
      </div>

      {/* Stop Selection Tabs */}
      <div className="tech-stop-pills-row" role="tablist">
        {STOPS.map((stop, index) => {
          const isSelected = stop.id === selectedStopId;
          const stopArrived = arrivedStops[stop.id];

          return (
            <button
              key={stop.id}
              type="button"
              role="tab"
              aria-selected={isSelected}
              className={`tech-stop-pill ${isSelected ? 'active' : ''} ${
                stopArrived ? 'arrived' : ''
              }`}
              onClick={() => setSelectedStopId(stop.id)}
            >
              <div className="stop-pill-number">
                {stopArrived ? '✓' : index + 1}
              </div>
              <div className="stop-pill-info">
                <span className="stop-pill-area">{stop.area}</span>
                <span className="stop-pill-cust">
                  {stop.customerName.split(' ')[0]} · {stop.distance}
                </span>
              </div>
              {stop.priority === 'Urgent' && (
                <span className="urgent-indicator-dot" title="Urgent Inverter Alarm" />
              )}
            </button>
          );
        })}
      </div>

      {/* Interactive Map Visual Area */}
      <div className="tech-map-viewport">
        {/* SVG Vector Map of Bengaluru (HAL, Indiranagar, ORR, Whitefield) */}
        <svg
          className="tech-vector-map-svg"
          viewBox="0 0 1000 480"
          preserveAspectRatio="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            {/* Background Grid Pattern */}
            <pattern id="map_grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#f1f5f9" strokeWidth="1" />
            </pattern>

            {/* Glowing route stroke filter */}
            <filter id="routeGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#2563eb" floodOpacity="0.45" />
            </filter>
          </defs>

          {/* Map Base Canvas */}
          <rect width="1000" height="480" fill="#f8fafc" />
          <rect width="1000" height="480" fill="url(#map_grid)" opacity="0.8" />

          {/* Water Bodies & Lake Reservoirs */}
          <path
            d="M120,80 C150,60 210,70 230,110 C240,150 180,180 140,160 C100,140 100,100 120,80 Z"
            fill="#dbeafe"
            stroke="#93c5fd"
            strokeWidth="1.5"
          />
          <text x="145" y="125" fill="#3b82f6" fontSize="11" fontWeight="600" opacity="0.75">
            Ulsoor Lake
          </text>

          <path
            d="M520,320 C580,310 660,340 680,390 C690,440 610,460 560,450 C490,430 480,350 520,320 Z"
            fill="#dbeafe"
            stroke="#93c5fd"
            strokeWidth="1.5"
          />
          <text x="560" y="390" fill="#3b82f6" fontSize="11" fontWeight="600" opacity="0.75">
            Bellandur Lake
          </text>

          {/* Major Bengaluru Road Arteries */}
          {/* Outer Ring Road (ORR) */}
          <path
            d="M150,470 C280,380 480,360 620,300 C740,240 850,160 960,60"
            fill="none"
            stroke="#e2e8f0"
            strokeWidth="16"
            strokeLinecap="round"
          />
          <path
            d="M150,470 C280,380 480,360 620,300 C740,240 850,160 960,60"
            fill="none"
            stroke="#cbd5e1"
            strokeWidth="6"
            strokeLinecap="round"
          />

          {/* Old Airport Road & 100ft Road Indiranagar */}
          <path
            d="M50,260 C200,240 380,210 550,250 C700,290 850,220 980,180"
            fill="none"
            stroke="#e2e8f0"
            strokeWidth="12"
            strokeLinecap="round"
          />
          <path
            d="M50,260 C200,240 380,210 550,250 C700,290 850,220 980,180"
            fill="none"
            stroke="#cbd5e1"
            strokeWidth="4"
            strokeLinecap="round"
          />

          {/* Indiranagar 100 Feet Cross Road */}
          <path
            d="M380,50 L380,380"
            fill="none"
            stroke="#e2e8f0"
            strokeWidth="10"
            strokeLinecap="round"
          />
          <path
            d="M380,50 L380,380"
            fill="none"
            stroke="#cbd5e1"
            strokeWidth="3.5"
            strokeLinecap="round"
          />

          {/* Secondary Arteries & Neighborhood Grids */}
          <path
            d="M200,100 L550,100 M620,180 L920,180 M280,260 L280,450 M620,120 L620,420"
            fill="none"
            stroke="#f1f5f9"
            strokeWidth="4"
          />

          {/* Highway & Area Text Labels */}
          <text x="390" y="90" fill="#64748b" fontSize="12" fontWeight="700">
            100 FT RD · INDIRANAGAR
          </text>
          <text x="590" y="235" fill="#64748b" fontSize="12" fontWeight="700">
            OUTER RING ROAD
          </text>
          <text x="810" y="160" fill="#64748b" fontSize="12" fontWeight="700">
            ITPL · WHITEFIELD
          </text>
          <text x="640" y="340" fill="#64748b" fontSize="11" fontWeight="600">
            Doddanekkundi
          </text>

          {/* ACTIVE DISPATCH ROUTE (Technician Current Position -> Selected Destination) */}
          {activeStop.id === 'stop-1' && (
            <path
              d="M180,320 C240,280 320,260 380,210"
              fill="none"
              stroke="#2563eb"
              strokeWidth="5"
              strokeLinecap="round"
              strokeDasharray="8 6"
              className="anim-active-route-path"
              filter="url(#routeGlow)"
            />
          )}

          {activeStop.id === 'stop-2' && (
            <path
              d="M180,320 C280,290 450,270 620,264"
              fill="none"
              stroke="#2563eb"
              strokeWidth="5"
              strokeLinecap="round"
              strokeDasharray="8 6"
              className="anim-active-route-path"
              filter="url(#routeGlow)"
            />
          )}

          {activeStop.id === 'stop-3' && (
            <path
              d="M180,320 C350,280 600,240 860,168"
              fill="none"
              stroke="#2563eb"
              strokeWidth="5"
              strokeLinecap="round"
              strokeDasharray="8 6"
              className="anim-active-route-path"
              filter="url(#routeGlow)"
            />
          )}

          {/* TECHNICIAN CURRENT GPS LOCATION BEACON */}
          <g transform="translate(180, 320)" className="tech-beacon-group">
            <circle cx="0" cy="0" r="22" fill="#3b82f6" opacity="0.25" className="beacon-pulse-ring" />
            <circle cx="0" cy="0" r="14" fill="#2563eb" opacity="0.35" />
            <circle cx="0" cy="0" r="8" fill="#1d4ed8" stroke="#ffffff" strokeWidth="2.5" />
            <text x="14" y="5" fill="#1e40af" fontSize="11" fontWeight="700">
              Technician Live (Karthik Raja)
            </text>
          </g>

          {/* STOP 1 PIN: INDIRANAGAR (Arun Kumar) */}
          <g
            transform="translate(380, 210)"
            className={`map-marker-group ${selectedStopId === 'stop-1' ? 'selected' : ''}`}
            onClick={() => setSelectedStopId('stop-1')}
          >
            <circle cx="0" cy="0" r="18" fill="#ef4444" opacity="0.2" className="marker-ripple" />
            <path
              d="M0 -24 C-8 -24 -14 -18 -14 -10 C-14 2 0 16 0 16 C0 16 14 2 14 -10 C14 -18 8 -24 0 -24 Z"
              fill="#ef4444"
              stroke="#ffffff"
              strokeWidth="2"
            />
            <circle cx="0" cy="-10" r="4.5" fill="#ffffff" />
            <rect x="-65" y="-52" width="130" height="24" rx="12" fill="#111827" opacity="0.92" />
            <text x="0" y="-36" fill="#ffffff" fontSize="10.5" fontWeight="700" textAnchor="middle">
              Arun Kumar (Red LED)
            </text>
          </g>

          {/* STOP 2 PIN: DODDANEKKUNDI (Villa 12) */}
          <g
            transform="translate(620, 264)"
            className={`map-marker-group ${selectedStopId === 'stop-2' ? 'selected' : ''}`}
            onClick={() => setSelectedStopId('stop-2')}
          >
            <circle cx="0" cy="0" r="16" fill="#3b82f6" opacity="0.18" />
            <path
              d="M0 -22 C-7 -22 -12 -17 -12 -9 C-12 2 0 14 0 14 C0 14 12 2 12 -9 C12 -17 7 -22 0 -22 Z"
              fill="#2563eb"
              stroke="#ffffff"
              strokeWidth="2"
            />
            <circle cx="0" cy="-9" r="4" fill="#ffffff" />
            <rect x="-60" y="-48" width="120" height="22" rx="11" fill="#111827" opacity="0.88" />
            <text x="0" y="-33" fill="#ffffff" fontSize="10" fontWeight="600" textAnchor="middle">
              Villa 12 · 3kW Survey
            </text>
          </g>

          {/* STOP 3 PIN: WHITEFIELD (TechSpark) */}
          <g
            transform="translate(860, 168)"
            className={`map-marker-group ${selectedStopId === 'stop-3' ? 'selected' : ''}`}
            onClick={() => setSelectedStopId('stop-3')}
          >
            <circle cx="0" cy="0" r="16" fill="#8b5cf6" opacity="0.18" />
            <path
              d="M0 -22 C-7 -22 -12 -17 -12 -9 C-12 2 0 14 0 14 C0 14 12 2 12 -9 C12 -17 7 -22 0 -22 Z"
              fill="#7c3aed"
              stroke="#ffffff"
              strokeWidth="2"
            />
            <circle cx="0" cy="-9" r="4" fill="#ffffff" />
            <rect x="-68" y="-48" width="136" height="22" rx="11" fill="#111827" opacity="0.88" />
            <text x="0" y="-33" fill="#ffffff" fontSize="10" fontWeight="600" textAnchor="middle">
              TechSpark · 10kW Wiring
            </text>
          </g>
        </svg>

        {/* Live Navigation Heads-Up Display (HUD) */}
        <div className="tech-map-hud-overlay">
          <div className="hud-compass-chip">
            <Compass size={14} color="#2563eb" />
            <span>Northeast · Heading 042°</span>
          </div>
          <div className="hud-next-turn">
            <Navigation size={14} color="#10b981" />
            <span>In 350m: Turn Right onto 100 Feet Rd</span>
          </div>
          <div className="hud-traffic-pill">
            <span className="traffic-dot" />
            <span>{activeStop.traffic}</span>
          </div>
        </div>
      </div>

      {/* Selected Customer Site Action Panel */}
      <div className="tech-site-action-card">
        <div className="site-details-col">
          <div className="site-tag-row">
            <span className="priority-badge-urgent">
              <AlertTriangle size={12} />
              <span>{activeStop.issueType}</span>
            </span>
            <span className="tag-badge">{activeStop.workOrderId}</span>
            <span className="tag-badge">{activeStop.systemSize}</span>
            <span className="site-eta-badge">
              <Clock size={12} />
              <span>
                {activeStop.distance} · {activeStop.eta} away
              </span>
            </span>
          </div>

          <h4 className="site-customer-title">
            <span>{activeStop.customerName}</span>
            <span className="site-slot-time">({activeStop.scheduledSlot})</span>
          </h4>

          <div className="site-address-line">
            <MapPin size={14} color="#64748b" className="flex-shrink-0" />
            <span>{activeStop.address}</span>
          </div>

          <p className="site-problem-desc">
            <strong>Rectification Directive:</strong> {activeStop.problemDescription}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="site-actions-col">
          <button
            type="button"
            className="tech-nav-action-btn primary"
            onClick={() => handleStartNavigation(activeStop)}
          >
            <Navigation size={15} />
            <span>Start GPS Navigation</span>
            <ExternalLink size={13} opacity={0.7} />
          </button>

          <a
            href={`tel:${activeStop.phone}`}
            className="tech-nav-action-btn secondary"
            title="Call Customer"
          >
            <Phone size={15} />
            <span>Call Customer</span>
          </a>

          <button
            type="button"
            className={`tech-nav-action-btn ${isArrived ? 'success' : 'outline'}`}
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

