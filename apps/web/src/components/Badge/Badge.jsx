import React from 'react';
import { STATUS_META } from '../../lib/format';
import './Badge.css';

export function Badge({
  children,
  variant = 'neutral',
  dot = true,
  className = '',
  status = null,
}) {
  let resolvedVariant = variant;
  let resolvedLabel = children;

  if (status && STATUS_META[status]) {
    resolvedVariant = STATUS_META[status].variant;
    resolvedLabel = children || STATUS_META[status].label;
  }

  return (
    <span className={`badge badge-${resolvedVariant} ${className}`}>
      {dot && <span className="badge-dot" />}
      {resolvedLabel}
    </span>
  );
}

