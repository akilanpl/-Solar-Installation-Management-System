import React, { useState, useEffect } from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { DashboardView } from '../../components/DashboardView/DashboardView';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { Badge } from '../../components/Badge/Badge';
import { LoadingState } from '../../components/LoadingState/LoadingState';
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
import '../Customer/CustomerDashboard.css';

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
    showToast({
      type: 'success',
      title: 'Checklist Saved',
      message: 'Survey checklist progress saved to offline cache.',
    });
  };

  return (
    <AppShell requiredRole="technician">
      {loading ? (
        <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <LoadingState label="Loading field survey workbench…" />
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          {/* Master Bento Dashboard for Technician */}
          <DashboardView
            role="technician"
            jobs={jobs}
            onNewAction={() => showToast({ type: 'info', title: 'Inspection Mode', message: 'Field inspection mode active.' })}
          />

          {/* Interactive Site Inspection Checklist Cards */}
          <div className="bento-card" style={{ padding: '28px' }}>
            <div className="bento-card-header" style={{ marginBottom: '20px' }}>
              <div>
                <h3 className="bento-card-title">Assigned Rooftop Field Surveys</h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '12.5px', color: '#64748b' }}>
                  Conduct on-site shadow raytracing, verify structural roof integrity, and check off items.
                </p>
              </div>
              <button type="button" className="export-data-btn" onClick={fetchJobs}>
                <Clock size={13} />
                <span>Refresh Jobs</span>
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {jobs.map((job) => {
                const completedCount = job.checklist.filter((c) => c.done).length;
                const totalCount = job.checklist.length;
                const isAllDone = completedCount === totalCount;

                return (
                  <div key={job.id} className="floating-event-card" style={{ padding: '24px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{ fontSize: '16px', fontWeight: '700', color: '#111827' }}>
                            {job.reference} · {job.customer_name}
                          </span>
                          <Badge variant={isAllDone ? 'success' : 'warning'}>
                            {job.status.replace(/_/g, ' ')}
                          </Badge>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#64748b', marginTop: '4px' }}>
                          <MapPin size={14} color="#6366f1" />
                          <span>{job.address}</span>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span style={{ fontSize: '13px', fontWeight: '600', color: completedCount === totalCount ? '#10b981' : '#4f46e5' }}>
                          {completedCount}/{totalCount} Completed
                        </span>
                        <button
                          type="button"
                          className="export-data-btn"
                          onClick={() => showToast({ type: 'info', title: 'Camera Mode', message: 'Rooftop photo camera modal opened.' })}
                        >
                          <Camera size={14} />
                          <span>Upload Photos</span>
                        </button>
                      </div>
                    </div>

                    {/* Interactive Checklist Items */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '10px', marginTop: '12px' }}>
                      {job.checklist.map((item) => (
                        <div
                          key={item.id}
                          className="notification-item-compact"
                          style={{
                            cursor: 'pointer',
                            backgroundColor: item.done ? '#ecfdf5' : '#f8fafc',
                            borderColor: item.done ? '#a7f3d0' : '#f1f5f9',
                          }}
                          onClick={() => handleToggleCheck(job.id, item.id)}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <div
                              style={{
                                width: '20px',
                                height: '20px',
                                borderRadius: '6px',
                                border: item.done ? 'none' : '2px solid #cbd5e1',
                                backgroundColor: item.done ? '#10b981' : '#ffffff',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: '#ffffff',
                              }}
                            >
                              {item.done && <Check size={14} strokeWidth={3} />}
                            </div>
                            <span style={{ fontSize: '12.5px', fontWeight: item.done ? '600' : '500', color: item.done ? '#065f46' : '#374151' }}>
                              {item.label}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>

                    {isAllDone && (
                      <div style={{ marginTop: '18px', display: 'flex', justifyContent: 'flex-end' }}>
                        <button
                          type="button"
                          className="primary-board-btn"
                          onClick={() => showToast({ type: 'success', title: 'Survey Submitted', message: `Survey ${job.reference} submitted to sales review queue.` })}
                        >
                          <CheckCircle2 size={16} />
                          <span>Submit Signed Survey to Sales</span>
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}

export default TechnicianDashboard;
