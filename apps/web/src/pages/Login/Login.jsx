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

  const currentPortalConfig = PORTALS.find((p) => p.value === portal) || PORTALS[0];

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
    <div className="login-page-bg">
      <div className="login-split-card">
        {/* ==================================================================
            LEFT PANEL: HERO GRADIENT WITH STEP CARDS (EXACT REFERENCE LAYOUT)
            ================================================================== */}
        <div className="login-hero-panel">
          {/* Top Logo */}
          <div className="hero-logo-box">
            <div className="hero-logo-icon">
              <Zap size={18} fill="#C6FF34" />
            </div>
            <span className="hero-brand-name">SolarOps</span>
          </div>

          {/* Central Hero Messaging */}
          <div className="hero-content-box">
            <div className="hero-badge-pill">
              <span>Join Us to Build</span>
              <span>☀️</span>
            </div>

            <h1 className="hero-title">Start your Journey</h1>

            <p className="hero-subhead">
              Follow these simple steps to set up your rooftop solar account, monitor
              surveys, and track turnkey installation progress.
            </p>
          </div>

          {/* 3 Process Step Cards (Matching the reference layout) */}
          <div className="hero-steps-row">
            {/* Step 1: Active Clean White Card */}
            <div className="hero-step-card active">
              <div className="hero-step-num">1</div>
              <div className="hero-step-text">Register or instant bypass login</div>
            </div>

            {/* Step 2: Translucent Glass Card */}
            <div className="hero-step-card translucent">
              <div className="hero-step-num">2</div>
              <div className="hero-step-text">Technical rooftop survey inspection</div>
            </div>

            {/* Step 3: Translucent Glass Card */}
            <div className="hero-step-card translucent">
              <div className="hero-step-num">3</div>
              <div className="hero-step-text">DISCOM net-metering & power on</div>
            </div>
          </div>
        </div>

        {/* ==================================================================
            RIGHT PANEL: HIGH CONTRAST FORM (EXACT REFERENCE LAYOUT)
            ================================================================== */}
        <div className="login-form-panel">
          <h2 className="form-header-title">Sign In</h2>

          {/* ⚡ 1-Click Instant Demo Bypass Callout */}
          <div className="form-bypass-box">
            <div className="form-bypass-header">
              <span className="form-bypass-title">
                <Zap size={14} />
                <span>⚡ Instant Demo Bypass</span>
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
            {/* Phone Number / Contact (Like Reference Field 1) */}
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

            {/* 2-Column Row: Portal Role + Identifier (Like Full Name & Username in Reference) */}
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

            {/* Password Field with Eye Toggle (Like Reference) */}
            <div className="clean-form-group">
              <label className="clean-form-label">Password</label>
              <div className="clean-input-box">
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="clean-input-field"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••••••"
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

            {/* Continue Primary Button */}
            <button
              type="submit"
              className="clean-primary-btn"
              disabled={loading}
            >
              {loading ? (
                'Connecting to SolarOps…'
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

          {/* Secondary Action matching reference Google button */}
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
      </div>

      {/* Interactive Modal for full persona switcher */}
      <FakeLoginModal
        isOpen={fakeModalOpen}
        onClose={() => setFakeModalOpen(false)}
      />
    </div>
  );
}
