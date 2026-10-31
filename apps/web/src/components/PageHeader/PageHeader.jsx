import React from 'react';
import './PageHeader.css';

export function PageHeader({ title, description, action = null, icon = null }) {
  return (
    <div className="page-header">
      <div className="page-header-content">
        <h1 className="page-header-title">
          {icon && <span style={{ display: 'inline-flex' }}>{icon}</span>}
          <span>{title}</span>
        </h1>
        {description && <p className="page-header-description">{description}</p>}
      </div>
      {action && <div className="page-header-action">{action}</div>}
    </div>
  );
}

