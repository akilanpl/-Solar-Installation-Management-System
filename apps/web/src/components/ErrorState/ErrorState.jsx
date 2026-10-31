import React from 'react';
import { AlertCircle } from 'lucide-react';
import { Button } from '../Button/Button';
import './ErrorState.css';

export function ErrorState({
  title = 'An error occurred',
  message,
  onRetry = null,
}) {
  return (
    <div className="error-state-card">
      <div className="error-icon-box">
        <AlertCircle size={22} />
      </div>
      <div className="error-content">
        <h4 className="error-title">{title}</h4>
        <p className="error-message">{message || 'Unable to complete request.'}</p>
        {onRetry && (
          <div className="error-actions">
            <Button variant="outline" size="sm" onClick={onRetry}>
              Try Again
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

