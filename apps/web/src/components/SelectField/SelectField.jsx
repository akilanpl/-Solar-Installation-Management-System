import React from 'react';
import { ChevronDown } from 'lucide-react';
import './SelectField.css';
import '../TextField/TextField.css';

export function SelectField({
  label,
  id,
  name,
  value,
  onChange,
  children,
  required = false,
  error = null,
  hint = null,
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
      <div className="select-wrapper">
        <select
          id={fieldId}
          name={name}
          value={value}
          onChange={onChange}
          required={required}
          className={`select-input ${error ? 'has-error' : ''}`}
          {...props}
        >
          {children}
        </select>
        <span className="select-icon">
          <ChevronDown size={16} />
        </span>
      </div>
      {hint && !error && <span className="field-hint">{hint}</span>}
      {error && <span className="field-error">{error}</span>}
    </div>
  );
}

