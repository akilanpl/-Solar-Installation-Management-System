import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from '../../router/Router';
import { AppShell } from '../../components/AppShell/AppShell';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { Badge } from '../../components/Badge/Badge';
import { TextField } from '../../components/TextField/TextField';
import { StatusProgress } from '../../components/StatusProgress/StatusProgress';
import { LoadingState } from '../../components/LoadingState/LoadingState';
import { ErrorState } from '../../components/ErrorState/ErrorState';
import { api } from '../../services/api';
import {
  formatCapacity,
  formatInrFromPaise,
  formatWhen,
  formatDateTime,
  GRID_LABEL,
} from '../../lib/format';
import {
  ArrowLeft,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Calendar,
  Sun,
  MapPin,
  Clock,
  ShieldCheck,
} from 'lucide-react';
import './EnquiryReview.css';
import '../Customer/EnquiryDetail.css';

export function EnquiryReview({ enquiryId }) {
  const { user, showToast } = useAuth();
  const { navigate } = useRouter();

  const [enquiry, setEnquiry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState(null);

  const [notes, setNotes] = useState('');
  const [assignedTechnician, setAssignedTechnician] = useState('EMP-TECH-001 (Karthik Raja)');

  useEffect(() => {
    setLoading(true);
    api
      .getEnquiry(enquiryId)
      .then((data) => {
        setEnquiry(data);
        setNotes(data.qualification_notes || '');
      })
      .catch((err) => setError(err.message || 'Could not load enquiry.'))
      .finally(() => setLoading(false));
  }, [enquiryId]);

  const handleUpdateStatus = async (newStatus) => {
    setUpdating(true);
    try {
      const updated = await api.updateEnquiryQualification(enquiry.id, {
        status: newStatus,
        qualification_notes: notes || `Status updated to ${newStatus} by ${user?.full_name}`,
        next_action: newStatus === 'survey_scheduled' ? `Assigned to ${assignedTechnician}` : undefined,
      });
      setEnquiry(updated);
      showToast(`Enquiry ${updated.reference} updated to ${newStatus.toUpperCase()}`);
    } catch (err) {
      setError(err.message || 'Failed to update qualification.');
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return (
      <AppShell requiredRole="sales">
        <LoadingState label="Loading engineering data…" />
      </AppShell>
    );
  }

  if (error || !enquiry) {
    return (
      <AppShell requiredRole="sales">
        <ErrorState
          title="Record Unavailable"
          message={error || 'Enquiry record missing.'}
          onRetry={() => navigate('/sales')}
        />
      </AppShell>
    );
  }

  return (
    <AppShell requiredRole="sales">
      <PageHeader
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
            <span>Sales Feasibility: {enquiry.reference}</span>
            <Badge status={enquiry.status} />
          </div>
        }
        description={`Customer: ${enquiry.customer_name} (${enquiry.customer_phone}) · Submitted ${formatWhen(enquiry.created_at)}`}
        action={
          <Button
            variant="outline"
            icon={<ArrowLeft size={16} />}
            onClick={() => navigate('/sales')}
          >
            Back to Sales Queue
          </Button>
        }
      />

      <Card elevated accent="lime" style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '8px' }}>
          Lead Pipeline Stage
        </h3>
        <StatusProgress currentStatus={enquiry.status} />
      </Card>

      {/* Qualification Control Center */}
      <Card accent="violet" style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '18px', fontWeight: '800', color: 'var(--color-white)', marginBottom: '8px' }}>
          ⚡ Sales Qualification Decisions
        </h3>
        <p style={{ fontSize: '13px', color: 'var(--color-white-dim)', marginBottom: '16px' }}>
          Verify shadow raytracing feasibility, transformer capacity headroom, and customer connection sanction load.
        </p>

        <TextField
          label="Engineering Qualification Notes"
          name="notes"
          as="textarea"
          rows={3}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="e.g. South-facing RCC roof verified. Sanctioned load 7 kW allows 5 kW on-grid inverter without transformer upgrade…"
        />

        <div className="action-buttons-group">
          <Button
            variant="primary"
            icon={<CheckCircle size={16} />}
            disabled={updating}
            onClick={() => handleUpdateStatus('qualified')}
          >
            Qualify Solar Lead
          </Button>

          <Button
            variant="secondary"
            icon={<Calendar size={16} />}
            disabled={updating}
            onClick={() => handleUpdateStatus('survey_scheduled')}
          >
            Schedule Site Survey
          </Button>

          <Button
            variant="outline"
            icon={<AlertTriangle size={16} color="var(--color-warning)" />}
            disabled={updating}
            onClick={() => handleUpdateStatus('clarification_requested')}
          >
            Request Clarification
          </Button>

          <Button
            variant="danger"
            icon={<XCircle size={16} />}
            disabled={updating}
            onClick={() => handleUpdateStatus('disqualified')}
          >
            Disqualify Lead
          </Button>
        </div>
      </Card>

      {/* Specification Grids */}
      <div className="detail-grid-2">
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <Sun size={20} color="var(--color-lime)" />
            <h3 style={{ fontSize: '17px', fontWeight: '700' }}>Customer Request Details</h3>
          </div>

          <div className="spec-list">
            <div className="spec-item">
              <span className="spec-key">Target Capacity</span>
              <span className="spec-value" style={{ color: 'var(--color-lime)' }}>
                {formatCapacity(enquiry.preferred_capacity_w)}
              </span>
            </div>

            <div className="spec-item">
              <span className="spec-key">Grid Architecture</span>
              <span className="spec-value">{GRID_LABEL[enquiry.grid_preference] || enquiry.grid_preference}</span>
            </div>

            <div className="spec-item">
              <span className="spec-key">Monthly Electricity Bill</span>
              <span className="spec-value">{formatInrFromPaise(enquiry.monthly_bill_minor)}</span>
            </div>

            <div className="spec-item">
              <span className="spec-key">Roof Composition</span>
              <span className="spec-value">{enquiry.roof_type || 'RCC Flat'}</span>
            </div>

            <div className="spec-item">
              <span className="spec-key">Stated Roof Area</span>
              <span className="spec-value">{enquiry.roof_area_sqft || 800} sq. ft.</span>
            </div>
          </div>
        </Card>

        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <MapPin size={20} color="var(--color-violet-light)" />
            <h3 style={{ fontSize: '17px', fontWeight: '700' }}>Premises & Contact</h3>
          </div>

          <div className="spec-list">
            <div className="spec-item">
              <span className="spec-key">Customer Name</span>
              <span className="spec-value">{enquiry.customer_name}</span>
            </div>

            <div className="spec-item">
              <span className="spec-key">Email Address</span>
              <span className="spec-value">{enquiry.customer_email}</span>
            </div>

            <div className="spec-item">
              <span className="spec-key">Phone</span>
              <span className="spec-value">{enquiry.customer_phone}</span>
            </div>

            <div className="spec-item">
              <span className="spec-key">Site Address</span>
              <span className="spec-value" style={{ textAlign: 'right', maxWidth: '260px' }}>
                {enquiry.installation_address_line1}, {enquiry.city}
              </span>
            </div>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}

