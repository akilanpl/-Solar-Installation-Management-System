import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from '../../router/Router';
import { canAccessPath, homeForRole } from '../../lib/access';
import { Header } from '../Header/Header';
import { Sidebar } from '../Sidebar/Sidebar';
import { LoadingState } from '../LoadingState/LoadingState';
import { Button } from '../Button/Button';
import { ShieldAlert } from 'lucide-react';
import './AppShell.css';

export function AppShell({ children, requiredRole = null }) {
  const { user, loading } = useAuth();
  const { path, navigate } = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      navigate(`/login?next=${encodeURIComponent(path)}`);
    }
  }, [user, loading, path, navigate]);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
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
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <div className="app-shell-main">
          <Header onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
          <div className="app-shell-content">
            <div className="access-denied-box">
              <ShieldAlert size={48} color="var(--color-danger)" style={{ marginBottom: '16px' }} />
              <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '8px' }}>Access Restricted</h2>
              <p style={{ color: 'var(--color-white-dim)', marginBottom: '24px', fontSize: '14px' }}>
                Your current account ({user.role}) is not authorized to view this operational zone.
              </p>
              <Button onClick={() => navigate(homeForRole(user.role))}>
                Return to My Dashboard
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell-layout">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="app-shell-main">
        <Header onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
        <main className="app-shell-content">{children}</main>
      </div>
    </div>
  );
}

