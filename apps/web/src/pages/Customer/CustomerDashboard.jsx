import React, { useState, useEffect } from 'react';
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
import { Sun, Zap, FilePlus, ArrowRight, ShieldCheck, TrendingUp, IndianRupee } from 'lucide-react';
import './CustomerDashboard.css';

export function CustomerDashboard() {
  const { user } = useAuth();
  const { navigate } = useRouter();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchEnquiries = () => {
    setLoading(true);
    setError(null);
    api
      .getEnquiries()
      .then((res) => {
        // Filter customer's own enquiries or show all if demo
        const items = res.items || [];
        setData({
          items,
          total: items.length,
        });
      })
      .catch((err) => {
        setError(err.message || 'Failed to load enquiries.');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchEnquiries();
  }, []);

  // Compute metrics
  const totalCapacityWatts = (data?.items || []).reduce(
    (acc, item) => acc + (item.preferred_capacity_w || 0),
    0
  );
  const totalMonthlyBillsPaise = (data?.items || []).reduce(
    (acc, item) => acc + (item.monthly_bill_minor || 0),
    0
  );

  return (
    <AppShell requiredRole="customer">
      <PageHeader
        title={`Welcome, ${user?.full_name || 'Solar Customer'}`}
        description="Monitor rooftop solar installation progress, submit technical connection requests, and review proposals."
        action={
          <Button
            variant="primary"
            icon={<FilePlus size={16} />}
            onClick={() => navigate('/customer/enquiries/new')}
          >
            New Solar Enquiry
          </Button>
        }
      />

      {/* KPI Stats Grid */}
      <div className="stats-grid-4">
        <Card className="stat-card-kpi">
          <div className="stat-icon-wrapper stat-icon-lime">
            <Sun size={24} />
          </div>
          <div className="stat-kpi-info">
            <span className="stat-kpi-value">{data?.total ?? 0}</span>
            <span className="stat-kpi-label">Total Enquiries</span>
          </div>
        </Card>

        <Card className="stat-card-kpi">
          <div className="stat-icon-wrapper stat-icon-violet">
            <Zap size={24} />
          </div>
          <div className="stat-kpi-info">
            <span className="stat-kpi-value">{formatCapacity(totalCapacityWatts)}</span>
            <span className="stat-kpi-label">Configured Capacity</span>
          </div>
        </Card>

        <Card className="stat-card-kpi">
          <div className="stat-icon-wrapper stat-icon-lime">
            <TrendingUp size={24} />
          </div>
          <div className="stat-kpi-info">
            <span className="stat-kpi-value">
              {formatInrFromPaise(Math.round(totalMonthlyBillsPaise * 0.85))}
            </span>
            <span className="stat-kpi-label">Est. Monthly Savings</span>
          </div>
        </Card>

        <Card className="stat-card-kpi">
          <div className="stat-icon-wrapper stat-icon-violet">
            <ShieldCheck size={24} />
          </div>
          <div className="stat-kpi-info">
            <span className="stat-kpi-value">Active</span>
            <span className="stat-kpi-label">Grid Feasibility</span>
          </div>
        </Card>
      </div>

      {error && <ErrorState message={error} onRetry={fetchEnquiries} />}

      {loading && !data && <LoadingState label="Loading your solar installations…" />}

      {data && data.total === 0 && (
        <EmptyState
          title="No Solar Enquiries Yet"
          body="Take the first step toward clean renewable solar energy. Request a rooftop assessment today."
          action={
            <Button
              variant="primary"
              icon={<FilePlus size={16} />}
              onClick={() => navigate('/customer/enquiries/new')}
            >
              Start New Enquiry
            </Button>
          }
        />
      )}

      {data && data.items.length > 0 && (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '700' }}>My Solar Projects</h3>
            <span style={{ fontSize: '13px', color: 'var(--color-white-dim)' }}>
              Showing {data.items.length} records
            </span>
          </div>

          <div className="solar-table-container">
            <table className="solar-table">
              <thead>
                <tr>
                  <th>Reference</th>
                  <th>Status</th>
                  <th>System Capacity</th>
                  <th>Grid Mode</th>
                  <th>Monthly Bill</th>
                  <th>Date Submitted</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <Link
                        href={`/customer/enquiries/${item.id}`}
                        className="enquiry-ref-link"
                      >
                        {item.reference}
                      </Link>
                    </td>
                    <td>
                      <Badge status={item.status} />
                    </td>
                    <td style={{ fontWeight: '600', color: 'var(--color-white)' }}>
                      {formatCapacity(item.preferred_capacity_w)}
                    </td>
                    <td>{GRID_LABEL[item.grid_preference] || item.grid_preference}</td>
                    <td>{formatInrFromPaise(item.monthly_bill_minor)}</td>
                    <td>{formatWhen(item.created_at)}</td>
                    <td>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => navigate(`/customer/enquiries/${item.id}`)}
                      >
                        <span>Details</span>
                        <ArrowRight size={12} />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </AppShell>
  );
}

