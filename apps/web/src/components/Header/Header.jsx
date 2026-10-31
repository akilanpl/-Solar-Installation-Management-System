import React, { useState } from 'react';
import {
  Bell,
  Settings,
  Zap,
  LayoutDashboard,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from '../../router/Router';
import { FakeLoginModal } from '../FakeLoginModal/FakeLoginModal';
import { NotificationDrawer } from '../NotificationDrawer/NotificationDrawer';
import { UserSettingsModal } from '../UserSettingsModal/UserSettingsModal';
import { homeForRole } from '../../lib/access';
import './Header.css';

export function Header() {
  const { user, showToast } = useAuth();
  const { navigate } = useRouter();
  const [fakeLoginOpen, setFakeLoginOpen] = useState(false);

  // Right-Side Notifications Drawer State
  const [notifOpen, setNotifOpen] = useState(false);
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
      desc: 'Bi-directional net-meter sanction issued for Arun Kumar (5kW Hybrid Rooftop)',
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

  // Full-Screen Settings & User Profile State
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

  const handleSaveSettings = (newSettings) => {
    setSettings((prev) => ({ ...prev, ...newSettings }));
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

        {/* Right: Notifications (pop from right), Settings (fullscreen), Persona Switcher */}
        <div className="top-nav-right">
          {/* Notifications Bell Button */}
          <div className="top-nav-item-wrapper">
            <button
              type="button"
              className={`top-icon-btn ${notifOpen ? 'active' : ''}`}
              title="Notifications & System Alerts (Opens Drawer from Right)"
              onClick={() => {
                setNotifOpen(!notifOpen);
                if (settingsOpen) setSettingsOpen(false);
              }}
              aria-expanded={notifOpen}
            >
              <Bell size={18} />
              {unreadCount > 0 && <span className="top-icon-dot" />}
            </button>
          </div>

          {/* Settings Button */}
          <div className="top-nav-item-wrapper">
            <button
              type="button"
              className={`top-icon-btn ${settingsOpen ? 'active' : ''}`}
              title="Account & System Settings (Full Screen)"
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

      {/* Right-Side Slide-Over Notification Drawer */}
      <NotificationDrawer
        isOpen={notifOpen}
        onClose={() => setNotifOpen(false)}
        notifications={notifications}
        onNotificationClick={handleNotificationClick}
        onMarkAllRead={handleMarkAllRead}
        onClearAll={handleClearAll}
      />

      {/* Full-Screen User Settings & Profile Control Center */}
      <UserSettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={settings}
        onSaveSettings={handleSaveSettings}
      />

      {/* Modal View for Full Persona Switcher */}
      <FakeLoginModal
        isOpen={fakeLoginOpen}
        onClose={() => setFakeLoginOpen(false)}
      />
    </>
  );
}

export default Header;
