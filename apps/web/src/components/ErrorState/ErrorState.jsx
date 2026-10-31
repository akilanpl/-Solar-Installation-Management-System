import React from 'react';
import { Alert } from '../Alert/Alert';
import { Button } from '../Button/Button';
import './ErrorState.css';

export function ErrorState({
  title = 'An error occurred',
  message,
  onRetry = null,
}) {
  return (
    <div className="error-state-container">
      <Alert
        type="error"
        title={title}
        message={message || 'Unable to complete request.'}
      >
        {onRetry && (
          <div className="error-retry-action">
            <Button variant="outline" size="sm" onClick={onRetry}>
              Try Again
            </Button>
          </div>
        )}
      </Alert>
    </div>
  );
}
