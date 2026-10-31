import React, { useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Zap,
  Sun,
  Battery,
  Package,
  Users,
  ShieldCheck,
  Clock,
  ArrowUpRight,
  BarChart3,
  PieChart,
  Activity,
  Award,
  CheckCircle2,
  MapPin,
  Calendar,
  Download,
  RefreshCw,
  Filter,
  Sparkles,
  Layers,
  Globe,
  Sliders,
  ChevronRight,
  Info,
} from 'lucide-react';
import './AdminAnalyticsHub.css';

// ---------------------------------------------------------------------------
// DATA SETS: 12-Month Financials, Capacity, Streams, Territories, Funnel, Diurnal
// ---------------------------------------------------------------------------

const MONTHLY_FINANCIALS = [
  { month: 'Apr', revenue: 7.8, costs: 5.6, ebitda: 2.2, margin: 28.2, kw: 52 },
  { month: 'May', revenue: 8.9, costs: 6.3, ebitda: 2.6, margin: 29.2, kw: 64 },
  { month: 'Jun', revenue: 10.4, costs: 7.3, ebitda: 3.1, margin: 29.8, kw: 78 },
  { month: 'Jul', revenue: 11.2, costs: 7.9, ebitda: 3.3, margin: 29.5, kw: 82 },
  { month: 'Aug', revenue: 12.8, costs: 9.0, ebitda: 3.8, margin: 29.7, kw: 96 },
  { month: 'Sep', revenue: 13.9, costs: 9.7, ebitda: 4.2, margin: 30.2, kw: 105 },
  { month: 'Oct', revenue: 15.6, costs: 10.9, ebitda: 4.7, margin: 30.1, kw: 118 },
  { month: 'Nov', revenue: 14.8, costs: 10.4, ebitda: 4.4, margin: 29.7, kw: 110 },
  { month: 'Dec', revenue: 16.2, costs: 11.3, ebitda: 4.9, margin: 30.2, kw: 124 },
  { month: 'Jan', revenue: 13.5, costs: 9.6, ebitda: 3.9, margin: 28.9, kw: 98 },
  { month: 'Feb', revenue: 15.1, costs: 10.5, ebitda: 4.6, margin: 30.5, kw: 112 },
  { month: 'Mar', revenue: 17.8, costs: 12.4, ebitda: 5.4, margin: 30.3, kw: 135 },
];

const CAPACITY_COMPARISON = [
  { label: 'Q1 Apr-Jun', targetKw: 170, actualKw: 194, resKw: 118, commKw: 76, pct: 114 },
  { label: 'Q2 Jul-Sep', targetKw: 245, actualKw: 283, resKw: 169, commKw: 114, pct: 115 },
  { label: 'Q3 Oct-Dec', targetKw: 310, actualKw: 352, resKw: 215, commKw: 137, pct: 113 },
  { label: 'Q4 Jan-Mar (Proj)', targetKw: 320, actualKw: 345, resKw: 202, commKw: 143, pct: 108 },
];

const REVENUE_STREAMS = [
  { name: 'Residential Rooftops (3-10 kW)', value: 72.5, pct: 49, color: '#4f46e5', contracts: 382 },
  { name: 'Commercial & Industrial C&I', value: 44.4, pct: 30, color: '#059669', contracts: 48 },
  { name: 'LiFePO4 Battery Storage Add-ons', value: 17.8, pct: 12, color: '#f59e0b', contracts: 84 },
  { name: 'O&M & Annual Maintenance (AMC)', value: 8.9, pct: 6, color: '#0284c7', contracts: 412 },
  { name: 'PM Surya Ghar Portal Subsidies', value: 4.4, pct: 3, color: '#9333ea', contracts: 356 },
];

const ENTERPRISE_FUNNEL = [
  { stage: '1. Leads Ingested & Scored', count: 1420, pct: 100, drop: 0, sub: 'Portal, App & Referral inquiries' },
  { stage: '2. Feasibility Qualified', count: 1065, pct: 75.0, drop: 25.0, sub: 'Roof shadow & structural pre-check' },
  { stage: '3. Engineering Surveys Logged', count: 852, pct: 60.0, drop: 15.0, sub: 'On-site azimuth & 3D raytracing' },
  { stage: '4. Quotations & BOM Accepted', count: 681, pct: 47.9, drop: 12.1, sub: 'Advance deposit paid (20%)' },
  { stage: '5. BESCOM Sanction & Dispatch', count: 596, pct: 42.0, drop: 5.9, sub: 'DISCOM clearance & kit staging' },
  { stage: '6. Net-Metered & Commissioned', count: 512, pct: 36.1, drop: 5.9, sub: 'Bi-directional meter live' },
];

const REGIONAL_TERRITORIES = [
  { region: 'Bangalore Urban', rev: '₹58.2 L', targetRev: '₹56.0 L', kw: 380, quotaPct: 104, crews: 8, status: 'Exceeding' },
  { region: 'Bangalore Rural', rev: '₹34.5 L', targetRev: '₹37.0 L', kw: 210, quotaPct: 93, crews: 4, status: 'On Track' },
  { region: 'Mysore Division', rev: '₹26.8 L', targetRev: '₹30.0 L', kw: 145, quotaPct: 89, crews: 3, status: 'On Track' },
  { region: 'Mangalore & Coastal', rev: '₹18.4 L', targetRev: '₹19.0 L', kw: 95, quotaPct: 97, crews: 2, status: 'Exceeding' },
  { region: 'Hubli-Dharwad Circle', rev: '₹10.1 L', targetRev: '₹12.0 L', kw: 60, quotaPct: 84, crews: 2, status: 'Attention' },
];

const UNIT_ECONOMICS = [
  { component: 'Mono-PERC Tier-1 PV Modules', cost: 24300, pct: 45, color: '#4f46e5' },
  { component: 'Hybrid Inverter & Protection AC/DC DB', cost: 11880, pct: 22, color: '#06b6d4' },
  { component: 'LiFePO4 Modular Energy Storage', cost: 8640, pct: 16, color: '#f59e0b' },
  { component: 'Civil Structure, Aluminum Rails & Labour', cost: 5400, pct: 10, color: '#10b981' },
  { component: 'DISCOM Net-Meter & Permitting Fees', cost: 3780, pct: 7, color: '#8b5cf6' },
];

const DIURNAL_GENERATION = [
  { hour: '06:00', pvKw: 0.05, loadKw: 0.45, exportKw: 0.0 },
  { hour: '07:30', pvKw: 0.38, loadKw: 0.85, exportKw: 0.0 },
  { hour: '09:00', pvKw: 0.95, loadKw: 1.10, exportKw: 0.15 },
  { hour: '10:30', pvKw: 1.48, loadKw: 0.90, exportKw: 0.65 },
  { hour: '12:00', pvKw: 1.84, loadKw: 0.75, exportKw: 1.12 },
  { hour: '13:30', pvKw: 1.76, loadKw: 0.70, exportKw: 1.08 },
  { hour: '15:00', pvKw: 1.25, loadKw: 0.85, exportKw: 0.48 },
  { hour: '16:30', pvKw: 0.62, loadKw: 1.15, exportKw: 0.05 },
  { hour: '18:00', pvKw: 0.08, loadKw: 1.40, exportKw: 0.0 },
];

const WAREHOUSE_INVENTORY_MATRIX = [
  { category: 'DCR Mono-PERC PV Modules', value: '₹81.5 L', units: '142 Panels', turnover: '9.2x', health: 98, status: 'Optimal' },
  { category: 'Hybrid & Micro-Inverters', value: '₹54.3 L', units: '38 Inverters', turnover: '8.4x', health: 92, status: 'Optimal' },
  { category: 'LiFePO4 Modular Battery Packs', value: '₹34.9 L', units: '24 Units', turnover: '7.1x', health: 88, status: 'Reorder Warn' },
  { category: 'Galvanized Structures & Fasteners', value: '₹15.5 L', units: '520 Meters', turnover: '11.0x', health: 96, status: 'Optimal' },
  { category: 'Balance of System (DB, SPD, Cables)', value: '₹7.8 L', units: '45 Kits', turnover: '12.4x', health: 95, status: 'Optimal' },
];

const SLA_APPROVAL_TREND = [
  { month: 'May', bescomDays: 16.8, dbtDays: 22.0 },
  { month: 'Jun', bescomDays: 14.5, dbtDays: 19.5 },
  { month: 'Jul', bescomDays: 11.2, dbtDays: 16.8 },
  { month: 'Aug', bescomDays: 8.4, dbtDays: 14.2 },
  { month: 'Sep', bescomDays: 6.1, dbtDays: 12.8 },
  { month: 'Oct', bescomDays: 4.2, dbtDays: 11.4 },
];

export function AdminAnalyticsHub({ onExportReport = null }) {
  const [activeCategory, setActiveCategory] = useState('all'); // 'all' | 'financials' | 'ops' | 'supply' | 'sla'
  const [timeframe, setTimeframe] = useState('FY26'); // 'FY26' | 'Q2' | '30D'
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [hoveredDonut, setHoveredDonut] = useState(null);
  const [hoveredBar, setHoveredBar] = useState(null);

  // SVG Dimension constants for charts
  const areaW = 680;
  const areaH = 220;
  const paddingX = 40;
  const paddingY = 30;

  // Build Spline Path for Monthly Revenue
  const maxRevenue = 20; // 20 Lakhs
  const getCoords = (index, val) => {
    const x = paddingX + (index * (areaW - paddingX * 2)) / (MONTHLY_FINANCIALS.length - 1);
    const y = areaH - paddingY - (val / maxRevenue) * (areaH - paddingY * 2);
    return { x, y };
  };

  const pointsRev = MONTHLY_FINANCIALS.map((d, i) => getCoords(i, d.revenue));
  const pointsCosts = MONTHLY_FINANCIALS.map((d, i) => getCoords(i, d.costs));

  // Generate smooth cubic bezier SVG path
  const createSplineD = (points) => {
    if (!points.length) return '';
    let d = `M ${points[0].x} ${points[0].y}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = i > 0 ? points[i - 1] : points[i];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = i < points.length - 2 ? points[i + 2] : p2;

      const cp1x = p1.x + (p2.x - p0.x) / 6;
      const cp1y = p1.y + (p2.y - p0.y) / 6;
      const cp2x = p2.x - (p3.x - p1.x) / 6;
      const cp2y = p2.y - (p3.y - p1.y) / 6;

      d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
    }
    return d;
  };

  const splineRevD = createSplineD(pointsRev);
  const areaRevD = `${splineRevD} L ${pointsRev[pointsRev.length - 1].x} ${areaH - paddingY} L ${pointsRev[0].x} ${areaH - paddingY} Z`;
  const splineCostD = createSplineD(pointsCosts);

  // Donut SVG Math
  const donutRadius = 75;
  const donutCircumference = 2 * Math.PI * donutRadius;
  let accumulatedPct = 0;

  return (
    <div className="admin-analytics-hub">
      {/* ===================================================================
          1. HEADER & CONTROLS STRIP
          =================================================================== */}
      <div className="analytics-header-strip">
        <div className="analytics-title-group">
          <div className="analytics-live-badge">
            <span className="live-pulsing-dot" />
            <span>SolarOps Executive Telemetry · Live (18ms)</span>
          </div>
          <h2 className="analytics-main-title">Company-Wide Executive Analytics</h2>
          <p className="analytics-subtitle">
            Visualizing every operational nook and corner: revenue velocity, installation capacity, supply chain valuation,
            pipeline funnel conversions, and DISCOM grid synchronization SLAs.
          </p>
        </div>

        <div className="analytics-actions-group">
          {/* Timeframe Selector */}
          <div className="analytics-timeframe-pills">
            {['FY26', 'Q2', '30D'].map((tf) => (
              <button
                key={tf}
                type="button"
                className={`timeframe-pill-btn ${timeframe === tf ? 'active' : ''}`}
                onClick={() => setTimeframe(tf)}
              >
                {tf === 'FY26' ? 'FY 2025-26' : tf === 'Q2' ? 'Q2 Current' : 'Last 30 Days'}
              </button>
            ))}
          </div>

          {/* Export Report Action */}
          <button
            type="button"
            className="analytics-export-btn"
            onClick={onExportReport}
            title="Export Full Executive Company Performance Report"
          >
            <Download size={15} />
            <span>Export Board Report</span>
          </button>
        </div>
      </div>

      {/* ===================================================================
          2. CATEGORY TAB FILTER STRIP
          =================================================================== */}
      <div className="analytics-filter-tabs">
        {[
          { key: 'all', label: 'All Company Stats', icon: Globe },
          { key: 'financials', label: 'Financials & P&L', icon: DollarSign },
          { key: 'ops', label: 'Solar Ops & Capacity', icon: Sun },
          { key: 'supply', label: 'Supply Chain & Inventory', icon: Package },
          { key: 'sla', label: 'Grid, Permitting & CSAT', icon: ShieldCheck },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeCategory === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              className={`filter-tab-pill ${isActive ? 'active' : ''}`}
              onClick={() => setActiveCategory(tab.key)}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* ===================================================================
          3. EXECUTIVE KPI SPARKLINE STRIP (4 Mini Vector Charts)
          =================================================================== */}
      <div className="executive-kpi-grid">
        {/* KPI 1: Gross Revenue */}
        <div className="kpi-spark-card">
          <div className="kpi-spark-top">
            <span className="kpi-spark-label">Gross Revenue (YTD)</span>
            <span className="kpi-delta positive">
              <ArrowUpRight size={14} /> +28.4% YoY
            </span>
          </div>
          <div className="kpi-spark-value">₹1.48 Cr</div>
          <div className="kpi-spark-sub">Budget: ₹1.35 Cr · Target Achieved 109.6%</div>
          <div className="mini-sparkline-box">
            <svg viewBox="0 0 100 24" className="mini-sparkline-svg">
              <path
                d="M 0 20 L 10 18 L 20 15 L 30 16 L 40 12 L 50 11 L 60 8 L 70 9 L 80 5 L 90 6 L 100 2"
                fill="none"
                stroke="#4f46e5"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
          </div>
        </div>

        {/* KPI 2: Installed Solar Capacity */}
        <div className="kpi-spark-card">
          <div className="kpi-spark-top">
            <span className="kpi-spark-label">Installed Solar Capacity</span>
            <span className="kpi-delta positive">
              <ArrowUpRight size={14} /> +34.2% YoY
            </span>
          </div>
          <div className="kpi-spark-value">842.5 kW</div>
          <div className="kpi-spark-sub">512 Grid-Tied Installations Active</div>
          <div className="mini-sparkline-box">
            <svg viewBox="0 0 100 24" className="mini-sparkline-svg">
              <path
                d="M 0 22 L 15 19 L 30 16 L 45 13 L 60 10 L 75 8 L 90 4 L 100 2"
                fill="none"
                stroke="#059669"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
          </div>
        </div>

        {/* KPI 3: Net Profit Margin */}
        <div className="kpi-spark-card">
          <div className="kpi-spark-top">
            <span className="kpi-spark-label">Net Profit Margin</span>
            <span className="kpi-delta positive">
              <ArrowUpRight size={14} /> +4.1% MoM
            </span>
          </div>
          <div className="kpi-spark-value">29.3%</div>
          <div className="kpi-spark-sub">₹43.4 Lakhs EBITDA Net Margin</div>
          <div className="mini-sparkline-box">
            <svg viewBox="0 0 100 24" className="mini-sparkline-svg">
              <path
                d="M 0 16 L 20 17 L 40 14 L 60 12 L 80 8 L 100 5"
                fill="none"
                stroke="#f59e0b"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
          </div>
        </div>

        {/* KPI 4: Clean Fleet Generation */}
        <div className="kpi-spark-card">
          <div className="kpi-spark-top">
            <span className="kpi-spark-label">Clean Fleet Generation</span>
            <span className="kpi-delta positive">
              <ArrowUpRight size={14} /> 99.9% Uptime
            </span>
          </div>
          <div className="kpi-spark-value">3.42 GWh</div>
          <div className="kpi-spark-sub">2,736 Metric Tons CO₂ Offset</div>
          <div className="mini-sparkline-box">
            <svg viewBox="0 0 100 24" className="mini-sparkline-svg">
              <path
                d="M 0 22 L 15 18 L 30 14 L 45 12 L 60 7 L 75 5 L 90 3 L 100 1"
                fill="none"
                stroke="#06b6d4"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
          </div>
        </div>
      </div>

      {/* ===================================================================
          ROW A: FINANCIALS & CAPACITY PLOTS (Spline Area + Grouped Bar)
          =================================================================== */}
      {(activeCategory === 'all' || activeCategory === 'financials') && (
        <div className="analytics-two-col-grid">
          {/* Plot 1: Monthly Financial Spline Area Chart */}
          <div className="chart-card-bento">
            <div className="chart-header-row">
              <div>
                <h3 className="chart-title">12-Month Financial Performance & Cash Flow</h3>
                <span className="chart-subtitle">Monthly Gross Revenue vs Operating Delivery Costs (₹ in Lakhs)</span>
              </div>
              <div className="chart-legend-row">
                <span className="legend-item">
                  <span className="legend-dot" style={{ background: '#4f46e5' }} />
                  <span>Gross Revenue</span>
                </span>
                <span className="legend-item">
                  <span className="legend-dot" style={{ background: '#f59e0b' }} />
                  <span>Operating Costs</span>
                </span>
              </div>
            </div>

            {/* SVG Spline Area Plot */}
            <div className="svg-chart-container">
              <svg viewBox={`0 0 ${areaW} ${areaH}`} className="interactive-svg-chart">
                <defs>
                  <linearGradient id="revenueAreaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#4f46e5" stopOpacity="0.28" />
                    <stop offset="100%" stopColor="#4f46e5" stopOpacity="0.0" />
                  </linearGradient>
                  <linearGradient id="costLineGrad" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#f59e0b" />
                    <stop offset="100%" stopColor="#ef4444" />
                  </linearGradient>
                </defs>

                {/* Horizontal Grid lines */}
                {[0, 5, 10, 15, 20].map((val) => {
                  const y = areaH - paddingY - (val / maxRevenue) * (areaH - paddingY * 2);
                  return (
                    <g key={val} className="grid-line-group">
                      <line x1={paddingX} y1={y} x2={areaW - paddingX} y2={y} stroke="#f1f5f9" strokeWidth="1" />
                      <text x={paddingX - 10} y={y + 4} textAnchor="end" fontSize="10.5" fill="#94a3b8">
                        ₹{val}L
                      </text>
                    </g>
                  );
                })}

                {/* Shaded Area under Revenue Curve */}
                <path d={areaRevD} fill="url(#revenueAreaGrad)" />

                {/* Operating Costs Curve */}
                <path d={splineCostD} fill="none" stroke="url(#costLineGrad)" strokeWidth="2.5" strokeDasharray="5,4" />

                {/* Revenue Curve */}
                <path d={splineRevD} fill="none" stroke="#4f46e5" strokeWidth="3.2" strokeLinecap="round" />

                {/* Interactive Points on Revenue Curve */}
                {pointsRev.map((p, idx) => {
                  const item = MONTHLY_FINANCIALS[idx];
                  const isHovered = hoveredPoint?.index === idx;

                  return (
                    <g
                      key={idx}
                      className="interactive-point"
                      onMouseEnter={() => setHoveredPoint({ index: idx, item, p })}
                      onMouseLeave={() => setHoveredPoint(null)}
                      style={{ cursor: 'pointer' }}
                    >
                      <circle
                        cx={p.x}
                        cy={p.y}
                        r={isHovered ? 7 : 4}
                        fill="#ffffff"
                        stroke="#4f46e5"
                        strokeWidth={isHovered ? 3.5 : 2.5}
                        style={{ transition: 'all 150ms ease' }}
                      />
                      {/* Month label along X-axis */}
                      <text
                        x={p.x}
                        y={areaH - 10}
                        textAnchor="middle"
                        fontSize="11"
                        fontWeight={isHovered ? '700' : '500'}
                        fill={isHovered ? '#1e1b4b' : '#64748b'}
                      >
                        {item.month}
                      </text>
                    </g>
                  );
                })}

                {/* Hover Tooltip Overlay in SVG */}
                {hoveredPoint && (
                  <g className="svg-tooltip-box" transform={`translate(${Math.min(hoveredPoint.p.x - 65, areaW - 145)}, ${Math.max(hoveredPoint.p.y - 70, 10)})`}>
                    <rect width="130" height="54" rx="8" fill="#1e1b4b" fillOpacity="0.95" />
                    <text x="65" y="16" textAnchor="middle" fill="#ffffff" fontSize="11" fontWeight="700">
                      {hoveredPoint.item.month} 2026: ₹{hoveredPoint.item.revenue}L
                    </text>
                    <text x="65" y="32" textAnchor="middle" fill="#fbbf24" fontSize="10">
                      Costs: ₹{hoveredPoint.item.costs}L · Net: ₹{hoveredPoint.item.ebitda}L
                    </text>
                    <text x="65" y="46" textAnchor="middle" fill="#34d399" fontSize="10" fontWeight="600">
                      Margin: {hoveredPoint.item.margin}% · {hoveredPoint.item.kw} kW
                    </text>
                  </g>
                )}
              </svg>
            </div>

            <div className="chart-footer-metrics">
              <div className="chart-stat-chip">
                <span className="stat-chip-label">Peak Month:</span>
                <span className="stat-chip-val">March (₹17.8L · 135 kW)</span>
              </div>
              <div className="chart-stat-chip">
                <span className="stat-chip-label">Avg Margin:</span>
                <span className="stat-chip-val" style={{ color: '#059669' }}>29.7% EBITDA</span>
              </div>
            </div>
          </div>

          {/* Plot 2: Installed Solar Capacity Target vs Actual (Grouped Columns) */}
          <div className="chart-card-bento">
            <div className="chart-header-row">
              <div>
                <h3 className="chart-title">Quarterly Solar Capacity Delivered</h3>
                <span className="chart-subtitle">Delivered kW vs Quota Benchmark across Sectors</span>
              </div>
              <div className="chart-legend-row">
                <span className="legend-item">
                  <span className="legend-dot" style={{ background: '#059669' }} />
                  <span>Delivered Actual</span>
                </span>
                <span className="legend-item">
                  <span className="legend-dot" style={{ background: '#e2e8f0' }} />
                  <span>Target Quota</span>
                </span>
              </div>
            </div>

            <div className="grouped-bars-wrapper">
              {CAPACITY_COMPARISON.map((q, idx) => {
                const maxBarKw = 400;
                const actualWidthPct = (q.actualKw / maxBarKw) * 100;
                const targetWidthPct = (q.targetKw / maxBarKw) * 100;

                return (
                  <div key={idx} className="quarter-capacity-row">
                    <div className="quarter-row-header">
                      <span className="quarter-name">{q.label}</span>
                      <span className="quarter-stats">
                        <strong>{q.actualKw} kW</strong> / {q.targetKw} kW
                        <span className="quarter-pct-badge">+{q.pct - 100}% Exceeded</span>
                      </span>
                    </div>

                    <div className="capacity-bar-track">
                      {/* Target marker line */}
                      <div
                        className="capacity-target-marker"
                        style={{ left: `${targetWidthPct}%` }}
                        title={`Target: ${q.targetKw} kW`}
                      />

                      {/* Actual Stacked Bar (Residential + Commercial) */}
                      <div
                        className="capacity-actual-bar"
                        style={{ width: `${actualWidthPct}%` }}
                      >
                        <div
                          className="bar-sub-res"
                          style={{ width: `${(q.resKw / q.actualKw) * 100}%` }}
                          title={`Residential: ${q.resKw} kW`}
                        />
                        <div
                          className="bar-sub-comm"
                          style={{ width: `${(q.commKw / q.actualKw) * 100}%` }}
                          title={`Commercial: ${q.commKw} kW`}
                        />
                      </div>
                    </div>

                    <div className="quarter-breakdown-labels">
                      <span>🏠 Residential: {q.resKw} kW</span>
                      <span>🏢 Commercial C&I: {q.commKw} kW</span>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="chart-footer-metrics">
              <div className="chart-stat-chip">
                <span className="stat-chip-label">Total Commissioned:</span>
                <span className="stat-chip-val">842.5 kW / 825 kW Quota (102.1%)</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================
          ROW B: REVENUE STREAMS & CONVERSION FUNNEL (Donut + Funnel)
          =================================================================== */}
      {(activeCategory === 'all' || activeCategory === 'financials' || activeCategory === 'ops') && (
        <div className="analytics-two-col-grid">
          {/* Plot 3: Revenue Stream Distribution (Interactive Donut) */}
          <div className="chart-card-bento">
            <div className="chart-header-row">
              <div>
                <h3 className="chart-title">Revenue Stream Diversity Matrix</h3>
                <span className="chart-subtitle">Portfolio Distribution across 5 Business Verticals</span>
              </div>
              <span className="chart-badge-pill">₹1.48 Cr Portfolio</span>
            </div>

            <div className="donut-and-legend-layout">
              {/* SVG Donut */}
              <div className="donut-svg-wrapper">
                <svg viewBox="0 0 200 200" className="donut-svg-chart">
                  <circle
                    cx="100"
                    cy="100"
                    r={donutRadius}
                    fill="none"
                    stroke="#f1f5f9"
                    strokeWidth="24"
                  />
                  {REVENUE_STREAMS.map((seg, idx) => {
                    const strokeDash = (seg.pct / 100) * donutCircumference;
                    const strokeOffset = -(accumulatedPct / 100) * donutCircumference;
                    accumulatedPct += seg.pct;

                    const isHovered = hoveredDonut?.name === seg.name;

                    return (
                      <circle
                        key={idx}
                        cx="100"
                        cy="100"
                        r={donutRadius}
                        fill="none"
                        stroke={seg.color}
                        strokeWidth={isHovered ? 28 : 24}
                        strokeDasharray={`${strokeDash} ${donutCircumference}`}
                        strokeDashoffset={strokeOffset}
                        strokeLinecap="round"
                        transform="rotate(-90 100 100)"
                        className="donut-segment"
                        onMouseEnter={() => setHoveredDonut(seg)}
                        onMouseLeave={() => setHoveredDonut(null)}
                        style={{ cursor: 'pointer', transition: 'stroke-width 180ms ease' }}
                      />
                    );
                  })}
                  {/* Center Readout */}
                  <text x="100" y="93" textAnchor="middle" fontSize="18" fontWeight="800" fill="#0f172a">
                    {hoveredDonut ? `${hoveredDonut.pct}%` : '₹1.48 Cr'}
                  </text>
                  <text x="100" y="112" textAnchor="middle" fontSize="10.5" fill="#64748b" fontWeight="600">
                    {hoveredDonut ? hoveredDonut.name.split(' ')[0] : 'Total Turnover'}
                  </text>
                </svg>
              </div>

              {/* Legend List with Detailed Contracts Count */}
              <div className="donut-legend-list">
                {REVENUE_STREAMS.map((seg, idx) => (
                  <div
                    key={idx}
                    className={`donut-legend-row ${hoveredDonut?.name === seg.name ? 'highlighted' : ''}`}
                    onMouseEnter={() => setHoveredDonut(seg)}
                    onMouseLeave={() => setHoveredDonut(null)}
                  >
                    <div className="donut-legend-info">
                      <span className="legend-color-dot" style={{ background: seg.color }} />
                      <div className="legend-text-col">
                        <span className="legend-name">{seg.name}</span>
                        <span className="legend-sub">{seg.contracts} Active Accounts / Projects</span>
                      </div>
                    </div>
                    <div className="donut-legend-value">
                      <span className="val-inr">₹{seg.value} L</span>
                      <span className="val-pct">{seg.pct}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Plot 4: Enterprise Pipeline Conversion Funnel (Stepped Plot) */}
          <div className="chart-card-bento">
            <div className="chart-header-row">
              <div>
                <h3 className="chart-title">Customer Project Delivery Funnel</h3>
                <span className="chart-subtitle">End-to-End Pipeline Conversion from Lead to Grid Metering</span>
              </div>
              <span className="chart-badge-pill" style={{ background: '#ecfdf5', color: '#059669' }}>
                36.1% Net Conversion
              </span>
            </div>

            <div className="funnel-container">
              {ENTERPRISE_FUNNEL.map((step, idx) => {
                const widthPct = Math.max(step.pct, 24);

                return (
                  <div key={idx} className="funnel-step-item">
                    <div className="funnel-step-meta">
                      <span className="funnel-step-title">{step.stage}</span>
                      <div className="funnel-step-numbers">
                        <strong>{step.count.toLocaleString()}</strong>
                        <span className="funnel-pct">({step.pct}%)</span>
                      </div>
                    </div>

                    <div className="funnel-bar-track">
                      <div
                        className="funnel-bar-fill"
                        style={{
                          width: `${widthPct}%`,
                          background: `linear-gradient(90deg, #4f46e5 0%, #06b6d4 100%)`,
                          opacity: 1 - idx * 0.1,
                        }}
                      />
                    </div>

                    <div className="funnel-step-subtext">
                      <span>{step.sub}</span>
                      {step.drop > 0 && <span className="funnel-drop-tag">-{step.drop}% drop</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================
          ROW C: REGIONAL TERRITORIES & UNIT ECONOMICS STACK
          =================================================================== */}
      {(activeCategory === 'all' || activeCategory === 'ops' || activeCategory === 'financials') && (
        <div className="analytics-two-col-grid">
          {/* Plot 5: Regional Territory Benchmark (Horizontal Bars) */}
          <div className="chart-card-bento">
            <div className="chart-header-row">
              <div>
                <h3 className="chart-title">Regional Territory Operations & Quotas</h3>
                <span className="chart-subtitle">Revenue, Delivered Capacity and Field Crews by Circle</span>
              </div>
              <span className="chart-badge-pill">5 Operating Circles</span>
            </div>

            <div className="territory-list">
              {REGIONAL_TERRITORIES.map((t, idx) => (
                <div key={idx} className="territory-item">
                  <div className="territory-header-row">
                    <div className="territory-name-box">
                      <MapPin size={15} color="#4f46e5" />
                      <strong>{t.region}</strong>
                      <span className="territory-crew-pill">{t.crews} Field Crews</span>
                    </div>
                    <div className="territory-stats-box">
                      <span className="territory-rev">{t.rev}</span>
                      <span className="territory-kw">({t.kw} kW)</span>
                      <span className={`territory-status-chip ${t.status.toLowerCase()}`}>
                        {t.quotaPct}% Quota
                      </span>
                    </div>
                  </div>

                  <div className="territory-bar-track">
                    <div
                      className="territory-bar-fill"
                      style={{
                        width: `${Math.min(t.quotaPct, 100)}%`,
                        background: t.quotaPct >= 100 ? '#10b981' : t.quotaPct >= 90 ? '#4f46e5' : '#f59e0b',
                      }}
                    />
                    <div className="territory-benchmark-100" title="100% Target Benchmark" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Plot 6: Unit Economics & Standard 1 kW Rooftop Cost Stack */}
          <div className="chart-card-bento">
            <div className="chart-header-row">
              <div>
                <h3 className="chart-title">Standard 1 kW Cost Stack & Unit Economics</h3>
                <span className="chart-subtitle">BOM Composition & Cost Breakdown (Base Cost: ₹54,000 / kW)</span>
              </div>
              <span className="chart-badge-pill" style={{ background: '#f0fdf4', color: '#16a34a' }}>
                +₹15,800 Margin / kW
              </span>
            </div>

            <div className="unit-cost-stacked-bar">
              {UNIT_ECONOMICS.map((u, idx) => (
                <div
                  key={idx}
                  className="cost-stack-segment"
                  style={{ width: `${u.pct}%`, background: u.color }}
                  title={`${u.component}: ₹${u.cost.toLocaleString()} (${u.pct}%)`}
                />
              ))}
            </div>

            <div className="cost-breakdown-table">
              {UNIT_ECONOMICS.map((u, idx) => (
                <div key={idx} className="cost-breakdown-row">
                  <div className="cost-name-cell">
                    <span className="cost-legend-box" style={{ background: u.color }} />
                    <span className="cost-label">{u.component}</span>
                  </div>
                  <div className="cost-values-cell">
                    <span className="cost-amt">₹{u.cost.toLocaleString()}</span>
                    <span className="cost-pct">{u.pct}%</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="retail-margin-callout">
              <div className="retail-cell">
                <span className="cell-label">Total Cost of Goods (COGS):</span>
                <span className="cell-val">₹54,000 / kW</span>
              </div>
              <div className="retail-cell">
                <span className="cell-label">Retail Price to Customer:</span>
                <span className="cell-val" style={{ color: '#4f46e5' }}>₹69,800 / kW</span>
              </div>
              <div className="retail-cell">
                <span className="cell-label">Gross Margin per kW:</span>
                <span className="cell-val" style={{ color: '#059669' }}>₹15,800 (29.3%)</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================
          ROW D: DIURNAL SOLAR GENERATION & INVENTORY ASSET VALUATION
          =================================================================== */}
      {(activeCategory === 'all' || activeCategory === 'ops' || activeCategory === 'supply') && (
        <div className="analytics-two-col-grid">
          {/* Plot 7: 24-Hour Diurnal Fleet Solar Generation Curve */}
          <div className="chart-card-bento">
            <div className="chart-header-row">
              <div>
                <h3 className="chart-title">Diurnal Irradiance & Fleet Solar Generation</h3>
                <span className="chart-subtitle">Hourly Solar Yield vs Customer Self-Consumption & Grid Export</span>
              </div>
              <div className="chart-legend-row">
                <span className="legend-item">
                  <span className="legend-dot" style={{ background: '#f59e0b' }} />
                  <span>Solar PV Output</span>
                </span>
                <span className="legend-item">
                  <span className="legend-dot" style={{ background: '#059669' }} />
                  <span>Net Grid Export</span>
                </span>
              </div>
            </div>

            {/* SVG Diurnal Curve */}
            <div className="svg-chart-container">
              <svg viewBox="0 0 680 200" className="interactive-svg-chart">
                <defs>
                  <linearGradient id="solarYieldGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.32" />
                    <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.0" />
                  </linearGradient>
                  <linearGradient id="gridExportGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity="0.30" />
                    <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                {/* Grid guidelines */}
                {[0, 0.5, 1.0, 1.5, 2.0].map((v) => {
                  const y = 170 - (v / 2.0) * 140;
                  return (
                    <line key={v} x1="40" y1={y} x2="640" y2={y} stroke="#f1f5f9" strokeWidth="1" />
                  );
                })}

                {/* Shaded Area for Solar Output */}
                <path
                  d="M 40 170 C 100 165, 140 120, 200 80 C 260 40, 320 20, 380 20 C 440 20, 500 50, 560 110 C 600 150, 620 168, 640 170 Z"
                  fill="url(#solarYieldGrad)"
                />

                {/* Solar Curve */}
                <path
                  d="M 40 170 C 100 165, 140 120, 200 80 C 260 40, 320 20, 380 20 C 440 20, 500 50, 560 110 C 600 150, 620 168, 640 170"
                  fill="none"
                  stroke="#f59e0b"
                  strokeWidth="3.2"
                  strokeLinecap="round"
                />

                {/* Grid Export Area */}
                <path
                  d="M 220 170 C 260 120, 320 70, 380 70 C 440 70, 500 110, 540 170 Z"
                  fill="url(#gridExportGrad)"
                />
                <path
                  d="M 220 170 C 260 120, 320 70, 380 70 C 440 70, 500 110, 540 170"
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="2.5"
                  strokeDasharray="4,3"
                />

                {/* Hourly X-axis points */}
                {DIURNAL_GENERATION.map((d, i) => {
                  const x = 40 + (i * 600) / (DIURNAL_GENERATION.length - 1);
                  return (
                    <text key={i} x={x} y="190" textAnchor="middle" fontSize="10.5" fill="#64748b">
                      {d.hour}
                    </text>
                  );
                })}
              </svg>
            </div>

            <div className="chart-footer-metrics">
              <div className="chart-stat-chip">
                <span className="stat-chip-label">Peak Fleet Output:</span>
                <span className="stat-chip-val" style={{ color: '#d97706' }}>1.84 MW at 12:30 PM</span>
              </div>
              <div className="chart-stat-chip">
                <span className="stat-chip-label">Avg Peak Sun Hours:</span>
                <span className="stat-chip-val">5.42 PSH / Day</span>
              </div>
            </div>
          </div>

          {/* Plot 8: Warehouse Inventory Valuation Matrix */}
          <div className="chart-card-bento">
            <div className="chart-header-row">
              <div>
                <h3 className="chart-title">Warehouse Inventory Asset Health</h3>
                <span className="chart-subtitle">Material Stock Valuation & Turnover Ratio (Total: ₹1.94 Cr)</span>
              </div>
              <span className="chart-badge-pill" style={{ background: '#eef2ff', color: '#4f46e5' }}>
                8.4x Annual Turnover
              </span>
            </div>

            <div className="inventory-matrix-grid">
              {WAREHOUSE_INVENTORY_MATRIX.map((inv, idx) => (
                <div key={idx} className="inv-matrix-card">
                  <div className="inv-matrix-header">
                    <strong className="inv-category">{inv.category}</strong>
                    <span className={`inv-status-pill ${inv.status === 'Optimal' ? 'green' : 'amber'}`}>
                      {inv.status}
                    </span>
                  </div>

                  <div className="inv-matrix-body">
                    <div className="inv-val-primary">{inv.value}</div>
                    <div className="inv-sub-details">
                      <span>{inv.units}</span> · <span>Turnover {inv.turnover}</span>
                    </div>
                  </div>

                  {/* Stock Health Progress Bar */}
                  <div className="inv-health-bar-track">
                    <div
                      className="inv-health-bar-fill"
                      style={{
                        width: `${inv.health}%`,
                        background: inv.health >= 90 ? '#10b981' : '#f59e0b',
                      }}
                    />
                  </div>
                  <div className="inv-health-foot">
                    <span>Stock Health Index:</span>
                    <strong>{inv.health}%</strong>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================
          ROW E: DISCOM SLA TREND & EXECUTIVE RADIAL GAUGES
          =================================================================== */}
      {(activeCategory === 'all' || activeCategory === 'sla') && (
        <div className="analytics-two-col-grid">
          {/* Plot 9: DISCOM Net-Metering SLA Approval Speed (Historical Trend) */}
          <div className="chart-card-bento">
            <div className="chart-header-row">
              <div>
                <h3 className="chart-title">DISCOM Grid Interconnection SLA Velocity</h3>
                <span className="chart-subtitle">Average Days to Bi-directional Net-Meter & DBT Subsidy Release</span>
              </div>
              <span className="chart-badge-pill" style={{ background: '#ecfdf5', color: '#059669' }}>
                75% Faster Turnaround
              </span>
            </div>

            <div className="sla-trend-bars">
              {SLA_APPROVAL_TREND.map((item, idx) => {
                const maxDays = 25;
                const bescomWidth = (item.bescomDays / maxDays) * 100;
                const dbtWidth = (item.dbtDays / maxDays) * 100;

                return (
                  <div key={idx} className="sla-trend-row">
                    <span className="sla-month">{item.month}</span>

                    <div className="sla-bars-dual">
                      <div className="sla-bar-line">
                        <span className="sla-bar-label">BESCOM Meter:</span>
                        <div className="sla-track">
                          <div className="sla-fill bescom" style={{ width: `${bescomWidth}%` }} />
                        </div>
                        <span className="sla-days">{item.bescomDays}d</span>
                      </div>

                      <div className="sla-bar-line">
                        <span className="sla-bar-label">Portal DBT:</span>
                        <div className="sla-track">
                          <div className="sla-fill dbt" style={{ width: `${dbtWidth}%` }} />
                        </div>
                        <span className="sla-days">{item.dbtDays}d</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="chart-footer-metrics">
              <div className="chart-stat-chip">
                <span className="stat-chip-label">Current Meter SLA:</span>
                <span className="stat-chip-val" style={{ color: '#059669' }}>4.2 Days (Govt Target: 21 Days)</span>
              </div>
            </div>
          </div>

          {/* Plot 10: Executive Quality, Safety & CSAT Radial Gauges */}
          <div className="chart-card-bento">
            <div className="chart-header-row">
              <div>
                <h3 className="chart-title">Executive Operations Quality & Safety Compliance</h3>
                <span className="chart-subtitle">Audited Field Precision, CSAT and Fleet Uptime</span>
              </div>
              <span className="chart-badge-pill">Audited 100%</span>
            </div>

            <div className="executive-gauges-grid">
              {/* Gauge 1: Customer CSAT */}
              <div className="exec-gauge-card">
                <div className="exec-gauge-circle-box">
                  <svg width="68" height="68" viewBox="0 0 36 36">
                    <path
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      fill="none"
                      stroke="#f1f5f9"
                      strokeWidth="3.2"
                    />
                    <path
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      fill="none"
                      stroke="#059669"
                      strokeWidth="3.2"
                      strokeDasharray="96.4, 100"
                      strokeLinecap="round"
                    />
                  </svg>
                  <span className="gauge-center-val">96.4%</span>
                </div>
                <strong className="exec-gauge-title">Customer CSAT</strong>
                <span className="exec-gauge-sub">4.82/5 Stars · 520 Reviews</span>
              </div>

              {/* Gauge 2: Survey Accuracy */}
              <div className="exec-gauge-card">
                <div className="exec-gauge-circle-box">
                  <svg width="68" height="68" viewBox="0 0 36 36">
                    <path
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      fill="none"
                      stroke="#f1f5f9"
                      strokeWidth="3.2"
                    />
                    <path
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      fill="none"
                      stroke="#4f46e5"
                      strokeWidth="3.2"
                      strokeDasharray="94.2, 100"
                      strokeLinecap="round"
                    />
                  </svg>
                  <span className="gauge-center-val">94.2%</span>
                </div>
                <strong className="exec-gauge-title">Survey Accuracy</strong>
                <span className="exec-gauge-sub">Zero Rework on 3D Raytracing</span>
              </div>

              {/* Gauge 3: Safety Compliance */}
              <div className="exec-gauge-card">
                <div className="exec-gauge-circle-box">
                  <svg width="68" height="68" viewBox="0 0 36 36">
                    <path
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      fill="none"
                      stroke="#f1f5f9"
                      strokeWidth="3.2"
                    />
                    <path
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      fill="none"
                      stroke="#f59e0b"
                      strokeWidth="3.2"
                      strokeDasharray="99.8, 100"
                      strokeLinecap="round"
                    />
                  </svg>
                  <span className="gauge-center-val">99.8%</span>
                </div>
                <strong className="exec-gauge-title">Safety Gear SLA</strong>
                <span className="exec-gauge-sub">Zero-Harm on Rooftop Work</span>
              </div>

              {/* Gauge 4: Fleet Uptime */}
              <div className="exec-gauge-card">
                <div className="exec-gauge-circle-box">
                  <svg width="68" height="68" viewBox="0 0 36 36">
                    <path
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      fill="none"
                      stroke="#f1f5f9"
                      strokeWidth="3.2"
                    />
                    <path
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      fill="none"
                      stroke="#06b6d4"
                      strokeWidth="3.2"
                      strokeDasharray="99.9, 100"
                      strokeLinecap="round"
                    />
                  </svg>
                  <span className="gauge-center-val">99.9%</span>
                </div>
                <strong className="exec-gauge-title">Fleet Uptime</strong>
                <span className="exec-gauge-sub">Inverter Availability MTBF</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
