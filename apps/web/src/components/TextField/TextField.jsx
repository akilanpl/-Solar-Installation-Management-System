import React from 'react';
import './TextField.css';

export function TextField({
  label,
  id,
  name,
  type = 'text',
  value,
  onChange,
  placeholder,
  required = false,
  error = null,
  hint = null,
  as = 'input', // 'input' | 'textarea'
  rows = 3,
  className = '',
  ...props
}) {
  const fieldId = id || name;

  return (
    <div className={`field-group ${className}`}>
      {label && (
        <label htmlFor={fieldId} className="field-label">
          <span>
            {label}
            {required && <span className="field-required">*</span>}
          </span>
        </label>
      )}
      <div className="field-input-wrapper">
        {as === 'textarea' ? (
          <textarea
            id={fieldId}
            name={name}
            value={value}
            onChange={onChange}
            placeholder={placeholder}
            required={required}
            rows={rows}
            className={`field-input field-textarea ${error ? 'has-error' : ''}`}
            {...props}
          />
        ) : (
          <input
            id={fieldId}
            name={name}
            type={type}
            value={value}
            onChange={onChange}
            placeholder={placeholder}
            required={required}
            className={`field-input ${error ? 'has-error' : ''}`}
            {...props}
          />
        )}
      </div>
      {hint && !error && <span className="field-hint">{hint}</span>}
      {error && <span className="field-error">{error}</span>}
    </div>
  );
}

