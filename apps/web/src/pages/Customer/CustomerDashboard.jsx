import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from '../../router/Router';
import { AppShell } from '../../components/AppShell/AppShell';
import { DashboardView } from '../../components/DashboardView/DashboardView';
import { LoadingState } from '../../components/LoadingState/LoadingState';
import { ErrorState } from '../../components/ErrorState/ErrorState';
import { api } from '../../services/api';
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

  return (
    <AppShell requiredRole="customer">
      {loading ? (
        <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <LoadingState label="Loading solar operations dashboard…" />
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={fetchEnquiries} />
      ) : (
        <DashboardView
          role="customer"
          enquiries={data?.items || []}
          onNewAction={() => navigate('/customer/enquiries/new')}
        />
      )}
    </AppShell>
  );
}

export default CustomerDashboard;
