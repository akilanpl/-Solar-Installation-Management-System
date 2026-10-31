import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from '../../router/Router';
import { canAccessPath, homeForRole } from '../../lib/access';
import { Header } from '../Header/Header';
import { Sidebar } from '../Sidebar/Sidebar';
import { LoadingState } from '../LoadingState/LoadingState';
import { CustomerAccessibility } from '../CustomerAccessibility/CustomerAccessibility';
import { ShieldAlert } from 'lucide-react';
import './AppShell.css';

export function AppShell({ children, requiredRole = null }) {
  const { user, loading } = useAuth();
  const { path, navigate } = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      navigate(`/login?next=${encodeURIComponent(path)}`);
    }
  }, [user, loading, path, navigate]);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f6f7fb' }}>
        <LoadingState label="Verifying SolarOps Session…" />
      </div>
    );
  }

  if (!user) {
    return null;
  }

  // Role validation
  const hasAccess = requiredRole ? user.role === requiredRole || user.role === 'admin' : canAccessPath(user.role, path);

  if (!hasAccess) {
    return (
      <div className="app-shell-layout">
        <Sidebar />
        <div className="app-shell-main">
          <Header />
          <div className="app-shell-content">
            <div className="access-denied-box">
              <ShieldAlert size={48} color="#ef4444" style={{ marginBottom: '16px' }} />
              <h2 style={{ fontSize: '22px', fontWeight: '700', marginBottom: '8px', color: '#111827' }}>Access Restricted</h2>
              <p style={{ color: '#64748b', marginBottom: '24px', fontSize: '14px', lineHeight: '1.5' }}>
                Your current account ({user.role}) is not authorized to view this operational zone.
              </p>
              <button
                type="button"
                className="primary-board-btn"
                style={{ margin: '0 auto' }}
                onClick={() => navigate(homeForRole(user.role))}
              >
                Return to My Dashboard
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const isCustomerScope =
    user.role === 'customer' ||
    path.startsWith('/customer') ||
    path.startsWith('/store');

  return (
    <div className="app-shell-layout">
      <Sidebar />
      <div className="app-shell-main">
        <Header />
        <main className="app-shell-content">{children}</main>
      </div>
      {isCustomerScope && <CustomerAccessibility />}
    </div>
  );
}

export default AppShell;
