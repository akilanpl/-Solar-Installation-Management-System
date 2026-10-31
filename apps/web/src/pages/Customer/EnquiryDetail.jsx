import React, { useState, useEffect } from 'react';
import { useRouter } from '../../router/Router';
import { AppShell } from '../../components/AppShell/AppShell';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { Badge } from '../../components/Badge/Badge';
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
  Sun,
  MapPin,
  Calendar,
  FileCheck,
  CheckCircle2,
  Clock,
  MessageSquare,
} from 'lucide-react';
import './EnquiryDetail.css';

export function EnquiryDetail({ enquiryId }) {
  const { navigate } = useRouter();
  const [enquiry, setEnquiry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    api
      .getEnquiry(enquiryId)
      .then(setEnquiry)
      .catch((err) => setError(err.message || 'Could not load enquiry details.'))
      .finally(() => setLoading(false));
  }, [enquiryId]);

  if (loading) {
    return (
      <AppShell>
        <LoadingState label="Loading solar project specifications…" />
      </AppShell>
    );
  }

  if (error || !enquiry) {
    return (
      <AppShell>
        <ErrorState
          title="Project Not Found"
          message={error || 'Unable to locate enquiry record.'}
          onRetry={() => navigate('/customer')}
        />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
            <span>{enquiry.reference}</span>
            <Badge status={enquiry.status} />
          </div>
        }
        description={`Registered on ${formatWhen(enquiry.created_at)} for ${enquiry.customer_name}`}
        action={
          <Button
            variant="outline"
            icon={<ArrowLeft size={16} />}
            onClick={() => navigate('/customer')}
          >
            Back to Overview
          </Button>
        }
      />

      {/* Visual Status Progression */}
      <Card elevated>
        <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '8px' }}>
          Project Milestones & Deployment Phase
        </h3>
        <StatusProgress currentStatus={enquiry.status} />
      </Card>

      <div className="detail-grid-2">
        {/* Technical System Specs */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <Sun size={20} color="var(--color-lime)" />
            <h3 style={{ fontSize: '17px', fontWeight: '700' }}>System Parameters</h3>
          </div>

          <div className="spec-list">
            <div className="spec-item">
              <span className="spec-key">Target Solar Capacity</span>
              <span className="spec-value" style={{ color: 'var(--color-lime)' }}>
                {formatCapacity(enquiry.preferred_capacity_w)}
              </span>
            </div>

            <div className="spec-item">
              <span className="spec-key">Grid Interconnection</span>
              <span className="spec-value">{GRID_LABEL[enquiry.grid_preference] || enquiry.grid_preference}</span>
            </div>

            <div className="spec-item">
              <span className="spec-key">Monthly Utility Bill</span>
              <span className="spec-value">{formatInrFromPaise(enquiry.monthly_bill_minor)}</span>
            </div>

            <div className="spec-item">
              <span className="spec-key">Roof Structure</span>
              <span className="spec-value">{enquiry.roof_type || 'RCC Flat'}</span>
            </div>

            <div className="spec-item">
              <span className="spec-key">Available Shadow-Free Area</span>
              <span className="spec-value">{enquiry.roof_area_sqft || 800} sq. ft.</span>
            </div>

            <div className="spec-item">
              <span className="spec-key">Est. Monthly Generation</span>
              <span className="spec-value">
                ~{Math.round((enquiry.preferred_capacity_w / 1000) * 4.3 * 30)} Units (kWh)
              </span>
            </div>
          </div>
        </Card>

        {/* Site & Location Details */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <MapPin size={20} color="var(--color-violet-light)" />
            <h3 style={{ fontSize: '17px', fontWeight: '700' }}>Installation Site Address</h3>
          </div>

          <div className="spec-list">
            <div className="spec-item">
              <span className="spec-key">Customer Name</span>
              <span className="spec-value">{enquiry.customer_name}</span>
            </div>

            <div className="spec-item">
              <span className="spec-key">Contact Phone</span>
              <span className="spec-value">{enquiry.customer_phone}</span>
            </div>

            <div className="spec-item">
              <span className="spec-key">Premises Address</span>
              <span className="spec-value" style={{ textAlign: 'right', maxWidth: '280px' }}>
                {enquiry.installation_address_line1}
                {enquiry.installation_address_line2 ? `, ${enquiry.installation_address_line2}` : ''}
              </span>
            </div>

            <div className="spec-item">
              <span className="spec-key">City / State</span>
              <span className="spec-value">
                {enquiry.city}, {enquiry.state} - {enquiry.postal_code}
              </span>
            </div>

            {enquiry.customer_notes && (
              <div style={{ marginTop: '12px', padding: '12px', background: 'var(--color-black-surface)', borderRadius: 'var(--radius-sm)' }}>
                <span style={{ fontSize: '12px', color: 'var(--color-white-dim)', display: 'block', marginBottom: '4px' }}>
                  Customer Notes:
                </span>
                <p style={{ fontSize: '13px', color: 'var(--color-white)' }}>{enquiry.customer_notes}</p>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Engineering Qualification & Timeline */}
      <div className="detail-grid-2">
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <FileCheck size={20} color="var(--color-lime)" />
            <h3 style={{ fontSize: '17px', fontWeight: '700' }}>Sales Qualification Status</h3>
          </div>

          {enquiry.qualification_notes ? (
            <div style={{ padding: '16px', background: 'var(--color-black-surface)', borderRadius: 'var(--radius-sm)', borderLeft: '4px solid var(--color-lime)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-lime)' }}>
                  Engineer Review Summary
                </span>
                {enquiry.qualifier_name && (
                  <span style={{ fontSize: '11px', color: 'var(--color-white-dim)' }}>
                    Evaluated by: {enquiry.qualifier_name}
                  </span>
                )}
              </div>
              <p style={{ fontSize: '13.5px', color: 'var(--color-white)' }}>
                {enquiry.qualification_notes}
              </p>
            </div>
          ) : (
            <p style={{ fontSize: '13px', color: 'var(--color-white-dim)' }}>
              This enquiry is queued for engineering team feasibility review. Technical team will verify sanction load and roof azimuth orientation shortly.
            </p>
          )}
        </Card>

        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <Clock size={20} color="var(--color-violet-light)" />
            <h3 style={{ fontSize: '17px', fontWeight: '700' }}>Activity Timeline</h3>
          </div>

          <div className="timeline-list">
            {(enquiry.timeline || []).map((step, idx) => (
              <div key={idx} className="timeline-item">
                <span className="timeline-marker" />
                <div className="timeline-content">
                  <span className="timeline-step">{step.step}</span>
                  <span className="timeline-detail">{step.detail}</span>
                  <span className="timeline-time">{formatDateTime(step.time)}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </AppShell>
  );
}

