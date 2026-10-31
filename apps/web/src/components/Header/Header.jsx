import React, { useState } from 'react';
import {
  Search,
  Bell,
  Settings,
  Download,
  Plus,
  Zap,
  LayoutDashboard,
  Workflow,
  Cpu,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from '../../router/Router';
import { FakeLoginModal } from '../FakeLoginModal/FakeLoginModal';
import { homeForRole } from '../../lib/access';
import './Header.css';

export function Header() {
  const { user, showToast } = useAuth();
  const { path, navigate } = useRouter();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [theme, setTheme] = useState('light');
  const [searchVal, setSearchVal] = useState('');
  const [fakeLoginOpen, setFakeLoginOpen] = useState(false);

  const homePath = user ? homeForRole(user.role) : '/login';

  const handleExport = () => {
    showToast({
      type: 'success',
      title: 'Export Generated',
      message: 'Solar operations report exported as solarops-report.xls',
    });
  };

  const handleNewProject = () => {
    if (user?.role === 'customer') {
      navigate('/customer/enquiries/new');
    } else {
      showToast({
        type: 'info',
        title: 'New Board Modal',
        message: 'Project creation workflow initialized for this workspace.',
      });
    }
  };

  return (
    <>
      <header className="top-nav-bar" aria-label="Main Navigation">
        {/* Left: Tabs & Pill Search */}
        <div className="top-nav-left">
          <nav className="top-nav-tabs" aria-label="Dashboard views">
            <button
              type="button"
              className={`top-nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('dashboard');
                navigate(homePath);
              }}
            >
              <LayoutDashboard size={16} />
              <span>Dashboard</span>
            </button>

            <button
              type="button"
              className={`top-nav-tab ${activeTab === 'workflows' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('workflows');
                showToast({
                  type: 'info',
                  title: 'Workflows View',
                  message: 'Rooftop survey & installation pipelines active.',
                });
              }}
            >
              <Workflow size={16} />
              <span>Workflows</span>
            </button>

            <button
              type="button"
              className={`top-nav-tab ${activeTab === 'integrations' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('integrations');
                showToast({
                  type: 'info',
                  title: 'Grid Telemetry',
                  message: 'Net-metering & inverter telemetry feeds connected.',
                });
              }}
            >
              <Cpu size={16} />
              <span>Integrations</span>
            </button>
          </nav>

          {/* Pill Search Bar */}
          <div className="top-nav-search-box">
            <Search size={16} className="top-nav-search-icon" />
            <input
              type="text"
              className="top-nav-search-input"
              placeholder="Search or type command"
              value={searchVal}
              onChange={(e) => setSearchVal(e.target.value)}
              aria-label="Search dashboard"
            />
          </div>
        </div>

        {/* Right: Theme Toggle, Notifications, Settings, Export, Add New */}
        <div className="top-nav-right">
          {/* Light / Dark Mode Toggle Pill */}
          <div className="theme-toggle-pill" role="group" aria-label="Theme mode switcher">
            <button
              type="button"
              className={`theme-pill-btn ${theme === 'light' ? 'active' : 'inactive'}`}
              onClick={() => setTheme('light')}
            >
              <span>✦</span>
              <span>Light</span>
            </button>
            <button
              type="button"
              className={`theme-pill-btn ${theme === 'dark' ? 'active' : 'inactive'}`}
              onClick={() => {
                setTheme('dark');
                showToast({
                  type: 'info',
                  title: 'Theme Preference',
                  message: 'High-contrast light layout active.',
                });
              }}
            >
              <span>🌙</span>
              <span>Dark</span>
            </button>
          </div>

          {/* Notifications Bell */}
          <button
            type="button"
            className="top-icon-btn"
            title="Notifications"
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

          {/* Export Data Button */}
          <button
            type="button"
            className="export-data-btn"
            onClick={handleExport}
            title="Export operational summary"
          >
            <Download size={14} />
            <span>Export data .xls</span>
          </button>

          {/* Primary Action Button */}
          <button
            type="button"
            className="primary-board-btn"
            onClick={handleNewProject}
            title="Create new solar project or board"
          >
            <Plus size={16} />
            <span>Add new board</span>
          </button>

          {/* 1-Click Demo Bypass Helper */}
          <button
            type="button"
            className="bypass-trigger-pill"
            onClick={() => setFakeLoginOpen(true)}
            title="Instant Role Switcher / Demo Bypass"
          >
            <Zap size={14} color="#f59e0b" />
            <span>Bypass</span>
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
