import React, { useState, useEffect } from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { DashboardView } from '../../components/DashboardView/DashboardView';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { Badge } from '../../components/Badge/Badge';
import { LoadingState } from '../../components/LoadingState/LoadingState';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { formatWhen } from '../../lib/format';
import { Headphones, Search, Plus, CheckCircle, Clock, AlertCircle } from 'lucide-react';
import './SupportDashboard.css';
import '../Customer/CustomerDashboard.css';

export function SupportDashboard() {
  const { showToast } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lookupQuery, setLookupQuery] = useState('');
  const [lookupResult, setLookupResult] = useState(null);

  useEffect(() => {
    api.getSupportTickets().then((data) => {
      setTickets(data);
      setLoading(false);
    });
  }, []);

  const handleLookup = (e) => {
    e.preventDefault();
    if (!lookupQuery.trim()) return;
    setLookupResult({
      found: true,
      name: 'Arun Kumar',
      email: 'customer@solarops.dev',
      meter: 'BESCOM-KA-BLR-099234',
      system: '5 kW Hybrid (10x 540W Bifacial Modules)',
      sanctionLoad: '7.5 kW',
      warrantyExpires: '24 Oct 2036',
    });
    showToast({
      type: 'success',
      title: 'Customer Profile Located',
      message: 'BESCOM solar connection profile loaded for Arun Kumar.',
    });
  };

  return (
    <AppShell requiredRole="support">
      {loading ? (
        <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <LoadingState label="Loading support operations desk…" />
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          {/* Master Bento Dashboard for Support */}
          <DashboardView
            role="support"
            tickets={tickets}
            onNewAction={() => showToast({ type: 'info', title: 'Support Ticket', message: 'New customer escalation ticket modal opened.' })}
          />

          {/* Customer Fast Lookup Tool */}
          <div className="bento-card" style={{ padding: '28px' }}>
            <h3 className="bento-card-title" style={{ marginBottom: '6px' }}>
              🔍 Fast Customer Technical Lookup
            </h3>
            <p style={{ margin: '0 0 18px 0', fontSize: '13px', color: '#64748b' }}>
              Locate electricity meter number, transformer circle, system warranty expiry, and inverter telemetry.
            </p>

            <form onSubmit={handleLookup} style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '20px' }}>
              <div className="auth-input-box" style={{ flex: 1, minWidth: '280px' }}>
                <input
                  type="text"
                  className="auth-input-control"
                  placeholder="Enter BESCOM Meter No (e.g. BESCOM-KA-BLR-099234) or Email…"
                  value={lookupQuery}
                  onChange={(e) => setLookupQuery(e.target.value)}
                />
              </div>
              <button type="submit" className="primary-board-btn" style={{ height: '48px' }}>
                <Search size={16} />
                <span>Search Customer</span>
              </button>
            </form>

            {lookupResult && (
              <div className="floating-event-card" style={{ padding: '20px', borderLeft: '4px solid #6366f1' }}>
                <h4 style={{ fontSize: '15px', fontWeight: '700', color: '#111827', margin: '0 0 10px 0' }}>
                  {lookupResult.name} · {lookupResult.email}
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', fontSize: '13px' }}>
                  <div>
                    <span style={{ color: '#94a3b8', display: 'block', fontSize: '11px' }}>Bi-Directional Meter:</span>
                    <strong>{lookupResult.meter}</strong>
                  </div>
                  <div>
                    <span style={{ color: '#94a3b8', display: 'block', fontSize: '11px' }}>Installed System:</span>
                    <strong>{lookupResult.system}</strong>
                  </div>
                  <div>
                    <span style={{ color: '#94a3b8', display: 'block', fontSize: '11px' }}>Sanctioned Load:</span>
                    <strong>{lookupResult.sanctionLoad}</strong>
                  </div>
                  <div>
                    <span style={{ color: '#94a3b8', display: 'block', fontSize: '11px' }}>Inverter Warranty:</span>
                    <strong style={{ color: '#10b981' }}>{lookupResult.warrantyExpires}</strong>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Active Support Tickets Table */}
          <div className="bento-card" style={{ padding: '28px' }}>
            <div className="bento-card-header" style={{ marginBottom: '20px' }}>
              <div>
                <h3 className="bento-card-title">Customer Care & Operations Ticketing Desk</h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '12.5px', color: '#64748b' }}>
                  Liaise on BESCOM net-metering approvals, National Portal subsidies, and inverter warranty tickets.
                </p>
              </div>

              <button
                type="button"
                className="primary-board-btn"
                onClick={() => showToast({ type: 'info', title: 'New Ticket', message: 'Escalation ticket modal opened.' })}
              >
                <Plus size={16} />
                <span>Create Escalation Ticket</span>
              </button>
            </div>

            <div className="solar-table-container">
              <table className="solar-table">
                <thead>
                  <tr>
                    <th>Ticket Ref</th>
                    <th>Customer Name</th>
                    <th>Subject / Category</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Logged At</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((t) => (
                    <tr key={t.id}>
                      <td>
                        <span style={{ fontFamily: 'monospace', fontWeight: '700', color: '#111827' }}>
                          {t.reference}
                        </span>
                      </td>
                      <td>
                        <strong style={{ color: '#111827' }}>{t.customer_name}</strong>
                      </td>
                      <td>
                        <div style={{ fontWeight: '600', color: '#111827' }}>{t.subject}</div>
                        <div style={{ fontSize: '12px', color: '#64748b' }}>{t.category}</div>
                      </td>
                      <td>
                        <Badge variant={t.priority === 'urgent' ? 'danger' : t.priority === 'high' ? 'warning' : 'neutral'}>
                          {t.priority}
                        </Badge>
                      </td>
                      <td>
                        <Badge variant={t.status === 'resolved' ? 'success' : 'warning'}>
                          {t.status.replace(/_/g, ' ')}
                        </Badge>
                      </td>
                      <td style={{ fontSize: '12px', color: '#64748b' }}>{formatWhen(t.created_at)}</td>
                      <td>
                        <button
                          type="button"
                          className="bento-header-btn"
                          style={{ color: '#4f46e5', fontWeight: '700' }}
                          onClick={() => showToast({ type: 'success', title: 'Ticket Updated', message: `Ticket ${t.reference} marked In Progress.` })}
                        >
                          <span>Process</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}

export default SupportDashboard;
