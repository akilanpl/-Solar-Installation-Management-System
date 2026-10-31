import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useRouter, Link } from '../../router/Router';
import { destinationAfterLogin } from '../../lib/access';
import { FakeLoginModal } from '../../components/FakeLoginModal/FakeLoginModal';
import { ErrorState } from '../../components/ErrorState/ErrorState';
import {
  Zap,
  Eye,
  EyeOff,
  Sun,
  ShieldCheck,
  Check,
  ArrowRight,
  Sparkles,
  Lock,
} from 'lucide-react';
import './Login.css';

const PORTALS = [
  { value: 'customer', label: 'Customer Portal', defaultId: 'customer@solarops.dev', flag: '🏠' },
  { value: 'sales', label: 'Sales Feasibility', defaultId: 'EMP-SALES-001', flag: '📈' },
  { value: 'technician', label: 'Field Technician', defaultId: 'EMP-TECH-001', flag: '🔧' },
  { value: 'warehouse', label: 'Warehouse & Stock', defaultId: 'EMP-WH-001', flag: '📦' },
  { value: 'support', label: 'Customer Support', defaultId: 'EMP-SUP-001', flag: '🎧' },
  { value: 'admin', label: 'System Admin', defaultId: 'EMP-ADM-001', flag: '🛡️' },
];

export function Login() {
  const { login, bypassLogin } = useAuth();
  const { navigate, query } = useRouter();

  const [portal, setPortal] = useState('customer');
  const [identifier, setIdentifier] = useState('customer@solarops.dev');
  const [phone, setPhone] = useState('+91 98765 43210');
  const [password, setPassword] = useState('solarops2026');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fakeModalOpen, setFakeModalOpen] = useState(false);

  const handlePortalChange = (newPortal) => {
    setPortal(newPortal);
    const cfg = PORTALS.find((p) => p.value === newPortal);
    if (cfg) setIdentifier(cfg.defaultId);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const user = await login(
        identifier,
        password,
        portal === 'customer' ? 'customer' : 'employee'
      );
      const next = destinationAfterLogin(user.role, query.next);
      navigate(next);
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  // Instant 1-Click Demo Bypass handler
  const handleQuickBypass = (roleKey) => {
    const user = bypassLogin(roleKey);
    const next = destinationAfterLogin(user.role, query.next);
    navigate(next);
  };

  return (
    <div className="login-fullscreen-canvas">
      <div className="login-grid-overlay" />

      {/* Top Navigation Bar on the Full Screen Hero */}
      <header className="login-top-bar">
        <Link href="/" className="login-top-brand">
          <div className="login-top-brand-icon">
            <Zap size={20} fill="#000000" />
          </div>
          <div>
            <span className="login-top-brand-text">SolarOps</span>
            <span className="login-top-brand-sub">SunPower Solutions</span>
          </div>
        </Link>

        <div className="login-top-status-badge">
          <span className="login-top-status-dot" />
          <span>Grid Operations Active</span>
        </div>
      </header>

      {/* Center Sign-In Component (Hero Centerpiece) */}
      <main className="login-center-container">
        <div className="login-hero-card">
          {/* Card Header & Badge */}
          <div className="login-card-header">
            <div className="login-badge-pill">
              <span>Join Us to Build ☀️</span>
            </div>
            <h1 className="login-card-title">Start your Journey</h1>
            <p className="login-card-subtitle">
              Sign in with your enterprise credentials or use instant 1-click bypass.
            </p>
          </div>

          {/* 3 Process Step Indicator Pills */}
          <div className="login-journey-steps-row">
            <div className="journey-step-pill active">
              <span className="journey-step-circle">1</span>
              <span>Instant Bypass / Auth</span>
            </div>
            <div className="journey-step-pill inactive">
              <span className="journey-step-circle">2</span>
              <span>Site Survey</span>
            </div>
            <div className="journey-step-pill inactive">
              <span className="journey-step-circle">3</span>
              <span>Net-Metering</span>
            </div>
          </div>

          {/* ⚡ 1-Click Instant Demo Bypass Callout */}
          <div className="form-bypass-box">
            <div className="form-bypass-header">
              <span className="form-bypass-title">
                <Zap size={14} />
                <span>⚡ 1-Click Demo Bypass</span>
              </span>
              <span className="form-bypass-tag">Skip Login</span>
            </div>
            <div className="form-bypass-grid">
              <button
                type="button"
                className="form-bypass-btn"
                onClick={() => handleQuickBypass('customer')}
                title="Bypass as Customer"
              >
                🏠 Customer
              </button>
              <button
                type="button"
                className="form-bypass-btn"
                onClick={() => handleQuickBypass('sales')}
                title="Bypass as Sales Officer"
              >
                📈 Sales
              </button>
              <button
                type="button"
                className="form-bypass-btn"
                onClick={() => handleQuickBypass('technician')}
                title="Bypass as Field Technician"
              >
                🔧 Technician
              </button>
              <button
                type="button"
                className="form-bypass-btn"
                onClick={() => handleQuickBypass('warehouse')}
                title="Bypass as Warehouse Manager"
              >
                📦 Warehouse
              </button>
              <button
                type="button"
                className="form-bypass-btn"
                onClick={() => handleQuickBypass('support')}
                title="Bypass as Support Specialist"
              >
                🎧 Support
              </button>
              <button
                type="button"
                className="form-bypass-btn"
                onClick={() => handleQuickBypass('admin')}
                title="Bypass as Administrator"
              >
                🛡️ Admin
              </button>
            </div>
          </div>

          {error && <ErrorState message={error} />}

          <form onSubmit={handleSubmit}>
            {/* Phone Number Input */}
            <div className="clean-form-group">
              <label className="clean-form-label">Phone number</label>
              <div className="clean-input-box">
                <div className="clean-input-prefix">
                  <span>🇮🇳</span>
                  <span>+91</span>
                </div>
                <input
                  type="tel"
                  className="clean-input-field"
                  placeholder="98765 43210"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </div>
            </div>

            {/* 2-Column Row: Portal Role + Identifier */}
            <div className="clean-form-row">
              <div className="clean-form-group">
                <label className="clean-form-label">Signing in as</label>
                <div className="clean-input-box">
                  <select
                    className="clean-input-field"
                    style={{ cursor: 'pointer' }}
                    value={portal}
                    onChange={(e) => handlePortalChange(e.target.value)}
                  >
                    {PORTALS.map((p) => (
                      <option key={p.value} value={p.value}>
                        {p.flag} {p.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="clean-form-group">
                <label className="clean-form-label">
                  {portal === 'customer' ? 'Account Email' : 'Employee ID'}
                </label>
                <div className="clean-input-box">
                  <input
                    type="text"
                    className="clean-input-field"
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    required
                  />
                  <Check size={16} color="var(--color-violet)" />
                </div>
              </div>
            </div>

            {/* Password Field with Eye Toggle */}
            <div className="clean-form-group">
              <label className="clean-form-label">Password</label>
              <div className="clean-input-box">
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="clean-input-field"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••••••"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className="clean-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label="Toggle password view"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              <span className="clean-input-helper">
                At least 8 characters. Uppercase, lowercase letters, numbers, and symbols.
              </span>
            </div>

            {/* Primary Continue Button */}
            <button
              type="submit"
              className="clean-primary-btn"
              disabled={loading}
            >
              {loading ? (
                'Authenticating…'
              ) : (
                <>
                  <span>Continue</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          {/* Links */}
          <div className="clean-switch-link">
            <span>New customer looking for solar? </span>
            <Link href="/signup">Create account</Link>
          </div>

          <div className="clean-divider">
            <span>Or</span>
          </div>

          {/* Secondary Action */}
          <button
            type="button"
            className="clean-secondary-btn"
            onClick={() => setFakeModalOpen(true)}
          >
            <Sparkles size={16} color="var(--color-violet)" />
            <span>Open Interactive Persona Selector</span>
          </button>

          {/* Bottom Disclaimer */}
          <p className="clean-disclaimer">
            By signing in I confirm that I carefully have read and agree to the SolarOps{' '}
            <a href="#privacy">Privacy Policy</a> and <a href="#terms">Terms of Service</a>.
          </p>
        </div>
      </main>

      {/* Bottom Hero Footer */}
      <footer className="login-bottom-bar">
        <span>SunPower Solutions Operations © 2026. Enterprise Rooftop Solar Platform.</span>
        <div className="login-bottom-links">
          <a href="#privacy">Privacy</a>
          <a href="#terms">Security Policy</a>
          <a href="#support">Operations Desk</a>
        </div>
      </footer>

      {/* Interactive Modal for full persona switcher */}
      <FakeLoginModal
        isOpen={fakeModalOpen}
        onClose={() => setFakeModalOpen(false)}
      />
    </div>
  );
}
