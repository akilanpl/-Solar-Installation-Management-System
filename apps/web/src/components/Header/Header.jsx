import React, { useState } from 'react';
import {
  Bell,
  Settings,
  Zap,
  LayoutDashboard,
  Check,
  CheckCheck,
  Trash2,
  Sun,
  Shield,
  Package,
  CreditCard,
  Sliders,
  CheckCircle2,
  Radio,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from '../../router/Router';
import { FakeLoginModal } from '../FakeLoginModal/FakeLoginModal';
import { Modal } from '../Modal/Modal';
import { homeForRole } from '../../lib/access';
import './Header.css';

export function Header() {
  const { user, showToast } = useAuth();
  const { navigate } = useRouter();
  const [fakeLoginOpen, setFakeLoginOpen] = useState(false);

  // Notifications State
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifFilter, setNotifFilter] = useState('all'); // 'all' | 'unread'
  const [notifications, setNotifications] = useState([
    {
      id: 'notif-1',
      category: 'inspection',
      title: 'Rooftop Inspection Reminder',
      desc: '3 site surveys pending shadow raytracing check (Indiranagar & Whitefield)',
      time: '12m ago',
      read: false,
    },
    {
      id: 'notif-2',
      category: 'grid',
      title: 'BESCOM Net-Meter Approved',
      desc: 'Bi-directional net-meter sanction issued for Arun Kumar (5kW Hybrid)',
      time: '45m ago',
      read: false,
    },
    {
      id: 'notif-3',
      category: 'dispatch',
      title: 'Hardware Dispatch Staged',
      desc: '10x 540W Mono-PERC modules staged in warehouse for Crew Indiranagar',
      time: '2h ago',
      read: false,
    },
    {
      id: 'notif-4',
      category: 'payment',
      title: 'Advance Payment Reconciled',
      desc: '₹57,000 received via Razorpay UPI for Job #SO-0042',
      time: '3h ago',
      read: true,
    },
    {
      id: 'notif-5',
      category: 'safety',
      title: 'Zero-Harm Safety Protocol',
      desc: 'Double-lanyard harness and PPE verified on all rooftop jobs today',
      time: '5h ago',
      read: true,
    },
  ]);

  // Settings State
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, setSettings] = useState({
    discomCircle: 'BESCOM (Bangalore Urban & Rural)',
    defaultCapacity: '5 kW Hybrid Bifacial',
    autoSanctionCalc: true,
    smsDispatchAlerts: true,
    whatsappMilestones: true,
    lowStockReorderAlerts: true,
    visionOsGlass: true,
    telemetryRefreshRate: '15s',
    compactMode: false,
  });

  const homePath = user ? homeForRole(user.role) : '/login';

  const unreadCount = notifications.filter((n) => !n.read).length;

  const filteredNotifications =
    notifFilter === 'unread'
      ? notifications.filter((n) => !n.read)
      : notifications;

  const handleNotificationClick = (id) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
    showToast({
      type: 'info',
      title: 'Alert Acknowledged',
      message: 'Notification marked as read.',
    });
  };

  const handleMarkAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    showToast({
      type: 'success',
      title: 'All Caught Up',
      message: 'All notifications marked as read.',
    });
  };

  const handleClearAll = () => {
    setNotifications([]);
    showToast({
      type: 'info',
      title: 'Alerts Cleared',
      message: 'All notifications removed from notification center.',
    });
  };

  const handleSaveSettings = (e) => {
    e.preventDefault();
    setSettingsOpen(false);
    showToast({
      type: 'success',
      title: 'Settings Saved',
      message: 'Workspace configurations and operational defaults updated.',
    });
  };

  const getCategoryIcon = (cat) => {
    switch (cat) {
      case 'inspection':
        return <Sun size={16} color="#d97706" />;
      case 'grid':
        return <Zap size={16} color="#4f46e5" />;
      case 'dispatch':
        return <Package size={16} color="#0284c7" />;
      case 'payment':
        return <CreditCard size={16} color="#059669" />;
      case 'safety':
      default:
        return <Shield size={16} color="#10b981" />;
    }
  };

  return (
    <>
      <header className="top-nav-bar" aria-label="Main Navigation">
        {/* Left: Clean Dashboard Tab */}
        <div className="top-nav-left">
          <nav className="top-nav-tabs" aria-label="Dashboard views">
            <button
              type="button"
              className="top-nav-tab active"
              onClick={() => navigate(homePath)}
            >
              <LayoutDashboard size={17} />
              <span>Dashboard</span>
            </button>
          </nav>
        </div>

        {/* Right: Notifications, Settings, Bypass Switcher (User pill removed) */}
        <div className="top-nav-right">
          {/* Notifications Bell Button & Working Dropdown */}
          <div className="top-nav-item-wrapper">
            <button
              type="button"
              className={`top-icon-btn ${notifOpen ? 'active' : ''}`}
              title="Notifications & System Alerts"
              onClick={() => {
                setNotifOpen(!notifOpen);
                if (settingsOpen) setSettingsOpen(false);
              }}
              aria-expanded={notifOpen}
            >
              <Bell size={18} />
              {unreadCount > 0 && <span className="top-icon-dot" />}
            </button>

            {/* Notifications Dropdown Panel */}
            {notifOpen && (
              <>
                <div
                  className="top-nav-click-catcher"
                  onClick={() => setNotifOpen(false)}
                />
                <div className="notifications-dropdown" role="region" aria-label="Notifications Panel">
                  <div className="notif-dropdown-header">
                    <div className="notif-header-title-box">
                      <span className="notif-header-title">Notifications</span>
                      {unreadCount > 0 && (
                        <span className="notif-unread-count-pill">
                          {unreadCount} New
                        </span>
                      )}
                    </div>
                    {unreadCount > 0 && (
                      <button
                        type="button"
                        className="notif-mark-read-btn"
                        onClick={handleMarkAllRead}
                        title="Mark all notifications as read"
                      >
                        <CheckCheck size={14} />
                        <span>Mark read</span>
                      </button>
                    )}
                  </div>

                  {/* Filter Pills */}
                  <div className="notif-filter-pills">
                    <button
                      type="button"
                      className={`notif-filter-btn ${notifFilter === 'all' ? 'active' : ''}`}
                      onClick={() => setNotifFilter('all')}
                    >
                      All ({notifications.length})
                    </button>
                    <button
                      type="button"
                      className={`notif-filter-btn ${notifFilter === 'unread' ? 'active' : ''}`}
                      onClick={() => setNotifFilter('unread')}
                    >
                      Unread ({unreadCount})
                    </button>
                  </div>

                  {/* Notification Items List */}
                  <div className="notif-items-list">
                    {filteredNotifications.length === 0 ? (
                      <div className="notif-empty-state">
                        <CheckCircle2 size={24} color="#10b981" />
                        <p>No notifications to display</p>
                      </div>
                    ) : (
                      filteredNotifications.map((n) => (
                        <div
                          key={n.id}
                          className={`notif-item-row ${n.read ? 'read' : 'unread'}`}
                          onClick={() => handleNotificationClick(n.id)}
                          role="button"
                          tabIndex={0}
                        >
                          <div className="notif-item-icon-col">
                            <div className="notif-icon-circle">
                              {getCategoryIcon(n.category)}
                            </div>
                          </div>
                          <div className="notif-item-body-col">
                            <div className="notif-item-top">
                              <span className="notif-item-title">{n.title}</span>
                              <span className="notif-item-time">{n.time}</span>
                            </div>
                            <p className="notif-item-desc">{n.desc}</p>
                          </div>
                          {!n.read && <span className="notif-unread-indicator-dot" />}
                        </div>
                      ))
                    )}
                  </div>

                  {/* Footer Actions */}
                  {notifications.length > 0 && (
                    <div className="notif-dropdown-footer">
                      <button
                        type="button"
                        className="notif-clear-all-btn"
                        onClick={handleClearAll}
                      >
                        <Trash2 size={13} />
                        <span>Clear All Alerts</span>
                      </button>
                      <span className="notif-footer-telemetry">
                        ● Live Sync Active
                      </span>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Settings Button & Working Modal */}
          <div className="top-nav-item-wrapper">
            <button
              type="button"
              className={`top-icon-btn ${settingsOpen ? 'active' : ''}`}
              title="Workspace & Operations Settings"
              onClick={() => {
                setSettingsOpen(true);
                if (notifOpen) setNotifOpen(false);
              }}
            >
              <Settings size={18} />
            </button>
          </div>

          {/* 1-Click Demo Persona Switcher */}
          <button
            type="button"
            className="bypass-trigger-pill"
            onClick={() => setFakeLoginOpen(true)}
            title="Instant Role Switcher / Demo Bypass"
          >
            <Zap size={14} color="#f59e0b" />
            <span>Switch Role</span>
          </button>
        </div>
      </header>

      {/* Working Settings Modal */}
      <Modal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        title="Workspace & Operational Settings"
        maxWidth="620px"
      >
        <form onSubmit={handleSaveSettings} className="workspace-settings-form">
          {/* Section 1: Grid & DISCOM Interconnection */}
          <div className="settings-group-card">
            <h4 className="settings-group-title">
              <Zap size={16} color="#4f46e5" />
              <span>Grid & DISCOM Interconnection Defaults</span>
            </h4>
            <div className="settings-field-row">
              <label className="settings-label" htmlFor="discomCircle">
                Default DISCOM Utility Circle
              </label>
              <select
                id="discomCircle"
                className="settings-select"
                value={settings.discomCircle}
                onChange={(e) =>
                  setSettings({ ...settings, discomCircle: e.target.value })
                }
              >
                <option value="BESCOM (Bangalore Urban & Rural)">BESCOM (Bangalore Urban & Rural)</option>
                <option value="MESCOM (Mangalore & Coastal)">MESCOM (Mangalore & Coastal)</option>
                <option value="HESCOM (Hubli-Dharwad Circle)">HESCOM (Hubli-Dharwad Circle)</option>
                <option value="GESCOM (Gulbarga Division)">GESCOM (Gulbarga Division)</option>
                <option value="CHESCOM (Mysore Division)">CHESCOM (Mysore Division)</option>
              </select>
            </div>

            <div className="settings-field-row">
              <label className="settings-label" htmlFor="defaultCapacity">
                Standard Inverter Architecture
              </label>
              <select
                id="defaultCapacity"
                className="settings-select"
                value={settings.defaultCapacity}
                onChange={(e) =>
                  setSettings({ ...settings, defaultCapacity: e.target.value })
                }
              >
                <option value="3 kW Micro-Inverter (Residential)">3 kW Micro-Inverter (Residential)</option>
                <option value="5 kW Hybrid Bifacial (DCR Compliant)">5 kW Hybrid Bifacial (DCR Compliant)</option>
                <option value="10 kW Commercial String Inverter">10 kW Commercial String Inverter</option>
              </select>
            </div>

            <label className="settings-checkbox-row">
              <input
                type="checkbox"
                checked={settings.autoSanctionCalc}
                onChange={(e) =>
                  setSettings({ ...settings, autoSanctionCalc: e.target.checked })
                }
              />
              <div className="checkbox-text-col">
                <strong>Automatic Sanction Load Ratio Calculation</strong>
                <span>Recommend PV capacity capped at 80% of sanction meter load.</span>
              </div>
            </label>
          </div>

          {/* Section 2: Dispatch & Customer Reminders */}
          <div className="settings-group-card">
            <h4 className="settings-group-title">
              <Bell size={16} color="#059669" />
              <span>Field Dispatch & Automated Notifications</span>
            </h4>

            <label className="settings-checkbox-row">
              <input
                type="checkbox"
                checked={settings.smsDispatchAlerts}
                onChange={(e) =>
                  setSettings({ ...settings, smsDispatchAlerts: e.target.checked })
                }
              />
              <div className="checkbox-text-col">
                <strong>Technician Field Route SMS Reminders</strong>
                <span>Dispatch daily morning itinerary and GPS coordinates to technicians.</span>
              </div>
            </label>

            <label className="settings-checkbox-row">
              <input
                type="checkbox"
                checked={settings.whatsappMilestones}
                onChange={(e) =>
                  setSettings({ ...settings, whatsappMilestones: e.target.checked })
                }
              />
              <div className="checkbox-text-col">
                <strong>Customer WhatsApp Milestone Tracking</strong>
                <span>Dispatches automated stage alerts upon DISCOM sanction and meter sync.</span>
              </div>
            </label>

            <label className="settings-checkbox-row">
              <input
                type="checkbox"
                checked={settings.lowStockReorderAlerts}
                onChange={(e) =>
                  setSettings({ ...settings, lowStockReorderAlerts: e.target.checked })
                }
              />
              <div className="checkbox-text-col">
                <strong>Warehouse Low-Stock Warnings</strong>
                <span>Alert logistics managers when 540W modules dip below 15 units.</span>
              </div>
            </label>
          </div>

          {/* Section 3: Interface & Telemetry */}
          <div className="settings-group-card">
            <h4 className="settings-group-title">
              <Sliders size={16} color="#f59e0b" />
              <span>Interface & Live Telemetry Refresh</span>
            </h4>

            <div className="settings-field-row">
              <label className="settings-label" htmlFor="telemetryRate">
                Live Telemetry Polling Rate
              </label>
              <select
                id="telemetryRate"
                className="settings-select"
                value={settings.telemetryRefreshRate}
                onChange={(e) =>
                  setSettings({ ...settings, telemetryRefreshRate: e.target.value })
                }
              >
                <option value="10s">10 Seconds (Ultra-responsive)</option>
                <option value="15s">15 Seconds (Standard Operations)</option>
                <option value="30s">30 Seconds (Balanced)</option>
                <option value="60s">60 Seconds (Low Power Mode)</option>
              </select>
            </div>

            <label className="settings-checkbox-row">
              <input
                type="checkbox"
                checked={settings.visionOsGlass}
                onChange={(e) =>
                  setSettings({ ...settings, visionOsGlass: e.target.checked })
                }
              />
              <div className="checkbox-text-col">
                <strong>VisionOS Liquid Glass Optical Refraction</strong>
                <span>Enable high-index defocus blur and specular edge highlights.</span>
              </div>
            </label>
          </div>

          {/* Form Actions */}
          <div className="settings-modal-actions">
            <button
              type="button"
              className="settings-btn-cancel"
              onClick={() => setSettingsOpen(false)}
            >
              Cancel
            </button>
            <button type="submit" className="settings-btn-save">
              Save Preferences
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal View for Full Persona Switcher */}
      <FakeLoginModal
        isOpen={fakeLoginOpen}
        onClose={() => setFakeLoginOpen(false)}
      />
    </>
  );
}

export default Header;
