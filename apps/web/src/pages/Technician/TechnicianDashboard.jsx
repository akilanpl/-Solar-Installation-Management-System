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
  RefreshCw,
  ExternalLink,
  ClipboardCheck,
  Sparkles,
} from 'lucide-react';
import './TechnicianDashboard.css';
import '../Customer/CustomerDashboard.css';

export function TechnicianDashboard() {
  const { user, showToast } = useAuth();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('all'); // 'all' | 'assigned' | 'pending' | 'scheduled'

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

  const totalChecks = jobs.reduce((acc, j) => acc + (j.checklist?.length || 0), 0);
  const completedChecks = jobs.reduce(
    (acc, j) => acc + (j.checklist?.filter((c) => c.done).length || 0),
    0
  );
  const overallPercent = totalChecks > 0 ? Math.round((completedChecks / totalChecks) * 100) : 0;

  const filteredJobs = jobs.filter((job) => {
    if (filterStatus === 'all') return true;
    return job.status?.toLowerCase() === filterStatus;
  });

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
            onNewAction={() =>
              showToast({
                type: 'info',
                title: 'Inspection Mode',
                message: 'Field inspection mode active.',
              })
            }
          />

          {/* Interactive Site Inspection Checklist Cards */}
          <div className="survey-workbench-card">
            {/* Header with Title, Stats & Filter Controls */}
            <div className="survey-workbench-header">
              <div className="survey-header-main">
                <div className="survey-icon-pill">
                  <ClipboardCheck size={22} color="#4f46e5" strokeWidth={2.2} />
                </div>
                <div>
                  <div className="survey-title-row">
                    <h3 className="survey-workbench-title">Assigned Rooftop Field Surveys</h3>
                    <span className="survey-count-pill">{jobs.length} Active Jobs</span>
                  </div>
                  <p className="survey-workbench-subtitle">
                    Conduct on-site shadow raytracing, verify structural roof integrity, and check off items.
                  </p>
                </div>
              </div>

              <div className="survey-header-actions">
                {/* Overall Progress Meter */}
                <div className="survey-overall-meter">
                  <div className="meter-info">
                    <span className="meter-label">Verification Progress</span>
                    <span className="meter-value">{completedChecks}/{totalChecks} ({overallPercent}%)</span>
                  </div>
                  <div className="meter-track">
                    <div className="meter-fill" style={{ width: `${overallPercent}%` }} />
                  </div>
                </div>

                <button
                  type="button"
                  className="survey-refresh-btn"
                  onClick={fetchJobs}
                  title="Refresh Assigned Jobs"
                >
                  <RefreshCw size={14} className={loading ? 'spinning-refresh' : ''} />
                  <span>Refresh Jobs</span>
                </button>
              </div>
            </div>

            {/* Filter Tabs Bar */}
            <div className="survey-filter-tabs-row">
              <div className="survey-filter-tabs">
                <button
                  type="button"
                  className={`survey-tab ${filterStatus === 'all' ? 'active' : ''}`}
                  onClick={() => setFilterStatus('all')}
                >
                  All Surveys ({jobs.length})
                </button>
                <button
                  type="button"
                  className={`survey-tab ${filterStatus === 'assigned' ? 'active' : ''}`}
                  onClick={() => setFilterStatus('assigned')}
                >
                  Assigned ({jobs.filter((j) => j.status?.toLowerCase() === 'assigned').length})
                </button>
                <button
                  type="button"
                  className={`survey-tab ${filterStatus === 'pending' ? 'active' : ''}`}
                  onClick={() => setFilterStatus('pending')}
                >
                  Pending ({jobs.filter((j) => j.status?.toLowerCase() === 'pending').length})
                </button>
                <button
                  type="button"
                  className={`survey-tab ${filterStatus === 'scheduled' ? 'active' : ''}`}
                  onClick={() => setFilterStatus('scheduled')}
                >
                  Scheduled ({jobs.filter((j) => j.status?.toLowerCase() === 'scheduled').length})
                </button>
              </div>
            </div>

            {/* Job Cards Container */}
            <div className="survey-jobs-container">
              {filteredJobs.map((job) => {
                const completedCount = job.checklist?.filter((c) => c.done).length || 0;
                const totalCount = job.checklist?.length || 0;
                const isAllDone = totalCount > 0 && completedCount === totalCount;
                const jobPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;
                const customerName = job.client_name || job.customer_name || 'Commercial Client';
                const address = job.location || job.address || 'Bengaluru Site';

                return (
                  <div
                    key={job.id}
                    className={`survey-job-card ${isAllDone ? 'job-complete' : ''} status-${job.status?.toLowerCase()}`}
                  >
                    {/* Card Top Meta Strip */}
                    <div className="job-card-top-bar">
                      <div className="job-meta-left">
                        <span className="job-ref-badge">{job.reference}</span>
                        {job.enquiry_reference && (
                          <span className="job-enquiry-badge">{job.enquiry_reference}</span>
                        )}
                        {job.type && (
                          <span className="job-type-pill">{job.type}</span>
                        )}
                        <span className={`job-status-pill pill-${job.status?.toLowerCase()}`}>
                          <span className="status-dot" />
                          {job.status?.replace(/_/g, ' ').toUpperCase()}
                        </span>
                      </div>

                      <div className="job-meta-right">
                        {/* Individual Progress Pill */}
                        <div className="job-progress-widget">
                          <div className="progress-text-row">
                            <span className="progress-fraction">{completedCount}/{totalCount} Completed</span>
                            <span className="progress-percentage">{jobPercent}%</span>
                          </div>
                          <div className="job-progress-bar">
                            <div
                              className={`job-progress-fill ${isAllDone ? 'fill-done' : ''}`}
                              style={{ width: `${jobPercent}%` }}
                            />
                          </div>
                        </div>

                        {/* Upload Photos Trigger */}
                        <button
                          type="button"
                          className="job-camera-btn"
                          onClick={() =>
                            showToast({
                              type: 'info',
                              title: 'Camera Mode',
                              message: `Rooftop photo camera modal opened for ${job.reference}.`,
                            })
                          }
                        >
                          <Camera size={14} />
                          <span>Upload Photos</span>
                        </button>
                      </div>
                    </div>

                    {/* Customer & Location Row */}
                    <div className="job-client-row">
                      <h4 className="job-customer-name">{customerName}</h4>
                      <div className="job-details-chips">
                        <div className="job-detail-chip">
                          <MapPin size={13.5} className="detail-icon loc" />
                          <span>{address}</span>
                          <a
                            href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="open-map-link"
                            title="Open Site in Google Maps"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <ExternalLink size={12} />
                          </a>
                        </div>
                        {job.date && (
                          <div className="job-detail-chip">
                            <Calendar size={13.5} className="detail-icon cal" />
                            <span>{job.date}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Interactive Checklist Section */}
                    <div className="job-checklist-section">
                      <div className="checklist-section-header">
                        <span className="checklist-section-title">Field Inspection & Engineering Checklist</span>
                        <span className="checklist-hint">Click any tile to toggle verification status</span>
                      </div>

                      <div className="survey-checklist-grid">
                        {job.checklist?.map((item, idx) => (
                          <div
                            key={item.id}
                            className={`survey-check-tile ${item.done ? 'tile-checked' : 'tile-pending'}`}
                            onClick={() => handleToggleCheck(job.id, item.id)}
                            role="checkbox"
                            aria-checked={item.done}
                            tabIndex={0}
                            onKeyDown={(e) => {
                              if (e.key === ' ' || e.key === 'Enter') {
                                e.preventDefault();
                                handleToggleCheck(job.id, item.id);
                              }
                            }}
                          >
                            <div className="check-tile-left">
                              <div className={`check-custom-box ${item.done ? 'box-checked' : ''}`}>
                                {item.done ? (
                                  <Check size={13} strokeWidth={3.2} />
                                ) : (
                                  <span className="check-index-num">{idx + 1}</span>
                                )}
                              </div>
                            </div>
                            <div className="check-tile-content">
                              <span className="check-item-text">{item.label}</span>
                              <span className="check-status-tag">
                                {item.done ? 'Verified' : 'Pending Check'}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Card Footer Bar */}
                    <div className="survey-card-footer">
                      <div className="footer-status-msg">
                        {isAllDone ? (
                          <div className="footer-badge success">
                            <CheckCircle2 size={15} color="#059669" />
                            <span>All {totalCount} engineering checks verified. Ready for sales handoff.</span>
                          </div>
                        ) : (
                          <div className="footer-badge pending">
                            <Clock size={15} color="#d97706" />
                            <span>{totalCount - completedCount} checks remaining before digital sign-off.</span>
                          </div>
                        )}
                      </div>

                      <div className="footer-actions-group">
                        {!isAllDone && (
                          <button
                            type="button"
                            className="quick-verify-btn"
                            onClick={async () => {
                              for (const item of job.checklist) {
                                if (!item.done) {
                                  await api.toggleJobChecklistItem(job.id, item.id);
                                }
                              }
                              const fresh = await api.getTechnicianJobs();
                              setJobs([...fresh]);
                              showToast({
                                type: 'success',
                                title: 'All Checks Verified',
                                message: `Marked all items complete for ${job.reference}.`,
                              });
                            }}
                          >
                            <Sparkles size={13} />
                            <span>Verify All</span>
                          </button>
                        )}

                        {isAllDone && (
                          <button
                            type="button"
                            className="submit-survey-btn"
                            onClick={() =>
                              showToast({
                                type: 'success',
                                title: 'Survey Submitted to Sales',
                                message: `Survey ${job.reference} signed & transmitted to sales review queue.`,
                              })
                            }
                          >
                            <CheckCircle2 size={16} />
                            <span>Submit Signed Survey to Sales</span>
                          </button>
                        )}
                      </div>
                    </div>
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
