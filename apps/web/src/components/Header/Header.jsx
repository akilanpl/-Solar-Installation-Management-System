import React, { useState } from 'react';
import {
  Bell,
  Settings,
  Zap,
  LayoutDashboard,
  User,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from '../../router/Router';
import { FakeLoginModal } from '../FakeLoginModal/FakeLoginModal';
import { homeForRole } from '../../lib/access';
import './Header.css';

export function Header() {
  const { user, showToast } = useAuth();
  const { navigate } = useRouter();
  const [fakeLoginOpen, setFakeLoginOpen] = useState(false);

  const homePath = user ? homeForRole(user.role) : '/login';
  const roleLabel = user?.role ? user.role.replace(/_/g, ' ') : 'Customer';

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

        {/* Right: Role Badge, Notifications, Settings, Bypass Switcher */}
        <div className="top-nav-right">
          {/* User Role Badge */}
          <div className="top-user-pill">
            <span className="top-user-avatar">
              {user?.full_name
                ? user.full_name
                    .split(' ')
                    .map((n) => n[0])
                    .join('')
                    .substring(0, 2)
                    .toUpperCase()
                : 'SO'}
            </span>
            <div className="top-user-meta">
              <span className="top-user-name">{user?.full_name || 'User'}</span>
              <span className="top-user-role">{roleLabel}</span>
            </div>
          </div>

          {/* Notifications Bell */}
          <button
            type="button"
            className="top-icon-btn"
            title="Notifications & Alerts"
            onClick={() =>
              showToast({
                type: 'info',
                title: 'Notifications',
                message: '3 rooftop inspection reminders pending.',
              })
            }
          >
            <Bell size={18} />
            <span className="top-icon-dot" />
          </button>

          {/* Settings */}
          <button
            type="button"
            className="top-icon-btn"
            title="Workspace Settings"
            onClick={() =>
              showToast({
                type: 'info',
                title: 'Settings',
                message: 'SolarOps grid operations configurations.',
              })
            }
          >
            <Settings size={18} />
          </button>

          {/* 1-Click Demo Bypass Helper */}
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

      {/* Modal View for Full Persona Switcher */}
      <FakeLoginModal
        isOpen={fakeLoginOpen}
        onClose={() => setFakeLoginOpen(false)}
      />
    </>
  );
}

export default Header;
