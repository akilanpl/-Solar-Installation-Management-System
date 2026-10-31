import React, { useState, useEffect } from 'react';
import {
  Bell,
  X,
  CheckCheck,
  Trash2,
  Sun,
  Zap,
  Package,
  CreditCard,
  Shield,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
} from 'lucide-react';
import './NotificationDrawer.css';

export function NotificationDrawer({
  isOpen,
  onClose,
  notifications = [],
  onNotificationClick,
  onMarkAllRead,
  onClearAll,
}) {
  const [filter, setFilter] = useState('all'); // 'all' | 'unread' | 'inspection' | 'grid' | 'dispatch'

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Prevent background scrolling when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const filteredNotifications = notifications.filter((n) => {
    if (filter === 'unread') return !n.read;
    if (filter === 'inspection') return n.category === 'inspection';
    if (filter === 'grid') return n.category === 'grid';
    if (filter === 'dispatch') return n.category === 'dispatch';
    return true;
  });

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'inspection':
        return <Sun size={17} color="#d97706" />;
      case 'grid':
        return <Zap size={17} color="#4f46e5" />;
      case 'dispatch':
        return <Package size={17} color="#0284c7" />;
      case 'payment':
        return <CreditCard size={17} color="#059669" />;
      case 'warning':
        return <AlertTriangle size={17} color="#ef4444" />;
      case 'safety':
      default:
        return <Shield size={17} color="#10b981" />;
    }
  };

  const getCategoryLabel = (category) => {
    switch (category) {
      case 'inspection':
        return 'Site Survey';
      case 'grid':
        return 'BESCOM Grid';
      case 'dispatch':
        return 'Warehouse Dispatch';
      case 'payment':
        return 'Razorpay / Finance';
      default:
        return 'Operations';
    }
  };

  return (
    <>
      {/* Backdrop with defocus blur */}
      <div
        className={`notif-drawer-backdrop ${isOpen ? 'open' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Right-Side Slide-Over Tray */}
      <aside
        className={`notif-drawer-panel ${isOpen ? 'open' : ''}`}
        role="dialog"
        aria-label="SolarOps Notification Center"
        aria-modal="true"
      >
        {/* Drawer Header */}
        <div className="notif-drawer-header">
          <div className="notif-drawer-header-left">
            <div className="notif-drawer-icon-wrap">
              <Bell size={20} color="#4f46e5" />
              {unreadCount > 0 && <span className="notif-drawer-unread-pip" />}
            </div>
            <div>
              <h2 className="notif-drawer-title">Notifications</h2>
              <span className="notif-drawer-subtitle">
                {unreadCount > 0
                  ? `${unreadCount} unread system alert${unreadCount > 1 ? 's' : ''}`
                  : 'All operational alerts acknowledged'}
              </span>
            </div>
          </div>

          <div className="notif-drawer-header-right">
            {unreadCount > 0 && (
              <button
                type="button"
                className="notif-drawer-action-btn"
                onClick={onMarkAllRead}
                title="Mark all notifications as read"
              >
                <CheckCheck size={15} />
                <span>Mark All Read</span>
              </button>
            )}

            <button
              type="button"
              className="notif-drawer-close-btn"
              onClick={onClose}
              title="Close Notification Center (Esc)"
              aria-label="Close"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Filter Tabs Bar */}
        <div className="notif-drawer-filters">
          <button
            type="button"
            className={`notif-tab-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All ({notifications.length})
          </button>
          <button
            type="button"
            className={`notif-tab-btn ${filter === 'unread' ? 'active' : ''}`}
            onClick={() => setFilter('unread')}
          >
            Unread ({unreadCount})
          </button>
          <button
            type="button"
            className={`notif-tab-btn ${filter === 'inspection' ? 'active' : ''}`}
            onClick={() => setFilter('inspection')}
          >
            Surveys
          </button>
          <button
            type="button"
            className={`notif-tab-btn ${filter === 'grid' ? 'active' : ''}`}
            onClick={() => setFilter('grid')}
          >
            DISCOM
          </button>
          <button
            type="button"
            className={`notif-tab-btn ${filter === 'dispatch' ? 'active' : ''}`}
            onClick={() => setFilter('dispatch')}
          >
            Dispatch
          </button>
        </div>

        {/* Scrollable Notification List */}
        <div className="notif-drawer-body">
          {filteredNotifications.length === 0 ? (
            <div className="notif-drawer-empty">
              <div className="empty-circle">
                <CheckCircle2 size={36} color="#10b981" />
              </div>
              <h3 className="empty-title">You're All Caught Up!</h3>
              <p className="empty-desc">
                {filter === 'unread'
                  ? 'There are no unread alerts in your queue right now.'
                  : 'No notifications found matching the selected filter category.'}
              </p>
            </div>
          ) : (
            <div className="notif-cards-stack">
              {filteredNotifications.map((n) => (
                <div
                  key={n.id}
                  className={`notif-card ${n.read ? 'read' : 'unread'}`}
                  onClick={() => onNotificationClick(n.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') onNotificationClick(n.id);
                  }}
                >
                  <div className="notif-card-icon-col">
                    <div className="notif-card-icon-circle">
                      {getCategoryIcon(n.category)}
                    </div>
                  </div>

                  <div className="notif-card-content">
                    <div className="notif-card-top-row">
                      <span className="notif-category-chip">
                        {getCategoryLabel(n.category)}
                      </span>
                      <span className="notif-time-ago">{n.time}</span>
                    </div>

                    <h4 className="notif-card-title">{n.title}</h4>
                    <p className="notif-card-desc">{n.desc}</p>
                  </div>

                  {!n.read && <span className="notif-pulse-dot" />}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Drawer Sticky Footer */}
        <div className="notif-drawer-footer">
          <div className="notif-footer-telemetry">
            <span className="telemetry-live-dot" />
            <span>Telemetry WebSocket Connected · Zero-Loss Stream</span>
          </div>

          {notifications.length > 0 && (
            <button
              type="button"
              className="notif-clear-button"
              onClick={onClearAll}
              title="Clear all alerts from notification history"
            >
              <Trash2 size={14} />
              <span>Clear History</span>
            </button>
          )}
        </div>
      </aside>
    </>
  );
}

export default NotificationDrawer;
