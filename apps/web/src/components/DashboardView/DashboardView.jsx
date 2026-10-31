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
  Gift,
  FileText,
  Layers,
  Sparkles,
  Users,
  Paperclip,
  MessageSquare,
  ArrowRight,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from '../../router/Router';
import './DashboardView.css';

export function DashboardView({
  enquiries = [],
  onNewAction,
  roleSpecificCards,
}) {
  const { user, showToast } = useAuth();
  const { navigate } = useRouter();
  const [activeDate, setActiveDate] = useState(18); // Fri 18 active
  const [viewMode, setViewMode] = useState('list'); // 'grid' | 'list'

  const firstName = user?.full_name ? user.full_name.split(' ')[0] : 'James';

  return (
    <div className="dash-container">
      {/* ================================================================
          ROW 1: HERO GREETING & TOP FEATURE CARDS
          ================================================================ */}
      <section className="dash-hero-row" aria-label="Dashboard Overview">
        {/* Left: Big Headline Greeting */}
        <div className="dash-greeting-box">
          <h1 className="dash-greeting-title">
            <span className="dash-greeting-header-line">
              <span>Hi, {firstName}!</span>
              <span className="dash-avatar-cluster">
                <span className="dash-avatar-ring">⚡</span>
              </span>
            </span>
            <span>What are your</span>
            <span>plans for today?</span>
          </h1>
          <p className="dash-greeting-sub">
            This platform is designed to revolutionize the way you organize and access your rooftop solar operations and projects.
          </p>
        </div>

        {/* Right: 4 Feature / Quick-Action Cards */}
        <div className="dash-feature-cards-grid">
          {/* Card 1: Add New (Lavender Dashed with Purple Plus) */}
          <div
            className="dash-feature-card create-new"
            onClick={onNewAction || (() => navigate('/customer/enquiries/new'))}
            title="Create new solar project or enquiry"
            role="button"
            tabIndex={0}
          >
            <div className="dash-create-icon-box">
              <Plus size={22} strokeWidth={2.8} />
            </div>
          </div>

          {/* Card 2: Stay organized */}
          <div
            className="dash-feature-card"
            onClick={() =>
              showToast({
                type: 'info',
                title: 'Pipeline Structure',
                message: 'All residential and commercial project queues are organized.',
              })
            }
          >
            <div className="dash-feature-illustration">
              {/* Playful Calendar / Notes Vector */}
              <svg width="44" height="44" viewBox="0 0 48 48" fill="none">
                <rect x="8" y="10" width="32" height="30" rx="8" stroke="#4F46E5" strokeWidth="2.5" fill="#EEF2FF" />
                <path d="M16 6v6M32 6v6M8 20h32" stroke="#4F46E5" strokeWidth="2.5" strokeLinecap="round" />
                <rect x="14" y="26" width="8" height="8" rx="2" fill="#6366F1" />
                <circle cx="28" cy="30" r="2" fill="#4F46E5" />
              </svg>
            </div>
            <div>
              <h4 className="dash-feature-title">Stay organized</h4>
              <p className="dash-feature-sub">A clear structure for your notes</p>
            </div>
          </div>

          {/* Card 3: Sync your operations */}
          <div
            className="dash-feature-card"
            onClick={() =>
              showToast({
                type: 'success',
                title: 'Telemetry Synced',
                message: 'Active inverters and smart meter telemetry synchronized.',
              })
            }
          >
            <div className="dash-feature-illustration">
              {/* Hanging Notes Vector */}
              <svg width="44" height="44" viewBox="0 0 48 48" fill="none">
                <path d="M6 12C16 16 32 16 42 12" stroke="#4F46E5" strokeWidth="2" strokeLinecap="round" />
                <rect x="12" y="14" width="10" height="14" rx="2" stroke="#4F46E5" strokeWidth="2" fill="#EEF2FF" />
                <rect x="26" y="15" width="10" height="14" rx="2" stroke="#4F46E5" strokeWidth="2" fill="#EEF2FF" />
                <circle cx="17" cy="14" r="1.5" fill="#4F46E5" />
                <circle cx="31" cy="15" r="1.5" fill="#4F46E5" />
              </svg>
            </div>
            <div>
              <h4 className="dash-feature-title">Sync your notes</h4>
              <p className="dash-feature-sub">Ensure that notes are synced</p>
            </div>
          </div>

          {/* Card 4: Collaborate and share */}
          <div
            className="dash-feature-card"
            onClick={() =>
              showToast({
                type: 'info',
                title: 'Workspace Shared',
                message: 'Collaboration link copied to system clipboard.',
              })
            }
          >
            <div className="dash-feature-illustration">
              {/* Shared Cassette / Folder Vector */}
              <svg width="44" height="44" viewBox="0 0 48 48" fill="none">
                <rect x="8" y="12" width="32" height="24" rx="6" stroke="#4F46E5" strokeWidth="2.5" fill="#EEF2FF" />
                <rect x="14" y="18" width="20" height="10" rx="3" stroke="#4F46E5" strokeWidth="2" />
                <circle cx="19" cy="23" r="2" fill="#4F46E5" />
                <circle cx="29" cy="23" r="2" fill="#4F46E5" />
              </svg>
            </div>
            <div>
              <h4 className="dash-feature-title">Collaborate and share</h4>
              <p className="dash-feature-sub">Share notes with colleagues</p>
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================
          ROW 2: MIDDLE BENTO GRID (3 COLUMNS)
          ================================================================ */}
      <section className="dash-middle-grid">
        {/* Column 1: Notifications */}
        <div className="bento-card">
          <div className="bento-card-header">
            <h3 className="bento-card-title">Notifications</h3>
            <button
              type="button"
              className="bento-header-btn"
              onClick={() => showToast({ type: 'info', title: 'Notifications', message: 'Activity feed cleared.' })}
            >
              <Trash2 size={13} />
              <span>Clear</span>
            </button>
          </div>

          {/* Floating Highlight Card */}
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
            <p className="event-sub-info">Landing design meeting | Time: 120 min</p>
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
              <span className="notif-title">Message | Product design</span>
              <MoreHorizontal size={14} color="#94a3b8" style={{ cursor: 'pointer' }} />
            </div>
            <p className="notif-desc">
              Message from Ken Smith: "Hey team, just wanted to check in on the solar proposal review..."
            </p>
          </div>
        </div>

        {/* Column 2: Assignments */}
        <div className="bento-card">
          <div className="bento-card-header">
            <h3 className="bento-card-title">Assignments</h3>
            <button
              type="button"
              className="bento-header-btn"
              onClick={() => showToast({ type: 'info', title: 'Assignments', message: 'Filter & edit view active.' })}
            >
              <Edit2 size={13} />
              <span>Edit</span>
            </button>
          </div>

          <div className="assignment-tags-row">
            <span className="tag-badge">Motion design</span>
            <span className="tag-badge">Logo</span>
            <span className="priority-badge-high">High</span>
          </div>

          <h4 className="assignment-main-title">
            Design a packaging concept for a new product
          </h4>

          <div className="assignment-meta-row">
            <span className="status-chip-green">Package design</span>
            <div className="assignee-box">
              <span className="assignee-avatar">RL</span>
              <span>Rachel Lee</span>
            </div>
          </div>

          <button
            type="button"
            className="add-assignment-btn"
            onClick={onNewAction || (() => navigate('/customer/enquiries/new'))}
          >
            <Plus size={16} />
            <span>Add new assignment</span>
          </button>
        </div>

        {/* Column 3: Calendar & Schedule */}
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

          {/* Timed Agenda */}
          <div className="cal-agenda-timeline">
            <div>
              <div className="timeline-slot-header">04:30-05:00 PM</div>
              <div className="timeline-agenda-item" style={{ marginTop: '8px' }}>
                <div className="agenda-left">
                  <div className="agenda-icon-box">
                    <Users size={16} />
                  </div>
                  <div>
                    <h5 className="agenda-title">Team meeting</h5>
                    <p className="agenda-sub">12:00 - 12:30 • UX/UI design</p>
                  </div>
                </div>
                <MoreHorizontal size={14} color="#94a3b8" />
              </div>
            </div>

            <div>
              <div className="timeline-slot-header">11:30-12:30 PM</div>
              <div className="timeline-agenda-item" style={{ marginTop: '8px' }}>
                <div className="agenda-left">
                  <div className="agenda-icon-box">
                    <CheckCircle2 size={16} />
                  </div>
                  <div>
                    <h5 className="agenda-title">Meeting with new client</h5>
                    <p className="agenda-sub">12:30 - 01:30 PM • Job interview</p>
                  </div>
                </div>
                <MoreHorizontal size={14} color="#94a3b8" />
              </div>
            </div>
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
                <h5>Conduct research</h5>
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
                <h5>Schedule a meeting</h5>
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
                <h5>Send out reminders</h5>
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

        {/* Column 2: Go premium! Promo Card */}
        <div className="go-premium-card">
          <div className="premium-illustration-box">
            {/* Gift Box with Bow Vector matching reference */}
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="8" width="18" height="13" rx="3" fill="rgba(255,255,255,0.2)" />
              <path d="M12 8v13M3 13h18" stroke="#ffffff" strokeWidth="2" />
              <path d="M12 8c-2-2-4-3-5-2s0 4 5 2c5-2 6-3 5-2s-3 0-5 2z" fill="#ffffff" />
            </svg>
          </div>
          <h3 className="premium-title">Go premium!</h3>
          <p className="premium-sub">
            Gain access to a range of benefits designed to enhance your user experience
          </p>
          <button
            type="button"
            className="premium-cta-btn"
            onClick={() =>
              showToast({
                type: 'success',
                title: 'SolarOps Pro',
                message: 'Full telemetry, multi-inverter diagnostics, and priority survey routing active.',
              })
            }
          >
            Find out more
          </button>
        </div>

        {/* Column 3: Metrics Gauges & Board Meeting Card */}
        <div className="dash-col-metrics">
          {/* Upper: 2 Circular Progress Gauges */}
          <div className="gauges-card">
            {/* Gauge 1 (90% Green) */}
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
                    strokeDasharray="90, 100"
                    strokeLinecap="round"
                  />
                </svg>
                <div className="gauge-center-text">90%</div>
              </div>
              <div className="gauge-info">
                <span className="gauge-category">Data Research</span>
                <span className="gauge-title">Marketing</span>
                <span className="gauge-subnote">You marked 5/5. All assignments done!</span>
              </div>
            </div>

            {/* Gauge 2 (65% Coral) */}
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
                    strokeDasharray="65, 100"
                    strokeLinecap="round"
                  />
                </svg>
                <div className="gauge-center-text">65%</div>
              </div>
              <div className="gauge-info">
                <span className="gauge-category">UX/UI Design</span>
                <span className="gauge-title">Typography</span>
                <span className="gauge-subnote">You marked 3/5. 2 assignments left</span>
                <button
                  type="button"
                  className="gauge-check-btn"
                  onClick={() =>
                    showToast({
                      type: 'info',
                      title: 'Milestone Review',
                      message: 'Typography and design tokens validated.',
                    })
                  }
                >
                  Check
                </button>
              </div>
            </div>
          </div>

          {/* Lower: Board Meeting Card */}
          <div className="board-meeting-card">
            <div className="board-meeting-header">
              <h4 className="board-meeting-title">Board meeting</h4>
              <button type="button" className="bento-header-btn">
                <Edit2 size={13} />
                <span>Edit</span>
              </button>
            </div>
            <p className="board-meeting-time">● March 24 at 4:00 PM</p>
            <p className="board-meeting-desc">Meeting with John Smith, 4th floor, room 159</p>
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
                    title: 'Invite Accepted',
                    message: 'Board meeting confirmed on your calendar.',
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

