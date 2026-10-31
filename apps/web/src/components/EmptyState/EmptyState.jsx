import React from 'react';
import { SunMedium } from 'lucide-react';
import './EmptyState.css';

export function EmptyState({
  title = 'No items found',
  body = 'There is currently no data in this view.',
  icon = <SunMedium size={28} />,
  action = null,
}) {
  return (
    <div className="empty-state-card">
      <div className="empty-state-icon-box">{icon}</div>
      <h3 className="empty-state-title">{title}</h3>
      <p className="empty-state-body">{body}</p>
      {action && <div className="empty-state-action">{action}</div>}
    </div>
  );
}

