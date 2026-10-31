import React, { useState } from 'react';
import { Menu, LogOut, Zap, ShieldCheck } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from '../../router/Router';
import { FakeLoginModal } from '../FakeLoginModal/FakeLoginModal';
import { ROLE_DISPLAY } from '../../lib/access';
import './Header.css';

export function Header({ onToggleSidebar }) {
  const { user, logout } = useAuth();
  const { navigate } = useRouter();
  const [fakeLoginOpen, setFakeLoginOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .map((n) => n[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : 'SO';

  return (
    <>
      <header className="header-bar">
        <div className="header-left">
          <button
            type="button"
            className="mobile-menu-toggle"
            onClick={onToggleSidebar}
            aria-label="Toggle Navigation"
          >
            <Menu size={20} />
          </button>
          <div className="brand-badge-mobile">
            <span style={{ color: 'var(--color-lime)' }}>⚡</span>
            <span>SolarOps</span>
          </div>
        </div>

        <div className="header-right">
          {/* Fast Switch / Fake Login Bypass Trigger */}
          <button
            type="button"
            className="demo-bypass-btn"
            onClick={() => setFakeLoginOpen(true)}
            title="Switch Persona / Fake Login Bypass"
          >
            <Zap size={14} />
            <span>⚡ Demo Bypass</span>
          </button>

          {user && (
            <div className="user-profile-widget">
              <div className="user-avatar">{initials}</div>
              <div className="user-details">
                <span className="user-full-name">{user.full_name}</span>
                <span className="user-role-label">
                  {ROLE_DISPLAY[user.role] || user.role}
                  {user.employee_code ? ` · ${user.employee_code}` : ''}
                </span>
              </div>
            </div>
          )}

          <button
            type="button"
            className="header-logout-btn"
            onClick={handleLogout}
            title="Sign out"
          >
            <LogOut size={14} />
            <span>Exit</span>
          </button>
        </div>
      </header>

      <FakeLoginModal
        isOpen={fakeLoginOpen}
        onClose={() => setFakeLoginOpen(false)}
      />
    </>
  );
}

