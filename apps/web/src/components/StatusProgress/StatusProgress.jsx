import React from 'react';
import { Check } from 'lucide-react';
import './StatusProgress.css';

const STAGES = [
  { key: 'submitted', label: 'Submitted' },
  { key: 'under_review', label: 'Technical Screening' },
  { key: 'qualified', label: 'Qualified' },
  { key: 'survey_scheduled', label: 'Site Survey' },
  { key: 'completed', label: 'Approved & Active' },
];

export function StatusProgress({ currentStatus }) {
  let currentIndex = 0;
  if (currentStatus === 'submitted') currentIndex = 0;
  else if (currentStatus === 'under_review' || currentStatus === 'clarification_requested') currentIndex = 1;
  else if (currentStatus === 'qualified') currentIndex = 2;
  else if (currentStatus === 'survey_scheduled') currentIndex = 3;
  else if (currentStatus === 'completed') currentIndex = 4;
  else if (currentStatus === 'disqualified') currentIndex = 1;

  const progressPercent = (currentIndex / (STAGES.length - 1)) * 100;

  return (
    <div className="status-progress-track">
      <div className="status-progress-line" />
      <div
        className="status-progress-fill"
        style={{ width: `calc(${progressPercent}% * 0.85)` }}
      />
      {STAGES.map((stage, idx) => {
        const isCompleted = idx < currentIndex;
        const isCurrent = idx === currentIndex;
        return (
          <div
            key={stage.key}
            className={`status-progress-step ${
              isCompleted
                ? 'status-step-completed'
                : isCurrent
                ? 'status-step-current'
                : ''
            }`}
          >
            <div className="status-step-node">
              {isCompleted ? <Check size={16} strokeWidth={3} /> : idx + 1}
            </div>
            <span className="status-step-label">{stage.label}</span>
          </div>
        );
      })}
    </div>
  );
}

