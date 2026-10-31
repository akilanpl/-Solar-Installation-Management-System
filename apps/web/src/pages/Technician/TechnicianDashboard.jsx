import React, { useState, useEffect } from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { Badge } from '../../components/Badge/Badge';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import {
  HardHat,
  Check,
  CheckCircle2,
  Clock,
  MapPin,
  Calendar,
  Camera,
  Upload,
} from 'lucide-react';
import './TechnicianDashboard.css';

export function TechnicianDashboard() {
  const { user, showToast } = useAuth();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchJobs = () => {
    setLoading(true);
    api
      .getTechnicianJobs()
      .then(setJobs)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleToggleCheck = async (jobId, checkId) => {
    const updated = await api.toggleJobChecklistItem(jobId, checkId);
    setJobs([...updated]);
    showToast('Survey checklist progress saved to offline cache');
  };

  return (
    <AppShell requiredRole="technician">
      <PageHeader
        title={`Field Operations: ${user?.full_name || 'Karthik Raja'}`}
        description="Active site surveys, rooftop shadow ray-tracing checklists, and inverter commissioning visits."
        action={
          <Button variant="outline" size="sm" icon={<Clock size={14} />} onClick={fetchJobs}>
            Refresh Tasks
          </Button>
        }
      />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {jobs.map((job) => {
          const completedCount = job.checklist.filter((c) => c.done).length;
          const totalCount = job.checklist.length;
          const isAllDone = completedCount === totalCount;

          return (
            <div key={job.id} className="tech-job-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '13px', fontWeight: '800', color: 'var(--color-lime)', fontFamily: 'var(--font-mono)' }}>
                      {job.reference}
                    </span>
                    <Badge variant={job.status === 'assigned' ? 'violet' : 'warning'}>
                      {job.status.toUpperCase()}
                    </Badge>
                  </div>
                  <h3 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--color-white)', marginTop: '4px' }}>
                    {job.type}
                  </h3>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <Button size="sm" variant="outline" icon={<Camera size={14} />}>
                    Upload Site Photo
                  </Button>
                  {isAllDone && (
                    <Button
                      size="sm"
                      variant="primary"
                      icon={<CheckCircle2 size={14} />}
                      onClick={() => showToast(`Survey ${job.reference} submitted to sales review queue.`)}
                    >
                      Sign Off Inspection
                    </Button>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '18px', margin: '14px 0', fontSize: '13px', color: 'var(--color-white-dim)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <HardHat size={16} color="var(--color-lime)" />
                  <span style={{ color: 'var(--color-white)' }}>{job.client_name}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <MapPin size={16} color="var(--color-violet-light)" />
                  <span>{job.location}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Calendar size={16} />
                  <span>{job.date}</span>
                </div>
              </div>

              {/* Interactive Checklist */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-white-dim)' }}>
                    Field Verification Checklist ({completedCount} of {totalCount} verified)
                  </span>
                  <span style={{ fontSize: '12px', color: 'var(--color-lime)', fontWeight: '700' }}>
                    {Math.round((completedCount / totalCount) * 100)}% Complete
                  </span>
                </div>

                <div className="tech-checklist-group">
                  {job.checklist.map((item) => (
                    <div
                      key={item.id}
                      className={`tech-checklist-item ${item.done ? 'done' : ''}`}
                      onClick={() => handleToggleCheck(job.id, item.id)}
                    >
                      <div className="tech-checkbox">
                        {item.done && <Check size={13} strokeWidth={3} />}
                      </div>
                      <span>{item.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </AppShell>
  );
}

