import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useRouter, Link } from '../../router/Router';
import { AppShell } from '../../components/AppShell/AppShell';
import { PageHeader } from '../../components/PageHeader/PageHeader';
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
  const { user } = useAuth();
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
      .then((res) => setItems(res.items || []))
      .catch((err) => setError(err.message || 'Failed to fetch sales queue.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      // Tab filter
      if (activeTab !== 'all' && item.status !== activeTab) {
        return false;
      }
      // Search filter
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

  // Counts
  const pendingCount = items.filter((i) => i.status === 'submitted').length;
  const qualifiedCount = items.filter((i) => i.status === 'qualified').length;
  const surveyCount = items.filter((i) => i.status === 'survey_scheduled').length;

  return (
    <AppShell requiredRole="sales">
      <PageHeader
        title="Sales Operations & Feasibility Workbench"
        description="Screen incoming customer enquiries, evaluate electrical load parameters, and schedule site engineering surveys."
        action={
          <div style={{ display: 'flex', gap: '10px' }}>
            <Button
              variant="outline"
              size="sm"
              icon={<Clock size={14} />}
              onClick={loadData}
            >
              Refresh Queue
            </Button>
          </div>
        }
      />

      {/* KPI Row */}
      <div className="stats-grid-4">
        <Card className="stat-card-kpi">
          <div className="stat-icon-wrapper stat-icon-violet">
            <Clock size={24} />
          </div>
          <div className="stat-kpi-info">
            <span className="stat-kpi-value">{pendingCount}</span>
            <span className="stat-kpi-label">Pending Technical Review</span>
          </div>
        </Card>

        <Card className="stat-card-kpi">
          <div className="stat-icon-wrapper stat-icon-lime">
            <CheckCircle2 size={24} />
          </div>
          <div className="stat-kpi-info">
            <span className="stat-kpi-value">{qualifiedCount}</span>
            <span className="stat-kpi-label">Qualified Leads</span>
          </div>
        </Card>

        <Card className="stat-card-kpi">
          <div className="stat-icon-wrapper stat-icon-lime">
            <TrendingUp size={24} />
          </div>
          <div className="stat-kpi-info">
            <span className="stat-kpi-value">{surveyCount}</span>
            <span className="stat-kpi-label">Surveys in Field</span>
          </div>
        </Card>

        <Card className="stat-card-kpi">
          <div className="stat-icon-wrapper stat-icon-violet">
            <Sparkles size={24} />
          </div>
          <div className="stat-kpi-info">
            <span className="stat-kpi-value">{items.length}</span>
            <span className="stat-kpi-label">Total Pipeline</span>
          </div>
        </Card>
      </div>

      {error && <ErrorState message={error} onRetry={loadData} />}

      <Card>
        {/* Filters and Search Bar */}
        <div className="sales-filter-bar">
          <div className="filter-pills-group">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                className={`filter-pill ${activeTab === tab.key ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="search-box-wrapper">
            <Search size={16} className="search-box-icon" />
            <input
              type="text"
              className="search-box-input"
              placeholder="Search reference, customer, city…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {loading && <LoadingState label="Filtering sales pipeline records…" />}

        {!loading && filteredItems.length === 0 && (
          <EmptyState
            title="No Matching Enquiries"
            body="No solar leads match your selected status tab or search filter."
          />
        )}

        {!loading && filteredItems.length > 0 && (
          <div className="solar-table-container">
            <table className="solar-table">
              <thead>
                <tr>
                  <th>Enquiry Ref</th>
                  <th>Customer</th>
                  <th>Location</th>
                  <th>System Sizing</th>
                  <th>Monthly Bill</th>
                  <th>Status</th>
                  <th>Submitted</th>
                  <th>Workbench</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <Link
                        href={`/sales/enquiries/${item.id}`}
                        className="enquiry-ref-link"
                      >
                        {item.reference}
                      </Link>
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span style={{ fontWeight: '600', color: 'var(--color-white)' }}>
                          {item.customer_name}
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--color-white-dim)' }}>
                          {item.customer_phone}
                        </span>
                      </div>
                    </td>
                    <td>
                      <span>{item.city}</span>
                    </td>
                    <td>
                      <span style={{ color: 'var(--color-lime)', fontWeight: '700' }}>
                        {formatCapacity(item.preferred_capacity_w)}
                      </span>
                      <span style={{ fontSize: '12px', color: 'var(--color-white-dim)', marginLeft: '4px' }}>
                        · {GRID_LABEL[item.grid_preference] || item.grid_preference}
                      </span>
                    </td>
                    <td>{formatInrFromPaise(item.monthly_bill_minor)}</td>
                    <td>
                      <Badge status={item.status} />
                    </td>
                    <td>{formatWhen(item.created_at)}</td>
                    <td>
                      <Button
                        size="sm"
                        variant={item.status === 'submitted' ? 'primary' : 'outline'}
                        onClick={() => navigate(`/sales/enquiries/${item.id}`)}
                      >
                        <span>{item.status === 'submitted' ? 'Review & Qualify' : 'View'}</span>
                        <ArrowRight size={12} />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </AppShell>
  );
}

