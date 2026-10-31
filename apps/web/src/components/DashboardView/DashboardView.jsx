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
  const [viewMode, setViewMode] = useState('list'); // 'grid' | 'list'

  const activeRole = role || user?.role || 'customer';
  const firstName = user?.full_name ? user.full_name.split(' ')[0] : 'James';

  // --------------------------------------------------------------------------
  // ROLE-SPECIFIC GREETING & FOCUS DATA
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
              action: () => showToast({ type: 'info', title: 'Lead Queue', message: 'Ready to review incoming leads.' }),
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
            sub: '74 kW commissioned this month across Bangalore residential rooftop cluster.',
            buttonText: 'View Pipeline Target',
            action: () => showToast({ type: 'success', title: 'Target Metrics', message: '74% of target achieved!' }),
          },
          gauge1: { percent: '84%', cat: 'Conversion', title: 'Lead Velocity', sub: '21/25 proposals qualified' },
          gauge2: { percent: '92%', cat: 'SLA Speed', title: 'Quote Turnaround', sub: 'Under 24 hours' },
          agenda: [
            { time: '02:00-02:45 PM', title: 'Technical Feasibility Review', sub: 'Indiranagar 5kW Bifacial Proposal' },
            { time: '04:30-05:15 PM', title: 'Customer Proposal Call', sub: 'With Rahul Verma (Sanctioned 7.5kW)' },
          ],
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
            sub: 'Offline field mode enabled. GPS-tagged roof photos and azimuth measurements automatically queue for sync.',
            buttonText: 'Sync Offline Evidence',
            action: () => showToast({ type: 'success', title: 'Field Sync', message: 'Field photos synced successfully.' }),
          },
          gauge1: { percent: '95%', cat: 'Compliance', title: 'Safety Gear', sub: 'Full harness & boots verified' },
          gauge2: { percent: '80%', cat: 'Checklists', title: 'Site Reports', sub: '4/5 visits signed off' },
          agenda: [
            { time: '10:00-11:30 AM', title: 'Site Inspection: Indiranagar', sub: '5 kW RCC flat roof raytracing' },
            { time: '02:30-03:45 PM', title: 'Inverter DB Wiring Check', sub: 'Whitefield residential site' },
          ],
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
          agenda: [
            { time: '09:00-10:00 AM', title: 'Inbound Container Receiving', sub: '50x 5kW Hybrid Inverters' },
            { time: '01:30-02:30 PM', title: 'Dispatch Staging: Crew #2', sub: '12x Panels + Rail mounts' },
          ],
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
          agenda: [
            { time: '11:00-11:45 AM', title: 'DISCOM Liaison Call', sub: 'BESCOM Circle 4 Net-metering sync' },
            { time: '03:00-03:30 PM', title: 'Customer Warranty Briefing', sub: 'Inverter replacement firmware check' },
          ],
        };

      case 'admin':
        return {
          greetingQuestion: ['System oversight &', 'personnel today?'],
          greetingSub:
            'Provision enterprise personnel, monitor role-based access control, and inspect infrastructure telemetry.',
          featureCards: [
            {
              isAdd: true,
              label: 'Add Staff',
              action: () => showToast({ type: 'info', title: 'Staff Roster', message: 'Employee provisioning open.' }),
            },
            {
              title: 'Total Personnel',
              sub: `${employees.length || 12} Operations staff`,
              icon: <Users size={28} color="#4F46E5" />,
            },
            {
              title: 'Role Permissions',
              sub: 'Strict RBAC active',
              icon: <Shield size={28} color="#4F46E5" />,
            },
            {
              title: 'System Uptime',
              sub: '99.98% High availability',
              icon: <Zap size={28} color="#4F46E5" />,
            },
          ],
          focusCard: {
            title: 'Zero-Trust Security Active',
            sub: 'PostgreSQL connection pool healthy (18ms). HttpOnly session authorization tokens enforced.',
            buttonText: 'Inspect Health Logs',
            action: () => showToast({ type: 'success', title: 'System Status', message: 'All backend microservices green.' }),
          },
          gauge1: { percent: '100%', cat: 'Security', title: 'Compliance', sub: 'Zero unauthorized requests' },
          gauge2: { percent: '99%', cat: 'API Response', title: 'Latency SLA', sub: '< 45ms median response' },
          agenda: [
            { time: '10:00-10:45 AM', title: 'Security Architecture Audit', sub: 'Session token rotation review' },
            { time: '04:00-05:00 PM', title: 'Weekly Operations All-Hands', sub: 'SolarOps Q2 milestones review' },
          ],
        };

      case 'customer':
      default: {
        const totalCapacityWatts = enquiries.reduce((acc, item) => acc + (item.preferred_capacity_w || 0), 0);
        const totalMonthlyBillsPaise = enquiries.reduce((acc, item) => acc + (item.monthly_bill_minor || 0), 0);

        return {
          greetingQuestion: ['What are your', 'plans for today?'],
          greetingSub:
            'Track your rooftop solar installation progress, submit capacity connection requests, and monitor monthly savings.',
          featureCards: [
            {
              isAdd: true,
              label: 'New Solar Enquiry',
              action: onNewAction || (() => navigate('/customer/enquiries/new')),
            },
            {
              title: 'My Enquiries',
              sub: `${enquiries.length} Active project${enquiries.length === 1 ? '' : 's'}`,
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
          agenda: [
            { time: '11:00-11:45 AM', title: 'Technician Rooftop Survey', sub: 'Site feasibility & shadow raytracing' },
            { time: '03:30-04:15 PM', title: 'Proposals & Quotation Review', sub: 'With Senior Solar Consultant' },
          ],
        };
      }
    }
  };

  const config = getRoleConfig();

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
                <span className="dash-avatar-ring">⚡</span>
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
          ROW 2: MIDDLE BENTO GRID (3 COLUMNS)
          ================================================================ */}
      <section className="dash-middle-grid">
        {/* Column 1: Priority Activity / Notifications */}
        <div className="bento-card">
          <div className="bento-card-header">
            <h3 className="bento-card-title">Notifications</h3>
            <button
              type="button"
              className="bento-header-btn"
              onClick={() => showToast({ type: 'info', title: 'Notifications', message: 'Activity queue refreshed.' })}
            >
              <Trash2 size={13} />
              <span>Clear</span>
            </button>
          </div>

          {/* Floating Highlight Event Card */}
          <div className="floating-event-card">
            <div className="event-top-row">
              <span className="event-title-badge">
                <span>Upcoming event</span>
                <span className="event-status-dot" />
              </span>
              <div className="event-actions-row">
                <MoreHorizontal size={16} style={{ cursor: 'pointer' }} />
                <Trash2 size={13} style={{ cursor: 'pointer' }} />
                <Edit2 size={13} style={{ cursor: 'pointer' }} />
              </div>
            </div>
            <p className="event-sub-info">
              {activeRole === 'sales'
                ? 'Solar Feasibility & Quotation Review | Time: 45 min'
                : activeRole === 'technician'
                ? 'Rooftop Shadow Raytracing Visit | Time: 90 min'
                : activeRole.startsWith('warehouse')
                ? 'Material Dispatch Picking Verification | Time: 60 min'
                : activeRole === 'support'
                ? 'BESCOM Net-Metering Verification | Time: 30 min'
                : 'Technician Site Survey Visit | Time: 120 min'}
            </p>
            <div className="event-pills-row">
              <span className="event-pill">
                <Calendar size={12} color="#4f46e5" />
                <span>Sat, 10 May</span>
              </span>
              <span className="event-pill">
                <Clock size={12} color="#4f46e5" />
                <span>11 AM - 11:45 AM</span>
              </span>
            </div>
          </div>

          {/* Secondary Notification */}
          <div className="notification-item-compact">
            <div className="notif-top">
              <span className="notif-title">Message | Operations Desk</span>
              <MoreHorizontal size={14} color="#94a3b8" style={{ cursor: 'pointer' }} />
            </div>
            <p className="notif-desc">
              {activeRole === 'customer'
                ? 'Senior Solar Consultant approved your preliminary 5kW proposal with zero grid downtime.'
                : activeRole === 'sales'
                ? 'New customer enquiry received from Indiranagar with sanctioned load 7.5kW.'
                : activeRole === 'technician'
                ? 'Rooftop structural integrity checklist updated with latest BIS wind-load standards.'
                : activeRole.startsWith('warehouse')
                ? 'Inbound container of 50 hybrid inverters cleared customs inspection.'
                : 'Customer ticket #TK-1088 escalated for bi-directional meter synchronization.'}
            </p>
          </div>
        </div>

        {/* Column 2: Role-Specific Operational Workbench */}
        <div className="bento-card">
          <div className="bento-card-header">
            <h3 className="bento-card-title">
              {activeRole === 'sales'
                ? 'Lead Qualification'
                : activeRole === 'technician'
                ? 'Survey Checklist'
                : activeRole.startsWith('warehouse')
                ? 'Staged Dispatch'
                : activeRole === 'support'
                ? 'Fast Customer Lookup'
                : 'System Configuration'}
            </h3>
            <button
              type="button"
              className="bento-header-btn"
              onClick={() => showToast({ type: 'info', title: 'Edit View', message: 'Details workbench opened.' })}
            >
              <Edit2 size={13} />
              <span>Edit</span>
            </button>
          </div>

          <div className="assignment-tags-row">
            <span className="tag-badge">
              {activeRole === 'sales'
                ? 'Feasibility'
                : activeRole === 'technician'
                ? 'Shadow Check'
                : activeRole.startsWith('warehouse')
                ? 'Material Pick'
                : activeRole === 'support'
                ? 'BESCOM Meter'
                : '5kW Hybrid'}
            </span>
            <span className="tag-badge">
              {activeRole === 'sales'
                ? 'Tariff Model'
                : activeRole === 'technician'
                ? 'Azimuth/Tilt'
                : activeRole.startsWith('warehouse')
                ? '540W Mono-PERC'
                : activeRole === 'support'
                ? 'Warranty Desk'
                : 'Bifacial Modules'}
            </span>
            <span className="priority-badge-high">High</span>
          </div>

          <h4 className="assignment-main-title">
            {activeRole === 'sales'
              ? 'Evaluate electrical sanction & rooftop feasibility for Lead #SO-2026-0042'
              : activeRole === 'technician'
              ? 'Complete shadow raytracing & AC/DC distribution box mounting audit'
              : activeRole.startsWith('warehouse')
              ? 'Verify staging kit: 10x 540W modules & 5kW string inverter'
              : activeRole === 'support'
              ? 'Liaise on bi-directional meter sanction approval for Bangalore South'
              : 'Review custom rooftop solar proposal & DISCOM subsidy breakdown'}
          </h4>

          <div className="assignment-meta-row">
            <span className="status-chip-green">
              {activeRole === 'customer' ? 'Proposal Active' : 'In Progress'}
            </span>
            <div className="assignee-box">
              <span className="assignee-avatar">
                {activeRole === 'customer' ? 'SC' : 'RL'}
              </span>
              <span>
                {activeRole === 'customer' ? 'Solar Consultant' : 'Rachel Lee'}
              </span>
            </div>
          </div>

          <button
            type="button"
            className="add-assignment-btn"
            onClick={
              onNewAction ||
              (() =>
                showToast({
                  type: 'info',
                  title: 'Task Created',
                  message: 'Operational assignment added to the queue.',
                }))
            }
          >
            <Plus size={16} />
            <span>
              {activeRole === 'sales'
                ? 'Review Next Enquiry'
                : activeRole === 'technician'
                ? 'Log Field Checklist Item'
                : activeRole.startsWith('warehouse')
                ? 'Generate Picking Slip'
                : activeRole === 'support'
                ? 'Open New Ticket'
                : 'Add Project Milestone'}
            </span>
          </button>
        </div>

        {/* Column 3: Calendar & Schedule Widget */}
        <div className="bento-card">
          <div className="bento-card-header">
            <h3 className="bento-card-title">May 2026</h3>
            <div style={{ display: 'flex', gap: '6px', color: '#94a3b8' }}>
              <span style={{ cursor: 'pointer', fontSize: '13px' }}>&lt;</span>
              <span style={{ cursor: 'pointer', fontSize: '13px' }}>&gt;</span>
            </div>
          </div>

          {/* Weekly Date Strip */}
          <div className="cal-week-strip">
            {[
              { day: 'Mon', num: 14 },
              { day: 'Tue', num: 15 },
              { day: 'Wed', num: 16 },
              { day: 'Thr', num: 17 },
              { day: 'Fri', num: 18, active: true },
              { day: 'Sat', num: 19 },
              { day: 'Sun', num: 20 },
            ].map((d) => (
              <div
                key={d.num}
                className={`cal-day-cell ${activeDate === d.num ? 'active' : ''}`}
                onClick={() => setActiveDate(d.num)}
              >
                <span>{d.day}</span>
                <span className="cal-day-num">{d.num}</span>
              </div>
            ))}
          </div>

          {/* Timed Agenda Slots */}
          <div className="cal-agenda-timeline">
            {config.agenda.map((item, idx) => (
              <div key={idx}>
                <div className="timeline-slot-header">{item.time}</div>
                <div className="timeline-agenda-item" style={{ marginTop: '8px' }}>
                  <div className="agenda-left">
                    <div className="agenda-icon-box">
                      <Clock size={16} />
                    </div>
                    <div>
                      <h5 className="agenda-title">{item.title}</h5>
                      <p className="agenda-sub">{item.sub}</p>
                    </div>
                  </div>
                  <MoreHorizontal size={14} color="#94a3b8" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ================================================================
          ROW 3: BOTTOM BENTO GRID (3 COLUMNS)
          ================================================================ */}
      <section className="dash-bottom-grid">
        {/* Column 1: Today tasks */}
        <div className="bento-card">
          <div className="bento-card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h3 className="bento-card-title">Today tasks</h3>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <span className="dash-avatar-ring" style={{ width: '22px', height: '22px', fontSize: '10px' }}>👥</span>
              </div>
            </div>

            <div className="tasks-card-header-actions">
              <div className="view-toggles-cluster">
                <button
                  type="button"
                  className={`view-toggle-btn ${viewMode === 'grid' ? 'active' : ''}`}
                  onClick={() => setViewMode('grid')}
                  title="Grid view"
                >
                  <LayoutGrid size={13} />
                </button>
                <button
                  type="button"
                  className={`view-toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
                  onClick={() => setViewMode('list')}
                  title="List view"
                >
                  <List size={13} />
                </button>
              </div>
              <button type="button" className="bento-header-btn">
                <Edit2 size={13} />
                <span>Edit</span>
              </button>
              <button type="button" className="bento-header-btn">
                <Share2 size={13} />
                <span>Share</span>
              </button>
            </div>
          </div>

          <div className="today-tasks-list">
            {/* Task 1 */}
            <div className="today-task-row">
              <div className="task-name-col">
                <h5>
                  {activeRole === 'sales'
                    ? 'Review 5kW rooftop enquiry for Rahul Verma'
                    : activeRole === 'technician'
                    ? 'Conduct rooftop shadow raytracing & azimuth check'
                    : activeRole.startsWith('warehouse')
                    ? 'Staging pick: 10x 540W Bifacial modules'
                    : activeRole === 'support'
                    ? 'Verify bi-directional meter test report'
                    : 'Conduct site feasibility inspection'}
                </h5>
                <span>4 May, 09:20 AM</span>
              </div>
              <div className="task-duration-col">
                <span style={{ fontSize: '10px', color: '#94a3b8', display: 'block' }}>Duration</span>
                <span>02 h 45 m</span>
              </div>
              <div className="task-progress-col">
                <span style={{ fontSize: '11px', fontWeight: '700', color: '#111827' }}>90%</span>
                <div className="task-progress-track">
                  <div className="task-progress-fill" style={{ width: '90%' }} />
                </div>
              </div>
              <div className="task-meta-col">
                <MessageSquare size={13} />
                <span>4</span>
                <Paperclip size={13} />
                <span>16</span>
              </div>
            </div>

            {/* Task 2 */}
            <div className="today-task-row">
              <div className="task-name-col">
                <h5>
                  {activeRole === 'sales'
                    ? 'Schedule technician field survey with Karthik'
                    : activeRole === 'technician'
                    ? 'Measure AC/DC breaker voltage drop & earthing pit'
                    : activeRole.startsWith('warehouse')
                    ? 'Inspect incoming delivery of 50 hybrid inverters'
                    : activeRole === 'support'
                    ? 'Liaise on BESCOM net-metering approval'
                    : 'Review formal BOQ proposal & tariff schedule'}
                </h5>
                <span>14 May, 12:45 AM</span>
              </div>
              <div className="task-duration-col">
                <span style={{ fontSize: '10px', color: '#94a3b8', display: 'block' }}>Duration</span>
                <span>06 h 55 m</span>
              </div>
              <div className="task-progress-col">
                <span style={{ fontSize: '11px', fontWeight: '700', color: '#111827' }}>50%</span>
                <div className="task-progress-track">
                  <div className="task-progress-fill" style={{ width: '50%' }} />
                </div>
              </div>
              <div className="task-meta-col">
                <MessageSquare size={13} />
                <span>4</span>
                <Calendar size={13} />
                <span>3 June</span>
              </div>
            </div>

            {/* Task 3 */}
            <div className="today-task-row">
              <div className="task-name-col">
                <h5>
                  {activeRole === 'sales'
                    ? 'Dispatch formal subsidy application documents'
                    : activeRole === 'technician'
                    ? 'Upload rooftop azimuth photo evidence to cloud'
                    : activeRole.startsWith('warehouse')
                    ? 'Update physical inventory counts for mounting rails'
                    : activeRole === 'support'
                    ? 'Close resolved inverter warranty ticket #TK-1088'
                    : 'Grid net-metering sync confirmation'}
                </h5>
                <span>21 May, 10:30 AM</span>
              </div>
              <div className="task-duration-col">
                <span style={{ fontSize: '10px', color: '#94a3b8', display: 'block' }}>Duration</span>
                <span>01 h 30 m</span>
              </div>
              <div className="task-progress-col">
                <span style={{ fontSize: '11px', fontWeight: '700', color: '#111827' }}>10%</span>
                <div className="task-progress-track">
                  <div className="task-progress-fill" style={{ width: '10%' }} />
                </div>
              </div>
              <div className="task-meta-col">
                <MessageSquare size={13} />
                <span>16</span>
                <Calendar size={13} />
                <span>3 June</span>
              </div>
            </div>
          </div>
        </div>

        {/* Column 2: Role Focus Card (REPLACED "Go premium!") */}
        <div className="go-premium-card" style={{ background: 'linear-gradient(150deg, #605dec 0%, #5b5fc7 50%, #4f46e5 100%)' }}>
          <div className="premium-illustration-box">
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
          <h3 className="premium-title">{config.focusCard.title}</h3>
          <p className="premium-sub">{config.focusCard.sub}</p>
          <button
            type="button"
            className="premium-cta-btn"
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
                <svg width="52" height="52" viewBox="0 0 36 36">
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
                <svg width="52" height="52" viewBox="0 0 36 36">
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="#e2e8f0"
                    strokeWidth="3.2"
                  />
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="#f43f5e"
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
                <button
                  type="button"
                  className="gauge-check-btn"
                  onClick={() =>
                    showToast({
                      type: 'info',
                      title: 'Milestone Review',
                      message: `${config.gauge2.title} validated.`,
                    })
                  }
                >
                  Check
                </button>
              </div>
            </div>
          </div>

          {/* Lower: Meeting Briefing Card */}
          <div className="board-meeting-card">
            <div className="board-meeting-header">
              <h4 className="board-meeting-title">
                {activeRole === 'sales'
                  ? 'Client Technical Briefing'
                  : activeRole === 'technician'
                  ? 'Field Engineering Debrief'
                  : activeRole.startsWith('warehouse')
                  ? 'Logistics Carrier Sync'
                  : activeRole === 'support'
                  ? 'DISCOM Coordination Call'
                  : activeRole === 'admin'
                  ? 'Operations Staff Standup'
                  : 'Technical Consultation'}
              </h4>
              <button type="button" className="bento-header-btn">
                <Edit2 size={13} />
                <span>Edit</span>
              </button>
            </div>
            <p className="board-meeting-time">● Today at 4:00 PM</p>
            <p className="board-meeting-desc">
              {activeRole === 'customer'
                ? 'With Senior Solar Consultant, Rooftop Feasibility review'
                : 'With Engineering Operations Lead, Room 104'}
            </p>
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
