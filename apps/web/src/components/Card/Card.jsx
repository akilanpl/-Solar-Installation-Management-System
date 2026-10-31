import React from 'react';
import './Card.css';

export function Card({
  children,
  className = '',
  accent = 'none', // 'none' | 'violet' | 'lime'
  elevated = false,
  interactive = false,
  onClick,
  ...props
}) {
  const classNames = [
    'card',
    elevated ? 'card-elevated' : '',
    interactive ? 'card-interactive' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={classNames} onClick={onClick} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, action, className = '' }) {
  return (
    <div className={`card-header ${className}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
      <div>
        {title && <h3 className="card-title">{title}</h3>}
        {subtitle && <p className="card-subtitle">{subtitle}</p>}
      </div>
      {action && <div className="card-action">{action}</div>}
    </div>
  );
}

