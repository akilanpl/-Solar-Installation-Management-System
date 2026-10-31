import React from 'react';
import { Link, useRouter } from '../../router/Router';
import { useAuth } from '../../context/AuthContext';
import { homeForRole } from '../../lib/access';
import {
  LayoutGrid,
  User,
  Workflow,
  Bell,
  Calendar,
  MessageSquare,
  FileEdit,
  RefreshCw,
} from 'lucide-react';
import './Sidebar.css';

export function Sidebar({ isOpen, onClose }) {
  const { user } = useAuth();
  const { path } = useRouter();

  const homePath = user ? homeForRole(user.role) : '/login';

  return (
    <aside className="dock-sidebar-container" aria-label="Quick Dock Navigation">
      {/* Top Nav Column */}
      <div className="dock-nav-column">
        {/* Active Dashboard Icon (White rounded square) */}
        <Link
          href={homePath}
          className="dock-item-active"
          title="Dashboard Overview"
        >
          <LayoutGrid size={22} strokeWidth={2.4} />
        </Link>

        {/* Profile / Account */}
        <Link
          href={homePath}
          className="dock-nav-btn"
          title={`Signed in as ${user?.full_name || 'User'}`}
        >
          <User size={20} strokeWidth={2} />
        </Link>

        {/* Workflows / Live Status (with green dot indicator) */}
        <Link
          href={homePath}
          className="dock-nav-btn"
          title="Active Workflows"
        >
          <Workflow size={20} strokeWidth={2} />
          <span className="dock-status-dot" />
        </Link>

        {/* Notifications */}
        <button
          type="button"
          className="dock-nav-btn"
          title="Notifications & Alerts"
          onClick={() => {}}
        >
          <Bell size={20} strokeWidth={2} />
        </button>

        {/* Calendar / Schedule */}
        <button
          type="button"
          className="dock-nav-btn"
          title="Calendar & Site Surveys"
          onClick={() => {}}
        >
          <Calendar size={20} strokeWidth={2} />
        </button>

        {/* Messages */}
        <button
          type="button"
          className="dock-nav-btn"
          title="Team & Customer Messages"
          onClick={() => {}}
        >
          <MessageSquare size={20} strokeWidth={2} />
        </button>

        {/* Assignments / Edits */}
        <button
          type="button"
          className="dock-nav-btn"
          title="Task Assignments"
          onClick={() => {}}
        >
          <FileEdit size={20} strokeWidth={2} />
        </button>
      </div>

      {/* Bottom Sync Column */}
      <div className="dock-bottom-column">
        <button
          type="button"
          className="dock-bottom-btn"
          title="Sync Operations Telemetry"
          onClick={() => window.location.reload()}
        >
          <RefreshCw size={17} strokeWidth={2.2} />
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
