import React, { useState, useEffect } from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { Badge } from '../../components/Badge/Badge';
import { api } from '../../services/api';
import { MapPin, Calendar, HardHat, CheckCircle2, Clock } from 'lucide-react';
import './SalesSurveys.css';

export function SalesSurveys() {
  const [jobs, setJobs] = useState([]);

  useEffect(() => {
    api.getTechnicianJobs().then(setJobs);
  }, []);

  return (
    <AppShell>
      <PageHeader
        title="Field Site Surveys & Structural Verification"
        description="Monitor technician shadow analysis, 3D azimuth measurements, and roof structural integrity checks."
      />

      <div className="surveys-grid">
        {jobs.map((job) => (
          <div key={job.id} className="survey-card">
            <div className="survey-card-header">
              <span className="survey-ref">{job.reference}</span>
              <Badge variant={job.status === 'assigned' ? 'violet' : 'warning'}>
                {job.status.toUpperCase()}
              </Badge>
            </div>

            <h4 className="survey-title">{job.type}</h4>

            <div className="survey-meta-item">
              <HardHat size={16} color="var(--color-lime)" />
              <span>Client: {job.client_name}</span>
            </div>

            <div className="survey-meta-item">
              <MapPin size={16} color="var(--color-white-dim)" />
              <span>{job.location}</span>
            </div>

            <div className="survey-meta-item">
              <Calendar size={16} color="var(--color-white-dim)" />
              <span>{job.date}</span>
            </div>

            <div style={{ marginTop: '8px', paddingTop: '10px', borderTop: '1px solid var(--color-border-subtle)' }}>
              <span style={{ fontSize: '11px', color: 'var(--color-white-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Checklist Progress ({job.checklist.filter((c) => c.done).length}/{job.checklist.length})
              </span>
              <div style={{ width: '100%', height: '4px', background: 'var(--color-border)', borderRadius: '2px', marginTop: '6px', overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${(job.checklist.filter((c) => c.done).length / job.checklist.length) * 100}%`,
                    height: '100%',
                    background: 'var(--color-lime)',
                  }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </AppShell>
  );
}

