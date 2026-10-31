import React, { useState, useEffect } from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { Badge } from '../../components/Badge/Badge';
import { TextField } from '../../components/TextField/TextField';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { formatWhen } from '../../lib/format';
import { Headphones, Search, Plus, CheckCircle, Clock, AlertCircle } from 'lucide-react';
import './SupportDashboard.css';
import '../Customer/CustomerDashboard.css';

export function SupportDashboard() {
  const { showToast } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [lookupQuery, setLookupQuery] = useState('');
  const [lookupResult, setLookupResult] = useState(null);

  useEffect(() => {
    api.getSupportTickets().then(setTickets);
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
    showToast('Customer operational profile located.');
  };

  return (
    <AppShell requiredRole="support">
      <PageHeader
        title="Customer Care & Operations Ticketing Desk"
        description="Liaise on BESCOM net-metering approvals, National Portal subsidies, and inverter warranty tickets."
        action={
          <Button
            variant="primary"
            icon={<Plus size={16} />}
            onClick={() => showToast('New customer escalation ticket modal opened.')}
          >
            Create Escalation Ticket
          </Button>
        }
      />

      {/* Customer Quick Lookup Tool */}
      <div className="lookup-box-card">
        <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '8px', color: 'var(--color-white)' }}>
          🔍 Fast Customer Technical Lookup
        </h3>
        <p style={{ fontSize: '13px', color: 'var(--color-white-dim)', marginBottom: '14px' }}>
          Enter customer phone or email to inspect meter serial, inverter model, and grid connection state:
        </p>
        <form onSubmit={handleLookup} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
          <div style={{ flex: 1 }}>
            <input
              type="text"
              placeholder="e.g. customer@solarops.dev or 9876543210"
              value={lookupQuery}
              onChange={(e) => setLookupQuery(e.target.value)}
              className="field-input"
            />
          </div>
          <Button type="submit" variant="secondary" icon={<Search size={16} />}>
            Search Customer
          </Button>
        </form>

        {lookupResult && (
          <div style={{ marginTop: '16px', padding: '16px', background: 'var(--color-black-surface)', borderRadius: 'var(--radius-sm)', borderLeft: '3px solid var(--color-lime)' }}>
            <h4 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--color-lime)' }}>
              {lookupResult.name} ({lookupResult.email})
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginTop: '10px', fontSize: '13px' }}>
              <div>
                <span style={{ color: 'var(--color-white-dim)', display: 'block', fontSize: '11px' }}>Installed System</span>
                <strong>{lookupResult.system}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--color-white-dim)', display: 'block', fontSize: '11px' }}>Bidirectional Meter No.</span>
                <strong style={{ fontFamily: 'var(--font-mono)' }}>{lookupResult.meter}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--color-white-dim)', display: 'block', fontSize: '11px' }}>Warranty In-Service</span>
                <strong style={{ color: 'var(--color-lime)' }}>Valid until {lookupResult.warrantyExpires}</strong>
              </div>
            </div>
          </div>
        )}
      </div>

      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: '700' }}>Active Customer Support Queue</h3>
          <span style={{ fontSize: '13px', color: 'var(--color-white-dim)' }}>
            Showing {tickets.length} tickets
          </span>
        </div>

        <div className="solar-table-container">
          <table className="solar-table">
            <thead>
              <tr>
                <th>Ticket Ref</th>
                <th>Customer</th>
                <th>Category</th>
                <th>Subject</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Last Update</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((t) => (
                <tr key={t.id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', color: 'var(--color-lime)' }}>
                    {t.reference}
                  </td>
                  <td style={{ fontWeight: '600', color: 'var(--color-white)' }}>{t.customer_name}</td>
                  <td>
                    <Badge variant="violet">{t.category}</Badge>
                  </td>
                  <td style={{ maxWidth: '300px', whiteSpace: 'normal' }}>{t.subject}</td>
                  <td>
                    <Badge variant={t.priority === 'high' ? 'danger' : t.priority === 'medium' ? 'warning' : 'neutral'}>
                      {t.priority.toUpperCase()}
                    </Badge>
                  </td>
                  <td>
                    <Badge status={t.status} />
                  </td>
                  <td style={{ fontSize: '12px', color: 'var(--color-white-dim)', maxWidth: '240px', whiteSpace: 'normal' }}>
                    {t.last_update}
                  </td>
                  <td>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => showToast(`Ticket ${t.reference} updated to In Progress.`)}
                    >
                      Update
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </AppShell>
  );
}

