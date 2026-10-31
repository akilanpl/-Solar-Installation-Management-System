import React, { useState } from 'react';
import {
  Plus,
  Calendar,
  Clock,
  MoreHorizontal,
  Trash2,
  Edit2,
  Share2,
  LayoutGrid,
  List,
  CheckCircle2,
  FileText,
  Layers,
  Sparkles,
  Users,
  Paperclip,
  MessageSquare,
  ArrowRight,
  Sun,
  Zap,
  TrendingUp,
  Package,
  Wrench,
  Headphones,
  Shield,
  Check,
  AlertTriangle,
  Upload,
  MapPin,
  Search,
  DollarSign,
  Truck,
  Phone,
  ExternalLink,
  Award,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from '../../router/Router';
import { formatCapacity, formatInrFromPaise } from '../../lib/format';
import './DashboardView.css';

export function DashboardView({
  role = null,
  enquiries = [],
  jobs = [],
  stock = [],
  tickets = [],
  employees = [],
  onNewAction = null,
  onChecklistItemToggle = null,
}) {
  const { user, showToast } = useAuth();
  const { navigate } = useRouter();
  const [activeDate, setActiveDate] = useState(18); // Fri 18 active

  const activeRole = role || user?.role || 'customer';
  const firstName = user?.full_name ? user.full_name.split(' ')[0] : 'James';

  // --------------------------------------------------------------------------
  // INTERACTIVE DEMO STATES PER ROLE
  // --------------------------------------------------------------------------
  // Sales BOM Package Generator
  const [activePkg, setActivePkg] = useState('5kW');

  // Warehouse Serial Barcode Scanner
  const [scannedSerials, setScannedSerials] = useState([
    'SN-PV540-KA-0981',
    'SN-PV540-KA-0982',
    'SN-PV540-KA-0983',
    'SN-PV540-KA-0984',
    'SN-PV540-KA-0985',
  ]);
  const [serialInput, setSerialInput] = useState('');

  // Technician Checklist & Signature
  const [techChecklist, setTechChecklist] = useState([
    { id: 1, label: 'Rooftop Orientation & True South 180° Azimuth', done: true },
    { id: 2, label: 'Shadow Raytracing Analysis (09:00 AM - 04:00 PM)', done: true },
    { id: 3, label: 'RCC Structural Roof Slab Load Bearing Integrity', done: true },
    { id: 4, label: 'AC/DC Distribution Box Location & Breaker Rating', done: false },
    { id: 5, label: 'Chemical Earthing Pit Ground Resistance < 5Ω', done: false },
    { id: 6, label: 'Bi-directional Net-Metering Meter Clearance', done: false },
  ]);
  const [signatureSigned, setSignatureSigned] = useState(false);
  const [otpInput, setOtpInput] = useState('');
  const [otpVerified, setOtpVerified] = useState(false);

  // Support SysCache Fast Lookup
  const [sysCacheQuery, setSysCacheQuery] = useState('');
  const [sysCacheCustomer, setSysCacheCustomer] = useState({
    name: 'Arun Kumar',
    email: 'customer@solarops.dev',
    meter: 'BESCOM-KA-BLR-099234',
    system: '5 kW Hybrid Bifacial (10x 540W)',
    inverterSn: 'INV-HYB5K-2026-041',
    commissioned: '24 Oct 2025',
    warranty: 'Active (Expires 24 Oct 2035)',
    livePower: '4.32 kW',
  });

  // Customer Advance Payment
  const [advancePaid, setAdvancePaid] = useState(false);

  // --------------------------------------------------------------------------
  // ROLE CONFIGURATION: GREETINGS, TOP STATS, FOCUS CARD, GAUGES & BRIEFINGS
  // --------------------------------------------------------------------------
  const getRoleConfig = () => {
    switch (activeRole) {
      case 'sales':
        return {
          greetingQuestion: ['Ready to review', 'feasibility today?'],
          greetingSub:
            'Screen incoming solar enquiries, analyze rooftop load parameters, and schedule site engineering surveys.',
          featureCards: [
            {
              isAdd: true,
              label: 'Qualify Leads',
              action: () => showToast({ type: 'info', title: 'Lead Queue', message: 'Ready to qualify incoming leads.' }),
            },
            {
              title: 'Enquiry Funnel',
              sub: `${enquiries.length || 18} Active submissions`,
              icon: <Layers size={28} color="#4F46E5" />,
            },
            {
              title: 'Feasibility Quotes',
              sub: '9 Proposals ready for review',
              icon: <FileText size={28} color="#4F46E5" />,
            },
            {
              title: 'Scheduled Surveys',
              sub: '6 Site visits assigned',
              icon: <Calendar size={28} color="#4F46E5" />,
            },
          ],
          focusCard: {
            title: 'Monthly Target: 100 kW',
            sub: '74 kW commissioned this month across Bangalore residential rooftop cluster (74% achieved).',
            buttonText: 'View Pipeline Target',
            action: () => showToast({ type: 'success', title: 'Target Metrics', message: '74% of target achieved!' }),
          },
          gauge1: { percent: '84%', cat: 'Conversion', title: 'Lead Velocity', sub: '21/25 proposals qualified' },
          gauge2: { percent: '92%', cat: 'SLA Speed', title: 'Quote Turnaround', sub: 'Under 24 hours' },
          briefing: {
            title: 'Client Technical Briefing',
            time: '● Today at 4:30 PM',
            desc: 'With Rahul Verma, Sanctioned load 7.5kW proposal review',
          },
        };

      case 'technician':
        return {
          greetingQuestion: ['Ready for your', 'site surveys today?'],
          greetingSub:
            'Conduct on-site rooftop shadow raytracing, verify structural roof integrity, and upload engineering checklist evidence.',
          featureCards: [
            {
              isAdd: true,
              label: 'New Inspection',
              action: () => showToast({ type: 'info', title: 'Field Queue', message: 'Ready for today\'s inspections.' }),
            },
            {
              title: 'Assigned Surveys',
              sub: `${jobs.length || 3} Rooftop locations`,
              icon: <Wrench size={28} color="#4F46E5" />,
            },
            {
              title: 'Shadow Checks',
              sub: '100% Raytracing logged',
              icon: <Sun size={28} color="#4F46E5" />,
            },
            {
              title: 'Offline Sync',
              sub: 'Local field cache ready',
              icon: <CheckCircle2 size={28} color="#4F46E5" />,
            },
          ],
          focusCard: {
            title: 'Field Diagnostics Active',
            sub: 'SysCache field engine active. GPS-tagged roof photos and azimuth readings automatically queue for sync.',
            buttonText: 'Sync Offline Evidence',
            action: () => showToast({ type: 'success', title: 'Field Sync', message: 'Field photos synced successfully.' }),
          },
          gauge1: { percent: '95%', cat: 'Compliance', title: 'Safety Gear', sub: 'Full harness & boots verified' },
          gauge2: { percent: '80%', cat: 'Checklists', title: 'Site Reports', sub: '4/5 visits signed off' },
          briefing: {
            title: 'Field Engineering Debrief',
            time: '● Today at 5:00 PM',
            desc: 'With Engineering Operations Lead, Room 104',
          },
        };

      case 'warehouse_staff':
      case 'warehouse_manager':
        return {
          greetingQuestion: ['What solar inventory', 'needs dispatch today?'],
          greetingSub:
            'Monitor physical counts of photovoltaic modules, hybrid inverters, batteries, and staging material dispatches.',
          featureCards: [
            {
              isAdd: true,
              label: 'Inbound GRN',
              action: () => showToast({ type: 'info', title: 'Warehouse', message: 'GRN intake modal initialized.' }),
            },
            {
              title: 'In-Stock Modules',
              sub: `${stock.reduce?.((acc, s) => acc + (s.in_stock || 0), 0) || 142} PV Panels`,
              icon: <Package size={28} color="#4F46E5" />,
            },
            {
              title: 'Hybrid Inverters',
              sub: '38 Grid-tie units',
              icon: <Zap size={28} color="#4F46E5" />,
            },
            {
              title: 'Staging Dispatches',
              sub: '18 Material kits ready',
              icon: <Layers size={28} color="#4F46E5" />,
            },
          ],
          focusCard: {
            title: 'Inventory Health Alert',
            sub: 'Mono-PERC 540W modules are approaching safety reorder threshold (14 units remaining).',
            buttonText: 'Generate Supplier PO',
            action: () => showToast({ type: 'warning', title: 'Supplier PO', message: 'PO drafted for 50 PV modules.' }),
          },
          gauge1: { percent: '98%', cat: 'Stock Level', title: 'Accuracy', sub: 'Physical count verified' },
          gauge2: { percent: '85%', cat: 'Logistics', title: 'Pick Speed', sub: 'Average 28m per crew kit' },
          briefing: {
            title: 'Logistics Carrier Sync',
            time: '● Today at 3:30 PM',
            desc: 'Staging truck routing with Freight Dispatch Coordinator',
          },
        };

      case 'support':
        return {
          greetingQuestion: ['What customer tickets', 'need resolution today?'],
          greetingSub:
            'Liaise on BESCOM net-metering approvals, DISCOM grid synchronization, and inverter warranty tickets.',
          featureCards: [
            {
              isAdd: true,
              label: 'New Ticket',
              action: () => showToast({ type: 'info', title: 'Support', message: 'Escalation ticket modal opened.' }),
            },
            {
              title: 'Open Tickets',
              sub: `${tickets.length || 8} Active enquiries`,
              icon: <Headphones size={28} color="#4F46E5" />,
            },
            {
              title: 'Net-Metering',
              sub: '14 BESCOM applications',
              icon: <CheckCircle2 size={28} color="#4F46E5" />,
            },
            {
              title: 'Warranty Support',
              sub: '3 Replacements in transit',
              icon: <Shield size={28} color="#4F46E5" />,
            },
          ],
          focusCard: {
            title: 'DISCOM Grid Sync SLA',
            sub: 'Karnataka BESCOM circle approval time reduced to an average of 4.2 business days.',
            buttonText: 'View Circle Telemetry',
            action: () => showToast({ type: 'info', title: 'BESCOM SLA', message: 'Average sync: 4.2 days.' }),
          },
          gauge1: { percent: '96%', cat: 'Customer CSAT', title: 'Satisfaction', sub: '52 positive reviews' },
          gauge2: { percent: '92%', cat: 'Resolution', title: 'First-Contact', sub: 'Resolved within 2 hours' },
          briefing: {
            title: 'DISCOM Coordination Call',
            time: '● Today at 4:00 PM',
            desc: 'BESCOM Circle 4 Bi-directional net-meter sync',
          },
        };

      case 'admin':
        return {
          greetingQuestion: ['Solar Operations &', 'Job Profitability today?'],
          greetingSub:
            'Monitor per-installation job cost accounting, customer invoices, subsidy claims, and enterprise personnel roster.',
          featureCards: [
            {
              isAdd: true,
              label: 'Add Staff',
              action: onNewAction || (() => showToast({ type: 'info', title: 'Staff Roster', message: 'Employee provisioning open.' })),
            },
            {
              title: 'Total Revenue',
              sub: '₹1.48 Cr Q2 YTD',
              icon: <DollarSign size={28} color="#4F46E5" />,
            },
            {
              title: 'Gross Margin',
              sub: '29.3% Average',
              icon: <TrendingUp size={28} color="#4F46E5" />,
            },
            {
              title: 'Operations Staff',
              sub: `${employees.length || 12} Active personnel`,
              icon: <Users size={28} color="#4F46E5" />,
            },
          ],
          focusCard: {
            title: 'Zero-Trust Security Active',
            sub: 'PostgreSQL connection pool healthy (18ms). HttpOnly session authorization tokens enforced with role RBAC.',
            buttonText: 'Inspect Health Logs',
            action: () => showToast({ type: 'success', title: 'System Status', message: 'All backend microservices green.' }),
          },
          gauge1: { percent: '100%', cat: 'Security', title: 'Compliance', sub: 'Zero unauthorized requests' },
          gauge2: { percent: '99%', cat: 'API Response', title: 'Latency SLA', sub: '< 45ms median response' },
          briefing: {
            title: 'Weekly Operations All-Hands',
            time: '● Today at 4:00 PM',
            desc: 'SolarOps Q2 milestones & gross profit review',
          },
        };

      case 'customer':
      default: {
        const totalCapacityWatts = enquiries.reduce((acc, item) => acc + (item.preferred_capacity_w || 0), 0);
        const totalMonthlyBillsPaise = enquiries.reduce((acc, item) => acc + (item.monthly_bill_minor || 0), 0);

        return {
          greetingQuestion: ['What are your', 'plans for today?'],
          greetingSub:
            'Track your rooftop solar system installation, milestones, serialized equipment warranties, and monthly savings.',
          featureCards: [
            {
              isAdd: true,
              label: 'New Solar Enquiry',
              action: onNewAction || (() => navigate('/customer/enquiries/new')),
            },
            {
              title: 'My Enquiries',
              sub: `${enquiries.length || 1} Active project`,
              icon: <Layers size={28} color="#4F46E5" />,
            },
            {
              title: 'Planned Capacity',
              sub: totalCapacityWatts > 0 ? formatCapacity(totalCapacityWatts) : '5.0 kW Hybrid',
              icon: <Sun size={28} color="#4F46E5" />,
            },
            {
              title: 'Monthly Savings',
              sub: totalMonthlyBillsPaise > 0 ? `₹${formatInrFromPaise(totalMonthlyBillsPaise)} / mo` : '₹4,200 / mo',
              icon: <TrendingUp size={28} color="#4F46E5" />,
            },
          ],
          focusCard: {
            title: '☀️ Live Solar Generation',
            sub: 'Estimated 620 kWh monthly rooftop generation offsetting 85% of your grid electricity bill.',
            buttonText: 'View Generation Telemetry',
            action: () => showToast({ type: 'success', title: 'Solar Telemetry', message: 'Real-time generation: 4.8 kW.' }),
          },
          gauge1: { percent: '90%', cat: 'Solar Offset', title: 'Grid Independence', sub: '5/5 milestones validated' },
          gauge2: { percent: '65%', cat: 'Annual Goal', title: 'Carbon Neutrality', sub: '2.4 tons CO2 saved' },
          briefing: {
            title: 'Technical Consultation',
            time: '● Today at 4:00 PM',
            desc: 'With Senior Solar Consultant, Rooftop Feasibility review',
          },
        };
      }
    }
  };

  const config = getRoleConfig();

  // Helper for BOM package selector
  const BOM_PACKAGES = {
    '1kW': {
      capacity: '1.0 kW Single-Phase',
      panels: '2x 540W Mono-PERC Modules',
      inverter: '1x 1kW Micro-Inverter',
      structures: '1x Anodized Aluminum Rail Set',
      cables: '20m 4 sq mm Solar DC Cables',
      price: 65000,
      subsidy: 30000,
      margin: '28%',
    },
    '3kW': {
      capacity: '3.0 kW Single-Phase',
      panels: '6x 540W Mono-PERC Bifacial',
      inverter: '1x 3kW String Grid-Tie Inverter',
      structures: '2x Anodized Aluminum Rail Sets',
      cables: '30m 4 sq mm Solar DC Cables',
      price: 175000,
      subsidy: 78000,
      margin: '30%',
    },
    '5kW': {
      capacity: '5.0 kW Three-Phase Hybrid',
      panels: '10x 540W Mono-PERC Bifacial',
      inverter: '1x 5kW Hybrid Inverter (Wi-Fi)',
      structures: '4x Anodized Aluminum Rail Sets',
      cables: '40m 4 sq mm Solar DC Cables',
      price: 285000,
      subsidy: 78000,
      margin: '32%',
    },
    '10kW': {
      capacity: '10.0 kW Three-Phase Commercial',
      panels: '20x 540W Mono-PERC Bifacial',
      inverter: '1x 10kW Commercial Solar Inverter',
      structures: '8x Heavy-Duty Rail Mount Sets',
      cables: '80m Heavy DC Armoured Cables',
      price: 540000,
      subsidy: 78000,
      margin: '34%',
    },
  };

  // Helper for adding serial scan
  const handleAddSerial = (e) => {
    e.preventDefault();
    if (!serialInput.trim()) return;
    setScannedSerials([...scannedSerials, serialInput.trim().toUpperCase()]);
    setSerialInput('');
    showToast({
      type: 'success',
      title: 'Barcode Scanned',
      message: `Serial ${serialInput.trim().toUpperCase()} verified and locked to Order SO-2026-0042.`,
    });
  };

  // Helper for technician checklist toggle
  const toggleTechCheck = (id) => {
    setTechChecklist(
      techChecklist.map((item) => (item.id === id ? { ...item, done: !item.done } : item))
    );
  };

  // Helper for Support SysCache lookup
  const handleSysCacheSearch = (e) => {
    e.preventDefault();
    if (!sysCacheQuery.trim()) return;
    setSysCacheCustomer({
      name: 'Arun Kumar',
      email: sysCacheQuery.includes('@') ? sysCacheQuery : 'customer@solarops.dev',
      meter: sysCacheQuery.toUpperCase().startsWith('BESCOM') ? sysCacheQuery.toUpperCase() : 'BESCOM-KA-BLR-099234',
      system: '5 kW Hybrid Bifacial (10x 540W)',
      inverterSn: 'INV-HYB5K-2026-041',
      commissioned: '24 Oct 2025',
      warranty: 'Active (Expires 24 Oct 2035)',
      livePower: '4.32 kW',
    });
    showToast({
      type: 'success',
      title: 'SysCache Hit (< 0.28s)',
      message: 'Customer technical profile loaded from Redis cache.',
    });
  };

  return (
    <div className="dash-container">
      {/* ================================================================
          ROW 1: HERO GREETING & TOP FEATURE CARDS
          ================================================================ */}
      <section className="dash-hero-row" aria-label="Dashboard Overview">
        {/* Left: Role-Specific Greeting Headline */}
        <div className="dash-greeting-box">
          <h1 className="dash-greeting-title">
            <span className="dash-greeting-header-line">
              <span>Hi, {firstName}!</span>
              <span className="dash-avatar-cluster">
                <span className="dash-avatar-ring"> </span>
              </span>
            </span>
            <span>{config.greetingQuestion[0]}</span>
            <span>{config.greetingQuestion[1]}</span>
          </h1>
          <p className="dash-greeting-sub">{config.greetingSub}</p>
        </div>

        {/* Right: 4 Tailored Quick-Action / Stat Cards */}
        <div className="dash-feature-cards-grid">
          {config.featureCards.map((card, idx) =>
            card.isAdd ? (
              <div
                key={idx}
                className="dash-feature-card create-new"
                onClick={card.action}
                title={card.label}
                role="button"
                tabIndex={0}
              >
                <div className="dash-create-icon-box">
                  <Plus size={22} strokeWidth={2.8} />
                </div>
              </div>
            ) : (
              <div
                key={idx}
                className="dash-feature-card"
                onClick={() =>
                  showToast({
                    type: 'info',
                    title: card.title,
                    message: card.sub,
                  })
                }
              >
                <div className="dash-feature-illustration">{card.icon}</div>
                <div>
                  <h4 className="dash-feature-title">{card.title}</h4>
                  <p className="dash-feature-sub">{card.sub}</p>
                </div>
              </div>
            )
          )}
        </div>
      </section>

      {/* ================================================================
          ROW 2: MIDDLE BENTO GRID (ESSENTIAL CONTAINERS TAILORED PER ROLE)
          ================================================================ */}
      <section className="dash-middle-grid">
        {/* ======================= CUSTOMER ROW 2 ======================= */}
        {activeRole === 'customer' && (
          <>
            {/* Col 1: Installation Lifecycle Stepper */}
            <div className="bento-card">
              <div className="bento-card-header">
                <h3 className="bento-card-title">Installation Lifecycle</h3>
                <span className="event-pill" style={{ background: '#ecfdf5', color: '#047857', border: 'none' }}>
                  <CheckCircle2 size={12} color="#047857" />
                  <span>On Schedule</span>
                </span>
              </div>
              <div className="lifecycle-stepper">
                <div className="stepper-step completed">
                  <div className="stepper-icon-circle">✓</div>
                  <div className="stepper-text">1. Solar Feasibility Enquiry</div>
                  <span style={{ fontSize: '11px', color: '#059669', fontWeight: '600' }}>Done</span>
                </div>
                <div className="stepper-step completed">
                  <div className="stepper-icon-circle">✓</div>
                  <div className="stepper-text">2. On-Site Rooftop Shadow Survey</div>
                  <span style={{ fontSize: '11px', color: '#059669', fontWeight: '600' }}>Done</span>
                </div>
                <div className="stepper-step active">
                  <div className="stepper-icon-circle">3</div>
                  <div className="stepper-text">3. Package Quotation & BOM Approved</div>
                  <span style={{ fontSize: '11px', color: '#4f46e5', fontWeight: '700' }}>Active</span>
                </div>
                <div className="stepper-step pending">
                  <div className="stepper-icon-circle">4</div>
                  <div className="stepper-text">4. 20% Advance Order Payment</div>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>Next</span>
                </div>
                <div className="stepper-step pending">
                  <div className="stepper-icon-circle">5</div>
                  <div className="stepper-text">5. Warehouse Staging & Serial Scan</div>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>Pending</span>
                </div>
                <div className="stepper-step pending">
                  <div className="stepper-icon-circle">6</div>
                  <div className="stepper-text">6. Rooftop Installation & Sign-off</div>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>Pending</span>
                </div>
              </div>
            </div>

            {/* Col 2: Approved Package Quotation & Itemized BOM */}
            <div className="bento-card">
              <div className="bento-card-header">
                <div>
                  <h3 className="bento-card-title">Approved 5 kW Hybrid BOM</h3>
                  <span style={{ fontSize: '11.5px', color: '#64748b' }}>Itemized parts list & pricing</span>
                </div>
                <span className="priority-badge-high" style={{ background: '#eef2ff', color: '#4f46e5' }}>
                  SO-2026-0042
                </span>
              </div>
              <div className="bom-breakdown-list">
                <div className="bom-item-row">
                  <div>
                    <span className="bom-item-name">Mono-PERC 540W Bifacial Panels</span>
                    <span className="bom-item-qty">x 10 units</span>
                  </div>
                  <span className="bom-item-price">₹1,35,000</span>
                </div>
                <div className="bom-item-row">
                  <div>
                    <span className="bom-item-name">5kW Hybrid Inverter (Grid-Tie + WiFi)</span>
                    <span className="bom-item-qty">x 1 unit</span>
                  </div>
                  <span className="bom-item-price">₹68,000</span>
                </div>
                <div className="bom-item-row">
                  <div>
                    <span className="bom-item-name">Anodized Aluminum Mounting Rail Kit</span>
                    <span className="bom-item-qty">x 4 sets</span>
                  </div>
                  <span className="bom-item-price">₹22,000</span>
                </div>
                <div className="bom-item-row">
                  <div>
                    <span className="bom-item-name">AC & DC Protection DBs with SPD</span>
                    <span className="bom-item-qty">x 2 boxes</span>
                  </div>
                  <span className="bom-item-price">₹18,000</span>
                </div>
                <div className="bom-item-row">
                  <div>
                    <span className="bom-item-name">Solar Cables, MC4 & Earthing Rods</span>
                    <span className="bom-item-qty">40m kit</span>
                  </div>
                  <span className="bom-item-price">₹12,000</span>
                </div>
              </div>

              <div className="bom-summary-box">
                <div>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>Total Package: ₹2,85,000 · Central Subsidy: -₹78,000</div>
                  <div style={{ fontSize: '15px', fontWeight: '800', color: '#0f172a' }}>
                    Net Payable: ₹2,07,000
                  </div>
                </div>
                <button
                  type="button"
                  className="add-assignment-btn"
                  style={{ width: 'auto', padding: '6px 14px', fontSize: '12px' }}
                  onClick={() => {
                    setAdvancePaid(true);
                    showToast({
                      type: 'success',
                      title: 'Order Confirmed',
                      message: '20% Advance (₹41,400) received! Sent to Warehouse staging.',
                    });
                  }}
                >
                  <DollarSign size={14} />
                  <span>{advancePaid ? 'Advance Paid ✓' : 'Pay 20% Advance'}</span>
                </button>
              </div>
            </div>

            {/* Col 3: Upcoming Rooftop Survey & Appointments */}
            <div className="bento-card">
              <div className="bento-card-header">
                <h3 className="bento-card-title">Survey & Site Visits</h3>
                <span className="event-pill">
                  <Calendar size={12} color="#4f46e5" />
                  <span>May 2026</span>
                </span>
              </div>

              <div className="floating-event-card">
                <div className="event-top-row">
                  <span className="event-title-badge">
                    <span>Upcoming Visit</span>
                    <span className="event-status-dot" />
                  </span>
                  <span className="otp-badge">OTP: 849 201</span>
                </div>
                <p className="event-sub-info">
                  Technician Rooftop Shadow Raytracing & Load Audit | Karthik Nair
                </p>
                <div className="event-pills-row">
                  <span className="event-pill">
                    <Calendar size={12} color="#4f46e5" />
                    <span>Sat, 18 May</span>
                  </span>
                  <span className="event-pill">
                    <Clock size={12} color="#4f46e5" />
                    <span>11:00 AM - 12:30 PM</span>
                  </span>
                </div>
              </div>

              <div className="notification-item-compact" style={{ marginTop: '12px' }}>
                <div className="notif-top">
                  <span className="notif-title">Verification Pin for Technician</span>
                  <Shield size={14} color="#6366f1" />
                </div>
                <p className="notif-desc">
                  Share OTP <strong>849 201</strong> with the field engineer upon arrival to authenticate the visit and unlock checklist logging.
                </p>
              </div>
            </div>
          </>
        )}

        {/* ======================= SALES ROW 2 ======================= */}
        {activeRole === 'sales' && (
          <>
            {/* Col 1: Incoming Enquiries & Lead Qualification Queue */}
            <div className="bento-card">
              <div className="bento-card-header">
                <h3 className="bento-card-title">Incoming Leads Queue</h3>
                <button
                  type="button"
                  className="bento-header-btn"
                  onClick={() => showToast({ type: 'info', title: 'Leads', message: 'Queue refreshed.' })}
                >
                  <Clock size={13} />
                  <span>Refresh</span>
                </button>
              </div>

              <div className="today-tasks-list">
                <div className="today-task-row">
                  <div className="task-name-col">
                    <h5>Rahul Verma · Indiranagar</h5>
                    <span>7.5 kW Sanctioned · Preferred: 5kW</span>
                  </div>
                  <button
                    type="button"
                    className="tag-badge"
                    style={{ background: '#ecfdf5', color: '#047857', border: 'none', cursor: 'pointer' }}
                    onClick={() => showToast({ type: 'success', title: 'Lead Qualified', message: 'Rahul Verma marked qualified.' })}
                  >
                    Qualify ✓
                  </button>
                </div>

                <div className="today-task-row">
                  <div className="task-name-col">
                    <h5>Priya Sharma · Whitefield</h5>
                    <span>5.0 kW Sanctioned · Bill ₹2,800/mo</span>
                  </div>
                  <span className="status-chip-green">Qualified</span>
                </div>

                <div className="today-task-row">
                  <div className="task-name-col">
                    <h5>Rajesh Hegde · Koramangala</h5>
                    <span>10.0 kW Commercial · 3-Phase</span>
                  </div>
                  <button
                    type="button"
                    className="tag-badge"
                    style={{ background: '#fffbeb', color: '#b45309', border: 'none', cursor: 'pointer' }}
                    onClick={() => showToast({ type: 'info', title: 'Clarification', message: 'Clarification email sent.' })}
                  >
                    Clarify ?
                  </button>
                </div>
              </div>
            </div>

            {/* Col 2: 1–5 kW Package BOM Automatic Generator */}
            <div className="bento-card">
              <div className="bento-card-header">
                <h3 className="bento-card-title">Automatic BOM Generator</h3>
                <span className="event-pill" style={{ color: '#4f46e5' }}>
                  Margin: {BOM_PACKAGES[activePkg].margin}
                </span>
              </div>

              {/* Package Selector Pills */}
              <div className="bom-pkg-selector">
                {Object.keys(BOM_PACKAGES).map((pkgKey) => (
                  <button
                    key={pkgKey}
                    type="button"
                    className={`bom-pkg-btn ${activePkg === pkgKey ? 'active' : ''}`}
                    onClick={() => setActivePkg(pkgKey)}
                  >
                    {pkgKey} Package
                  </button>
                ))}
              </div>

              {/* Automatic BOM Exploded View */}
              <div className="bom-breakdown-list">
                <div className="bom-item-row">
                  <span className="bom-item-name">{BOM_PACKAGES[activePkg].panels}</span>
                  <Check size={14} color="#10b981" />
                </div>
                <div className="bom-item-row">
                  <span className="bom-item-name">{BOM_PACKAGES[activePkg].inverter}</span>
                  <Check size={14} color="#10b981" />
                </div>
                <div className="bom-item-row">
                  <span className="bom-item-name">{BOM_PACKAGES[activePkg].structures}</span>
                  <Check size={14} color="#10b981" />
                </div>
              </div>

              <div className="bom-summary-box">
                <div>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>
                    Package: ₹{BOM_PACKAGES[activePkg].price.toLocaleString('en-IN')} · Subsidy: -₹{BOM_PACKAGES[activePkg].subsidy.toLocaleString('en-IN')}
                  </div>
                  <div style={{ fontSize: '14px', fontWeight: '800', color: '#0f172a' }}>
                    Customer Net: ₹{(BOM_PACKAGES[activePkg].price - BOM_PACKAGES[activePkg].subsidy).toLocaleString('en-IN')}
                  </div>
                </div>
                <button
                  type="button"
                  className="add-assignment-btn"
                  style={{ width: 'auto', padding: '6px 12px', fontSize: '11.5px' }}
                  onClick={() =>
                    showToast({
                      type: 'success',
                      title: 'Proposal Sent',
                      message: `Official quotation for ${activePkg} dispatched to customer.`,
                    })
                  }
                >
                  <FileText size={13} />
                  <span>Send Proposal</span>
                </button>
              </div>
            </div>

            {/* Col 3: Survey Scheduling & Technician Dispatch */}
            <div className="bento-card">
              <div className="bento-card-header">
                <h3 className="bento-card-title">Survey Dispatch</h3>
                <span className="priority-badge-high">Ready</span>
              </div>

              <div className="floating-event-card">
                <div className="event-top-row">
                  <span className="event-title-badge">
                    <span>Dispatch Pending</span>
                    <span className="event-status-dot" />
                  </span>
                </div>
                <h5 style={{ margin: '6px 0 2px 0', fontSize: '13px', fontWeight: '700' }}>
                  Rahul Verma · Indiranagar 5kW
                </h5>
                <p className="event-sub-info">RCC Flat Roof · Shadow Raytracing Required</p>
                <div className="event-pills-row">
                  <span className="event-pill">
                    <Wrench size={12} color="#4f46e5" />
                    <span>Assign: Karthik Nair</span>
                  </span>
                  <span className="event-pill">
                    <Calendar size={12} color="#4f46e5" />
                    <span>Sat, 18 May</span>
                  </span>
                </div>
              </div>

              <button
                type="button"
                className="add-assignment-btn"
                style={{ marginTop: '12px' }}
                onClick={() =>
                  showToast({
                    type: 'success',
                    title: 'Survey Dispatched',
                    message: 'Karthik Nair assigned to Indiranagar site survey with customer OTP generated.',
                  })
                }
              >
                <ArrowRight size={14} />
                <span>Dispatch Site Engineering Survey</span>
              </button>
            </div>
          </>
        )}

        {/* ======================= TECHNICIAN ROW 2 ======================= */}
        {activeRole === 'technician' && (
          <>
            {/* Col 1: Active Work Order & OTP Check-in */}
            <div className="bento-card">
              <div className="bento-card-header">
                <h3 className="bento-card-title">Active Work Order</h3>
                <span className="status-chip-green">In Progress</span>
              </div>

              <div className="assignment-tags-row">
                <span className="tag-badge">WO-2026-088</span>
                <span className="tag-badge">5kW Indiranagar</span>
                <span className="priority-badge-high">High</span>
              </div>

              <h4 className="assignment-main-title">
                Customer: Arun Kumar · #42, 4th Cross, Indiranagar
              </h4>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#64748b', marginBottom: '14px' }}>
                <Phone size={13} color="#4f46e5" />
                <span>+91 98450 12345</span>
                <span style={{ margin: '0 4px' }}>·</span>
                <MapPin size={13} color="#4f46e5" />
                <span>Bangalore East</span>
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  className="syscache-input"
                  placeholder="Enter Customer OTP (849201)…"
                  value={otpInput}
                  onChange={(e) => setOtpInput(e.target.value)}
                  style={{ height: '36px', fontSize: '12px' }}
                />
                <button
                  type="button"
                  className="add-assignment-btn"
                  style={{ width: 'auto', padding: '0 14px', height: '36px' }}
                  onClick={() => {
                    setOtpVerified(true);
                    showToast({
                      type: 'success',
                      title: 'OTP Verified',
                      message: 'Check-in confirmed! Work order checklist active.',
                    });
                  }}
                >
                  <span>{otpVerified ? 'Verified ✓' : 'Verify'}</span>
                </button>
              </div>
            </div>

            {/* Col 2: Mandatory Technical Feasibility Checklist & Evidence */}
            <div className="bento-card">
              <div className="bento-card-header">
                <div>
                  <h3 className="bento-card-title">Technical Checklist</h3>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>
                    {techChecklist.filter((c) => c.done).length} / {techChecklist.length} Verified
                  </span>
                </div>
                <button
                  type="button"
                  className="bento-header-btn"
                  onClick={() =>
                    showToast({
                      type: 'info',
                      title: 'Camera',
                      message: 'GPS Camera opened. Capturing rooftop azimuth.',
                    })
                  }
                >
                  <Upload size={13} />
                  <span>Upload Photos</span>
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {techChecklist.map((item) => (
                  <div
                    key={item.id}
                    className={`tech-checklist-item ${item.done ? 'checked' : ''}`}
                    onClick={() => toggleTechCheck(item.id)}
                  >
                    <CheckCircle2 size={16} color={item.done ? '#10b981' : '#cbd5e1'} />
                    <span style={{ flex: 1, textDecoration: item.done ? 'none' : 'none' }}>
                      {item.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Col 3: Daily Route Schedule */}
            <div className="bento-card">
              <div className="bento-card-header">
                <h3 className="bento-card-title">Daily Route Schedule</h3>
                <span className="event-pill">
                  <Calendar size={12} color="#4f46e5" />
                  <span>18 May</span>
                </span>
              </div>

              <div className="cal-agenda-timeline">
                <div>
                  <div className="timeline-slot-header">10:00 AM - 12:30 PM</div>
                  <div className="timeline-agenda-item" style={{ marginTop: '6px' }}>
                    <div className="agenda-left">
                      <div className="agenda-icon-box">
                        <MapPin size={16} />
                      </div>
                      <div>
                        <h5 className="agenda-title">Indiranagar 5kW Site Survey</h5>
                        <p className="agenda-sub">Arun Kumar · Shadow raytracing & load audit</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <div className="timeline-slot-header">02:30 PM - 04:45 PM</div>
                  <div className="timeline-agenda-item" style={{ marginTop: '6px' }}>
                    <div className="agenda-left">
                      <div className="agenda-icon-box">
                        <Wrench size={16} />
                      </div>
                      <div>
                        <h5 className="agenda-title">Whitefield DB Wiring Inspection</h5>
                        <p className="agenda-sub">Priya Sharma · Inverter AC isolator sync</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* ======================= WAREHOUSE ROW 2 ======================= */}
        {(activeRole === 'warehouse_staff' || activeRole === 'warehouse_manager') && (
          <>
            {/* Col 1: Installation Order BOM Picking Slips */}
            <div className="bento-card">
              <div className="bento-card-header">
                <h3 className="bento-card-title">BOM Picking Slips</h3>
                <span className="priority-badge-high">Pick Staging</span>
              </div>

              <div className="floating-event-card">
                <div className="event-top-row">
                  <span className="event-title-badge">
                    <span>Order #SO-2026-0042</span>
                    <span className="event-status-dot" />
                  </span>
                  <span className="event-pill">Crew #1 Indiranagar</span>
                </div>
                <div className="bom-breakdown-list" style={{ marginTop: '8px' }}>
                  <div className="bom-item-row">
                    <span className="bom-item-name">Mono-PERC 540W Bifacial Modules</span>
                    <span className="bom-item-qty">10 units</span>
                  </div>
                  <div className="bom-item-row">
                    <span className="bom-item-name">5kW Hybrid Inverter (INV-HYB-5K)</span>
                    <span className="bom-item-qty">1 unit</span>
                  </div>
                  <div className="bom-item-row">
                    <span className="bom-item-name">Anodized Aluminum Mounting Rail Kit</span>
                    <span className="bom-item-qty">4 pairs</span>
                  </div>
                </div>
              </div>

              <button
                type="button"
                className="add-assignment-btn"
                style={{ marginTop: '12px' }}
                onClick={() =>
                  showToast({
                    type: 'info',
                    title: 'Picking Slip',
                    message: 'BOM materials pulled from rack B4-Row 2 for Order SO-0042.',
                  })
                }
              >
                <Package size={14} />
                <span>Mark Materials Staged for Crew</span>
              </button>
            </div>

            {/* Col 2: Mandatory Serial-Number Barcode Scanner Before Dispatch */}
            <div className="bento-card">
              <div className="bento-card-header">
                <div>
                  <h3 className="bento-card-title">Serial Barcode Scanner</h3>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>
                    Mandatory serial scan before dispatch
                  </span>
                </div>
                <span className="event-pill" style={{ color: scannedSerials.length >= 10 ? '#047857' : '#b45309' }}>
                  {scannedSerials.length}/11 Scanned
                </span>
              </div>

              <form onSubmit={handleAddSerial} className="scanner-input-row">
                <input
                  type="text"
                  className="syscache-input"
                  placeholder="Scan/type serial (e.g. SN-PV540-0986)…"
                  value={serialInput}
                  onChange={(e) => setSerialInput(e.target.value)}
                  style={{ height: '36px', fontSize: '12px' }}
                />
                <button
                  type="submit"
                  className="add-assignment-btn"
                  style={{ width: 'auto', padding: '0 14px', height: '36px' }}
                >
                  <Plus size={14} />
                  <span>Scan</span>
                </button>
              </form>

              <div className="scan-progress-box" style={{ marginTop: '8px' }}>
                <div className="scan-progress-bar">
                  <div
                    className="scan-progress-fill"
                    style={{ width: `${Math.min(100, (scannedSerials.length / 11) * 100)}%` }}
                  />
                </div>
              </div>

              <div className="scanned-serials-list">
                {scannedSerials.map((sn, idx) => (
                  <div key={idx} className="scanned-serial-pill">
                    <span>{sn}</span>
                    <span style={{ fontSize: '10.5px', color: '#059669', fontWeight: '700' }}>Locked ✓</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Col 3: Logistics & Crew Dispatch Schedule */}
            <div className="bento-card">
              <div className="bento-card-header">
                <h3 className="bento-card-title">Logistics Dispatches</h3>
                <span className="event-pill">
                  <Truck size={12} color="#4f46e5" />
                  <span>Today</span>
                </span>
              </div>

              <div className="cal-agenda-timeline">
                <div>
                  <div className="timeline-slot-header">09:00 AM - 10:00 AM</div>
                  <div className="timeline-agenda-item" style={{ marginTop: '6px' }}>
                    <div className="agenda-left">
                      <div className="agenda-icon-box">
                        <Package size={16} />
                      </div>
                      <div>
                        <h5 className="agenda-title">Inbound Container Receiving</h5>
                        <p className="agenda-sub">50x 5kW Hybrid Inverters from Tier-1 OEM</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <div className="timeline-slot-header">01:30 PM - 02:30 PM</div>
                  <div className="timeline-agenda-item" style={{ marginTop: '6px' }}>
                    <div className="agenda-left">
                      <div className="agenda-icon-box">
                        <Truck size={16} />
                      </div>
                      <div>
                        <h5 className="agenda-title">Crew #1 Dispatch: Indiranagar</h5>
                        <p className="agenda-sub">Vehicle KA-01-MJ-8821 · 10 Panels + Inverter</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* ======================= SUPPORT ROW 2 ======================= */}
        {activeRole === 'support' && (
          <>
            {/* Col 1: SysCache Instant Customer Context Snapshot */}
            <div className="bento-card">
              <div className="bento-card-header">
                <div>
                  <h3 className="bento-card-title">SysCache Instant Lookup</h3>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>&lt; 1s search by meter/email</span>
                </div>
                <span className="syscache-badge">  SysCache 18ms</span>
              </div>

              <form onSubmit={handleSysCacheSearch} className="syscache-search-form">
                <input
                  type="text"
                  className="syscache-input"
                  placeholder="Enter Meter (BESCOM-BLR-099234) or Email…"
                  value={sysCacheQuery}
                  onChange={(e) => setSysCacheQuery(e.target.value)}
                  style={{ height: '36px', fontSize: '12px' }}
                />
                <button
                  type="submit"
                  className="add-assignment-btn"
                  style={{ width: 'auto', padding: '0 14px', height: '36px' }}
                >
                  <Search size={14} />
                  <span>Search</span>
                </button>
              </form>

              <div className="syscache-result-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong style={{ fontSize: '13.5px', color: '#0f172a' }}>{sysCacheCustomer.name}</strong>
                  <span className="status-chip-green">Warranty Active</span>
                </div>
                <div style={{ fontSize: '12px', color: '#475569' }}>Meter: {sysCacheCustomer.meter}</div>
                <div style={{ fontSize: '12px', color: '#475569' }}>System: {sysCacheCustomer.system}</div>
                <div style={{ fontSize: '12px', color: '#475569' }}>Inverter S/N: {sysCacheCustomer.inverterSn}</div>
                <div style={{ fontSize: '12px', color: '#059669', fontWeight: '600' }}>
                  Live Power Output: {sysCacheCustomer.livePower} (Normal)
                </div>
              </div>
            </div>

            {/* Col 2: Smart Plain-Language Complaint Intake & Diagnosis */}
            <div className="bento-card">
              <div className="bento-card-header">
                <h3 className="bento-card-title">Smart Complaint Intake</h3>
                <span className="priority-badge-high">AI Diagnostic</span>
              </div>

              <div className="floating-event-card">
                <div className="event-top-row">
                  <span className="event-title-badge">
                    <span>Intake: Inverter LED Error</span>
                    <span className="event-status-dot" />
                  </span>
                </div>
                <p className="event-sub-info" style={{ fontStyle: 'italic', color: '#334155' }}>
                  &ldquo;Customer reported red warning light blinking on hybrid inverter since yesterday afternoon.&rdquo;
                </p>
                <div className="notification-item-compact" style={{ marginTop: '8px', background: '#ffffff' }}>
                  <span style={{ fontSize: '11px', fontWeight: '800', color: '#4f46e5' }}>AUTO-DIAGNOSIS:</span>
                  <p style={{ margin: '2px 0 0 0', fontSize: '11.5px', color: '#0f172a' }}>
                    Fault Code E04: DC Ground Fault Detected (String 2 impedance drop).
                  </p>
                  <p style={{ margin: '2px 0 0 0', fontSize: '11px', color: '#059669', fontWeight: '600' }}>
                    Warranty Decision: 100% In-Warranty Free Repair (Technician dispatched).
                  </p>
                </div>
              </div>

              <button
                type="button"
                className="add-assignment-btn"
                style={{ marginTop: '10px' }}
                onClick={() =>
                  showToast({
                    type: 'success',
                    title: 'Service Work Order Created',
                    message: 'Ticket #TK-1088 assigned to Field Technician for DC ground diagnosis.',
                  })
                }
              >
                <Wrench size={14} />
                <span>Dispatch Warranty Repair Tech</span>
              </button>
            </div>

            {/* Col 3: Active Service Tickets Queue & SLA Countdown */}
            <div className="bento-card">
              <div className="bento-card-header">
                <h3 className="bento-card-title">Service Tickets SLA</h3>
                <span className="event-pill">
                  <Clock size={12} color="#4f46e5" />
                  <span>SLA Live</span>
                </span>
              </div>

              <div className="today-tasks-list">
                <div className="today-task-row">
                  <div className="task-name-col">
                    <h5>TK-1088 · Inverter Red LED</h5>
                    <span>Arun Kumar · Indiranagar</span>
                  </div>
                  <span className="tag-badge" style={{ background: '#fef2f2', color: '#991b1b', border: 'none' }}>
                    1h 45m left
                  </span>
                </div>

                <div className="today-task-row">
                  <div className="task-name-col">
                    <h5>TK-1092 · BESCOM Net-meter</h5>
                    <span>Priya Sharma · Whitefield</span>
                  </div>
                  <span className="tag-badge" style={{ background: '#fffbeb', color: '#b45309', border: 'none' }}>
                    3h 10m left
                  </span>
                </div>

                <div className="today-task-row">
                  <div className="task-name-col">
                    <h5>TK-1079 · AC Isolator Trip</h5>
                    <span>Suresh Reddy · Koramangala</span>
                  </div>
                  <span className="status-chip-green">Resolved ✓</span>
                </div>
              </div>
            </div>
          </>
        )}

        {/* ======================= ADMIN ROW 2 ======================= */}
        {activeRole === 'admin' && (
          <>
            {/* Col 1: Per-Installation Job Profitability Cost Accounting Table */}
            <div className="bento-card">
              <div className="bento-card-header">
                <div>
                  <h3 className="bento-card-title">Job Profitability Accounting</h3>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>
                    Profit = Revenue - Materials - Labour - Permits
                  </span>
                </div>
                <span className="profit-margin-pill">Avg 29.3%</span>
              </div>

              <div className="profitability-grid">
                <div className="profit-row header">
                  <span>Job Ref</span>
                  <span>Revenue</span>
                  <span>Materials</span>
                  <span>Labour</span>
                  <span>Net Profit</span>
                </div>
                <div className="profit-row">
                  <span style={{ fontWeight: '700', color: '#4f46e5' }}>SO-0042 (5kW)</span>
                  <span>₹2,85,000</span>
                  <span>₹1,72,000</span>
                  <span>₹24,000</span>
                  <span style={{ fontWeight: '700', color: '#059669' }}>₹83,000 (29%)</span>
                </div>
                <div className="profit-row">
                  <span style={{ fontWeight: '700', color: '#4f46e5' }}>SO-0043 (3kW)</span>
                  <span>₹1,75,000</span>
                  <span>₹1,04,000</span>
                  <span>₹16,000</span>
                  <span style={{ fontWeight: '700', color: '#059669' }}>₹50,000 (28%)</span>
                </div>
                <div className="profit-row">
                  <span style={{ fontWeight: '700', color: '#4f46e5' }}>SO-0039 (10kW)</span>
                  <span>₹5,40,000</span>
                  <span>₹3,20,000</span>
                  <span>₹45,000</span>
                  <span style={{ fontWeight: '700', color: '#059669' }}>₹1,63,000 (30%)</span>
                </div>
              </div>
            </div>

            {/* Col 2: Customer Invoices & Advance Payment Reconciliation */}
            <div className="bento-card">
              <div className="bento-card-header">
                <h3 className="bento-card-title">Invoices & Advance Payments</h3>
                <span className="priority-badge-high">Reconciliation</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div className="invoice-item-row">
                  <div>
                    <div style={{ fontWeight: '700', color: '#0f172a' }}>INV-2026-081 · Arun Kumar</div>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>20% Booking Advance · ₹57,000</div>
                  </div>
                  <span className="status-chip-green">Paid (UPI)</span>
                </div>

                <div className="invoice-item-row">
                  <div>
                    <div style={{ fontWeight: '700', color: '#0f172a' }}>INV-2026-079 · Priya Sharma</div>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>60% Delivery Stage · ₹1,05,000</div>
                  </div>
                  <span className="status-chip-green">Paid (NEFT)</span>
                </div>

                <div className="invoice-item-row">
                  <div>
                    <div style={{ fontWeight: '700', color: '#0f172a' }}>INV-2026-074 · Rahul Verma</div>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>20% Final Commissioning · ₹57,000</div>
                  </div>
                  <span className="tag-badge" style={{ background: '#fffbeb', color: '#b45309', border: 'none' }}>
                    Due in 3d
                  </span>
                </div>
              </div>

              <button
                type="button"
                className="add-assignment-btn"
                style={{ marginTop: '12px' }}
                onClick={() =>
                  showToast({
                    type: 'success',
                    title: 'GST Tax Invoice',
                    message: 'Official GST invoice drafted with 18% HSN breakdown.',
                  })
                }
              >
                <FileText size={14} />
                <span>Generate Commercial Tax Invoice</span>
              </button>
            </div>

            {/* Col 3: Operations Staff Roster & Technician Commission */}
            <div className="bento-card">
              <div className="bento-card-header">
                <h3 className="bento-card-title">Staff Roster & Payroll</h3>
                <button
                  type="button"
                  className="bento-header-btn"
                  onClick={onNewAction || (() => showToast({ type: 'info', title: 'Staff', message: 'Staff modal opened.' }))}
                >
                  <Plus size={13} />
                  <span>Add Staff</span>
                </button>
              </div>

              <div className="today-tasks-list">
                <div className="today-task-row">
                  <div className="task-name-col">
                    <h5>Karthik Nair · Field Engineer</h5>
                    <span>3 Surveys · 1 Signoff · ₹18,000 Commission</span>
                  </div>
                  <span className="status-chip-green">Active</span>
                </div>

                <div className="today-task-row">
                  <div className="task-name-col">
                    <h5>Suresh Kumar · Lead Installer</h5>
                    <span>2 Installations · ₹24,000 Commission</span>
                  </div>
                  <span className="status-chip-green">Active</span>
                </div>

                <div className="today-task-row">
                  <div className="task-name-col">
                    <h5>Ananya Iyer · Support Lead</h5>
                    <span>52 CSAT Ratings · 98% SLA Speed</span>
                  </div>
                  <span className="status-chip-green">Active</span>
                </div>
              </div>
            </div>
          </>
        )}
      </section>

      {/* ================================================================
          ROW 3: BOTTOM BENTO GRID (SECONDARY ESSENTIALS + FOCUS CARD + GAUGES)
          ================================================================ */}
      <section className="dash-bottom-grid">
        {/* Column 1: Role Secondary Essential Container */}
        <div className="bento-card">
          {activeRole === 'customer' && (
            <>
              <div className="bento-card-header">
                <div>
                  <h3 className="bento-card-title">Installed Equipment & Warranties</h3>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>Delivery-activated warranty records</span>
                </div>
                <button
                  type="button"
                  className="bento-header-btn"
                  onClick={() =>
                    showToast({
                      type: 'success',
                      title: 'Warranty Certificate',
                      message: 'Official 25-Year Warranty PDF downloaded.',
                    })
                  }
                >
                  <Award size={13} />
                  <span>Download Cert</span>
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div className="invoice-item-row">
                  <div>
                    <span style={{ fontWeight: '700', color: '#0f172a' }}>10x Mono-PERC 540W PV Panels</span>
                    <div style={{ fontSize: '11px', color: '#64748b', fontFamily: 'monospace' }}>
                      Serials: SN-PV540-KA-0981 to 0990
                    </div>
                  </div>
                  <span className="status-chip-green">25 Year Warranty</span>
                </div>

                <div className="invoice-item-row">
                  <div>
                    <span style={{ fontWeight: '700', color: '#0f172a' }}>5kW Hybrid Grid-Tie Inverter</span>
                    <div style={{ fontSize: '11px', color: '#64748b', fontFamily: 'monospace' }}>
                      Serial: INV-HYB5K-2026-041
                    </div>
                  </div>
                  <span className="status-chip-green">10 Year Warranty</span>
                </div>

                <div className="invoice-item-row">
                  <div>
                    <span style={{ fontWeight: '700', color: '#0f172a' }}>Anodized Rail Mounting System</span>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>Structural wind-load certified</div>
                  </div>
                  <span className="status-chip-green">10 Year Anti-Rust</span>
                </div>
              </div>
            </>
          )}

          {activeRole === 'sales' && (
            <>
              <div className="bento-card-header">
                <h3 className="bento-card-title">Order Confirmation & Advance Tracker</h3>
                <span className="status-chip-green">Live Pipeline</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div className="invoice-item-row">
                  <div>
                    <div style={{ fontWeight: '700', color: '#0f172a' }}>Order #SO-2026-0042 · Indiranagar</div>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>20% Advance (₹41,400) Received</div>
                  </div>
                  <span className="status-chip-green">Sent to Warehouse</span>
                </div>

                <div className="invoice-item-row">
                  <div>
                    <div style={{ fontWeight: '700', color: '#0f172a' }}>Order #SO-2026-0043 · Whitefield</div>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>20% Advance (₹35,000) Pending</div>
                  </div>
                  <span className="tag-badge" style={{ background: '#fffbeb', color: '#b45309', border: 'none' }}>
                    Payment Link Sent
                  </span>
                </div>

                <div className="invoice-item-row">
                  <div>
                    <div style={{ fontWeight: '700', color: '#0f172a' }}>Order #SO-2026-0041 · Koramangala</div>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>20% Advance (₹57,000) Received</div>
                  </div>
                  <span className="status-chip-green">Dispatched</span>
                </div>
              </div>
            </>
          )}

          {activeRole === 'technician' && (
            <>
              <div className="bento-card-header">
                <div>
                  <h3 className="bento-card-title">Customer Digital Signature</h3>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>Mandatory signoff on completion</span>
                </div>
                <span className="event-pill" style={{ color: signatureSigned ? '#047857' : '#4f46e5' }}>
                  {signatureSigned ? 'Signed ✓' : 'Pending Signoff'}
                </span>
              </div>

              <div
                className="signature-preview-box"
                onClick={() => {
                  setSignatureSigned(!signatureSigned);
                  showToast({
                    type: 'success',
                    title: signatureSigned ? 'Signature Cleared' : 'Digitally Signed',
                    message: signatureSigned
                      ? 'Signature cleared.'
                      : 'Customer Arun Kumar digitally signed the completion signoff.',
                  });
                }}
              >
                {signatureSigned ? (
                  <div style={{ textAlign: 'center' }}>
                    <div className="signature-signed">Arun Kumar</div>
                    <div style={{ fontSize: '10.5px', color: '#059669', marginTop: '2px' }}>
                      Digitally Verified · SHA-256 Timestamp 18 May 2026, 14:32 IST
                    </div>
                  </div>
                ) : (
                  <div>
                    <div style={{ fontSize: '12px', fontWeight: '600' }}>Click here to capture Customer Signature</div>
                    <div style={{ fontSize: '10.5px', color: '#94a3b8' }}>Touchscreen or mouse signoff</div>
                  </div>
                )}
              </div>

              <div style={{ fontSize: '11.5px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={14} color="#10b981" />
                <span>Hardware Serials Verified: 10x PV Modules + 1x Inverter match dispatch slip.</span>
              </div>
            </>
          )}

          {(activeRole === 'warehouse_staff' || activeRole === 'warehouse_manager') && (
            <>
              <div className="bento-card-header">
                <h3 className="bento-card-title">StockSense Real-Time Inventory</h3>
                <span className="event-pill">Live Warehouse</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div className="invoice-item-row">
                  <div>
                    <span style={{ fontWeight: '700', color: '#0f172a' }}>Mono-PERC 540W Bifacial Panels</span>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>142 in stock · 14 units buffer</div>
                  </div>
                  <span className="tag-badge" style={{ background: '#fef2f2', color: '#991b1b', border: 'none' }}>
                    Low Buffer Alert
                  </span>
                </div>

                <div className="invoice-item-row">
                  <div>
                    <span style={{ fontWeight: '700', color: '#0f172a' }}>5kW Hybrid Grid-Tie Inverters</span>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>38 in stock · 12 allocated</div>
                  </div>
                  <span className="status-chip-green">Healthy</span>
                </div>

                <div className="invoice-item-row">
                  <div>
                    <span style={{ fontWeight: '700', color: '#0f172a' }}>Anodized Aluminum Mounting Rails</span>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>85 pairs in stock</div>
                  </div>
                  <span className="status-chip-green">Healthy</span>
                </div>
              </div>
            </>
          )}

          {activeRole === 'support' && (
            <>
              <div className="bento-card-header">
                <h3 className="bento-card-title">Warranty Coverage Engine & DISCOM</h3>
                <span className="priority-badge-high">Billing Engine</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div className="invoice-item-row">
                  <div>
                    <span style={{ fontWeight: '700', color: '#0f172a' }}>In-Warranty Replacement Rule</span>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>Within 10 Years · Free Parts & Labour</div>
                  </div>
                  <span className="status-chip-green">₹0 Customer Charge</span>
                </div>

                <div className="invoice-item-row">
                  <div>
                    <span style={{ fontWeight: '700', color: '#0f172a' }}>Out-of-Warranty Service Rule</span>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>Post 10 Years or Physical Damage</div>
                  </div>
                  <span className="tag-badge" style={{ background: '#fffbeb', color: '#b45309', border: 'none' }}>
                    Parts + ₹1,500 Visit
                  </span>
                </div>

                <div className="invoice-item-row">
                  <div>
                    <span style={{ fontWeight: '700', color: '#0f172a' }}>BESCOM Net-Metering Tracker</span>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>14 Synchronizations in flight</div>
                  </div>
                  <span className="event-pill" style={{ color: '#4f46e5' }}>Avg 4.2 Days</span>
                </div>
              </div>
            </>
          )}

          {activeRole === 'admin' && (
            <>
              <div className="bento-card-header">
                <h3 className="bento-card-title">PM Surya Ghar Subsidy Claims</h3>
                <span className="status-chip-green">National Portal</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div className="subsidy-claim-row">
                  <div>
                    <span style={{ fontWeight: '700', color: '#0f172a' }}>Claim #SUB-KA-0042 · Arun Kumar</span>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>5 kW Hybrid System · ₹78,000</div>
                  </div>
                  <span className="status-chip-green">Portal Approved</span>
                </div>

                <div className="subsidy-claim-row">
                  <div>
                    <span style={{ fontWeight: '700', color: '#0f172a' }}>Claim #SUB-KA-0039 · Suresh Reddy</span>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>10 kW Commercial · ₹78,000</div>
                  </div>
                  <span className="status-chip-green">DBT Disbursed</span>
                </div>

                <div className="subsidy-claim-row">
                  <div>
                    <span style={{ fontWeight: '700', color: '#0f172a' }}>Claim #SUB-KA-0045 · Priya Sharma</span>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>3 kW Single Phase · ₹78,000</div>
                  </div>
                  <span className="tag-badge" style={{ background: '#fffbeb', color: '#b45309', border: 'none' }}>
                    DISCOM Verification
                  </span>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Column 2: Role Focus Card (REPLACED "Go premium!") */}
        <div className="dash-focus-card">
          <div className="focus-illustration-box">
            {activeRole === 'sales' ? (
              <TrendingUp size={36} color="#ffffff" />
            ) : activeRole === 'technician' ? (
              <Wrench size={36} color="#ffffff" />
            ) : activeRole.startsWith('warehouse') ? (
              <Package size={36} color="#ffffff" />
            ) : activeRole === 'support' ? (
              <Headphones size={36} color="#ffffff" />
            ) : activeRole === 'admin' ? (
              <Shield size={36} color="#ffffff" />
            ) : (
              <Sun size={36} color="#ffffff" />
            )}
          </div>
          <h3 className="focus-title">{config.focusCard.title}</h3>
          <p className="focus-sub">{config.focusCard.sub}</p>
          <button
            type="button"
            className="focus-cta-btn"
            onClick={config.focusCard.action}
          >
            {config.focusCard.buttonText}
          </button>
        </div>

        {/* Column 3: Metrics & Upcoming Meeting */}
        <div className="dash-col-metrics">
          {/* Upper: 2 Circular Progress Gauges */}
          <div className="gauges-card">
            {/* Gauge 1 */}
            <div className="gauge-item">
              <div className="gauge-svg-box">
                <svg width="48" height="48" viewBox="0 0 36 36">
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="#e2e8f0"
                    strokeWidth="3.2"
                  />
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="3.2"
                    strokeDasharray={`${parseInt(config.gauge1.percent, 10)}, 100`}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="gauge-center-text">{config.gauge1.percent}</div>
              </div>
              <div className="gauge-info">
                <span className="gauge-category">{config.gauge1.cat}</span>
                <span className="gauge-title">{config.gauge1.title}</span>
                <span className="gauge-subnote">{config.gauge1.sub}</span>
              </div>
            </div>

            {/* Gauge 2 */}
            <div className="gauge-item">
              <div className="gauge-svg-box">
                <svg width="48" height="48" viewBox="0 0 36 36">
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="#e2e8f0"
                    strokeWidth="3.2"
                  />
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="#6366f1"
                    strokeWidth="3.2"
                    strokeDasharray={`${parseInt(config.gauge2.percent, 10)}, 100`}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="gauge-center-text">{config.gauge2.percent}</div>
              </div>
              <div className="gauge-info">
                <span className="gauge-category">{config.gauge2.cat}</span>
                <span className="gauge-title">{config.gauge2.title}</span>
                <span className="gauge-subnote">{config.gauge2.sub}</span>
              </div>
            </div>
          </div>

          {/* Lower: Meeting Briefing Card */}
          <div className="board-meeting-card">
            <div className="board-meeting-header">
              <h4 className="board-meeting-title">{config.briefing.title}</h4>
              <button type="button" className="bento-header-btn">
                <Edit2 size={13} />
                <span>Edit</span>
              </button>
            </div>
            <p className="board-meeting-time">{config.briefing.time}</p>
            <p className="board-meeting-desc">{config.briefing.desc}</p>
            <div className="board-meeting-actions">
              <button
                type="button"
                className="btn-reschedule"
                onClick={() =>
                  showToast({
                    type: 'info',
                    title: 'Reschedule',
                    message: 'Calendar scheduler opened for alternative slot.',
                  })
                }
              >
                Reschedule
              </button>
              <button
                type="button"
                className="btn-accept-invite"
                onClick={() =>
                  showToast({
                    type: 'success',
                    title: 'Confirmed',
                    message: 'Meeting session confirmed on your calendar.',
                  })
                }
              >
                Accept invite
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default DashboardView;
