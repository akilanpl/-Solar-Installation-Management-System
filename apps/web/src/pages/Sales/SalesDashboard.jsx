import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useRouter, Link } from '../../router/Router';
import { AppShell } from '../../components/AppShell/AppShell';
import { DashboardView } from '../../components/DashboardView/DashboardView';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { Badge } from '../../components/Badge/Badge';
import { LoadingState } from '../../components/LoadingState/LoadingState';
import { EmptyState } from '../../components/EmptyState/EmptyState';
import { ErrorState } from '../../components/ErrorState/ErrorState';
import { api } from '../../services/api';
import { formatCapacity, formatInrFromPaise, formatWhen, GRID_LABEL } from '../../lib/format';
import {
  ClipboardCheck,
  Search,
  Filter,
  ArrowRight,
  TrendingUp,
  Clock,
  Sparkles,
  CheckCircle2,
} from 'lucide-react';
import './SalesDashboard.css';
import '../Customer/CustomerDashboard.css';

const TABS = [
  { key: 'all', label: 'All Enquiries' },
  { key: 'submitted', label: 'Needs Review' },
  { key: 'qualified', label: 'Qualified' },
  { key: 'clarification_requested', label: 'Clarification Needed' },
  { key: 'survey_scheduled', label: 'Survey Scheduled' },
  { key: 'disqualified', label: 'Disqualified' },
];

export function SalesDashboard() {
  const { user, showToast } = useAuth();
  const { navigate } = useRouter();

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const loadData = () => {
    setLoading(true);
    setError(null);
    api
      .getEnquiries()
      .then((res) => {
        setItems(res.items || []);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load enquiries.');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (activeTab !== 'all' && item.status !== activeTab) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const refMatch = item.reference?.toLowerCase().includes(q);
        const nameMatch = item.customer_name?.toLowerCase().includes(q);
        const cityMatch = item.city?.toLowerCase().includes(q);
        const emailMatch = item.customer_email?.toLowerCase().includes(q);
        return refMatch || nameMatch || cityMatch || emailMatch;
      }
      return true;
    });
  }, [items, activeTab, searchQuery]);

  return (
    <AppShell requiredRole="sales">
      {loading ? (
        <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <LoadingState label="Loading sales operations workbench…" />
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          {/* Bento Master Dashboard for Sales */}
          <DashboardView
            role="sales"
            enquiries={items}
            onNewAction={() => showToast({ type: 'info', title: 'Lead Queue', message: 'Ready to qualify next enquiry.' })}
          />

          {/* Dedicated Enquiries Review Section */}
          <div className="bento-card sales-enquiries-card">
            <div className="bento-card-header sales-enquiries-header">
              <div className="sales-title-col">
                <h3 className="bento-card-title">Incoming Customer Enquiries</h3>
                <p className="sales-header-subtitle">
                  Filter, evaluate electrical load parameters, and schedule technician surveys.
                </p>
              </div>

              <div className="sales-search-actions">
                <div className="top-nav-search-box sales-search-box">
                  <Search size={14} className="top-nav-search-icon" />
                  <input
                    type="text"
                    className="top-nav-search-input"
                    placeholder="Search leads…"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                <button
                  type="button"
                  className="export-data-btn"
                  onClick={loadData}
                >
                  <Clock size={13} />
                  <span>Refresh</span>
                </button>
              </div>
            </div>

            {/* Filter Tabs */}
            <div className="sales-filter-tabs" style={{ marginBottom: '18px' }}>
              {TABS.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  className={`sales-tab-btn ${activeTab === tab.key ? 'active' : ''}`}
                  onClick={() => setActiveTab(tab.key)}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Table */}
            {filteredItems.length === 0 ? (
              <EmptyState
                title="No enquiries in this status"
                description="There are currently no customer solar connection requests matching your active filter."
              />
            ) : (
              <div className="solar-table-container">
                <table className="solar-table">
                  <thead>
                    <tr>
                      <th>Ref Number</th>
                      <th>Customer</th>
                      <th>Location</th>
                      <th>Load / Capacity</th>
                      <th>Monthly Bill</th>
                      <th>Grid Phase</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredItems.map((item) => (
                      <tr key={item.id}>
                        <td>
                          <Link href={`/sales/enquiries/${item.id}`} className="enquiry-ref-link">
                            {item.reference}
                          </Link>
                        </td>
                        <td>
                          <div style={{ fontWeight: '600', color: '#111827' }}>{item.customer_name}</div>
                          <div style={{ fontSize: '12px', color: '#64748b' }}>{item.customer_email}</div>
                        </td>
                        <td>{item.city}</td>
                        <td>
                          <strong>{item.sanctioned_load_kw} kW</strong> load
                          <div style={{ fontSize: '11px', color: '#64748b' }}>
                            Preferred: {formatCapacity(item.preferred_capacity_w)}
                          </div>
                        </td>
                        <td>₹{formatInrFromPaise(item.monthly_bill_minor)}</td>
                        <td>{GRID_LABEL[item.grid_phase] || item.grid_phase}</td>
                        <td>
                          <Badge variant={item.status === 'qualified' ? 'success' : item.status === 'disqualified' ? 'danger' : 'warning'}>
                            {item.status.replace(/_/g, ' ')}
                          </Badge>
                        </td>
                        <td>
                          <Link
                            href={`/sales/enquiries/${item.id}`}
                            className="bento-header-btn"
                            style={{ color: '#4f46e5', fontWeight: '700' }}
                          >
                            <span>Review</span>
                            <ArrowRight size={13} />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </AppShell>
  );
}

export default SalesDashboard;
