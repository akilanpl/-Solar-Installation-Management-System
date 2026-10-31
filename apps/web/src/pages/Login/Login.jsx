import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useRouter, Link } from '../../router/Router';
import { destinationAfterLogin } from '../../lib/access';
import { FakeLoginModal } from '../../components/FakeLoginModal/FakeLoginModal';
import { ErrorState } from '../../components/ErrorState/ErrorState';
import {
  Eye,
  EyeOff,
  Check,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import './Login.css';

const PORTALS = [
  { value: 'customer', label: 'Customer', defaultId: 'customer@solarops.dev', flag: '🏠', name: 'Juliette Karapetyan' },
  { value: 'sales', label: 'Sales Exec', defaultId: 'EMP-SALES-001', flag: '📈', name: 'Aarav Patel' },
  { value: 'technician', label: 'Technician', defaultId: 'EMP-TECH-001', flag: '🔧', name: 'Vikram Singh' },
  { value: 'warehouse', label: 'Warehouse', defaultId: 'EMP-WH-001', flag: '📦', name: 'Kavita Nair' },
  { value: 'support', label: 'Support', defaultId: 'EMP-SUP-001', flag: '🎧', name: 'Ananya Iyer' },
  { value: 'admin', label: 'Admin', defaultId: 'EMP-ADM-001', flag: '🛡️', name: 'Dev Lead' },
];

export function Login({ initialMode = 'login' }) {
  const { login, signup, bypassLogin } = useAuth();
  const { navigate, query } = useRouter();

  const [mode, setMode] = useState(initialMode); // 'login' | 'signup'
  const [portal, setPortal] = useState('customer');
  const [fullName, setFullName] = useState('Juliette Karapetyan');
  const [identifier, setIdentifier] = useState('julietux');
  const [phone, setPhone] = useState('0000 00 00');
  const [password, setPassword] = useState('solarops2026');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fakeModalOpen, setFakeModalOpen] = useState(false);

  const handlePortalChange = (newPortal) => {
    setPortal(newPortal);
    const cfg = PORTALS.find((p) => p.value === newPortal);
    if (cfg) {
      setIdentifier(cfg.defaultId);
      setFullName(cfg.name);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (mode === 'signup') {
        await signup({
          full_name: fullName,
          email: identifier.includes('@') ? identifier : `${identifier}@solarops.dev`,
          phone: `+91 ${phone}`,
          password,
          address: 'Solar Rooftop Installation Site, Bengaluru',
        });
        navigate(`/verify-email?email=${encodeURIComponent(identifier)}`);
      } else {
        const user = await login(
          identifier.includes('@') ? identifier : `${identifier}@solarops.dev`,
          password,
          portal === 'customer' ? 'customer' : 'employee'
        );
        const next = destinationAfterLogin(user.role, query.next);
        navigate(next);
      }
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
    <div className="auth-page-viewport">
      {/* ================================================================
          LEFT HERO PANEL (Vibrant Royal Blue Gradient with 3 Step Cards)
          ================================================================ */}
      <section className="auth-hero-panel" aria-label="Hero Introduction">
        {/* Dynamic Background Video (100% Opacity, Zero Blue Tint) */}
        <video
          className="auth-hero-video-bg"
          autoPlay
          loop
          muted
          playsInline
        >
          <source src="/solar_loop.mp4" type="video/mp4" />
          <source src="/login-bg.mp4" type="video/mp4" />
        </video>
        <div className="auth-hero-video-overlay" />

        {/* Brand Logo & Title (Top Left) */}
        <Link href="/" className="auth-hero-brand">
          <div className="auth-hero-brand-icon">
            {/* Modern Connected Node Glyph matching reference image */}
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="5" r="2.5" />
              <circle cx="6" cy="17" r="2.5" />
              <circle cx="18" cy="17" r="2.5" />
              <line x1="12" y1="7.5" x2="6" y2="14.5" />
              <line x1="12" y1="7.5" x2="18" y2="14.5" />
              <line x1="8.5" y1="17" x2="15.5" y2="17" />
            </svg>
          </div>
          <span className="auth-hero-brand-name">SolarOps</span>
        </Link>

        {/* Lower Content: Pill, Title, Subtitle, 3 Step Cards */}
        <div className="auth-hero-content">
          <div className="auth-hero-badge">
            <span>Join Us</span>
          </div>

          <h1 className="auth-hero-title">Start your Journey</h1>
          <p className="auth-hero-subtitle">
            Follow these simple steps to set up your account.
          </p>

          {/* 3 Step Process Cards Row matching reference */}
          <div className="auth-hero-steps-grid">
            {/* Step 1: Active Solid White Card */}
            <div className="auth-step-card active">
              <div className="auth-step-badge">1</div>
              <div className="auth-step-label">Register your account</div>
            </div>

            {/* Step 2: Translucent Glass Card */}
            <div className="auth-step-card inactive">
              <div className="auth-step-badge">2</div>
              <div className="auth-step-label">Set up your profile information</div>
            </div>

            {/* Step 3: Translucent Glass Card */}
            <div className="auth-step-card inactive">
              <div className="auth-step-badge">3</div>
              <div className="auth-step-label">Verify your identity through passport/ID</div>
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================
            RIGHT FORM PANEL (Clean White Form Architecture)
            ================================================================ */}
      <section className="auth-form-panel" aria-label="Sign In or Registration Form">
        <div className="auth-form-inner">
          <h2 className="auth-form-heading">
            {mode === 'signup' ? 'Join Us' : 'Join Us'}
          </h2>

          {error && <ErrorState message={error} />}

          <form onSubmit={handleSubmit}>
            {/* Field 1: Phone Number with Country Flag & Code */}
            <div className="auth-field-group">
              <label className="auth-field-label">Phone number</label>
              <div className="auth-phone-box">
                <div className="auth-phone-prefix">
                  <span role="img" aria-label="Flag">🇦🇲</span>
                  <span>+374</span>
                </div>
                <div className="auth-phone-divider" />
                <input
                  type="tel"
                  className="auth-phone-input"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="0000 00 00"
                  required
                />
              </div>
            </div>

            {/* Field 2 & 3: Two-Column Row (Full Name + Username) */}
            <div className="auth-field-row">
              <div className="auth-field-group">
                <label className="auth-field-label">
                  {mode === 'signup' ? 'Full Name' : 'Full Name / Role'}
                </label>
                <div className="auth-input-box">
                  {mode === 'signup' ? (
                    <input
                      type="text"
                      className="auth-input-control"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Juliette Karapetyan"
                      required
                    />
                  ) : (
                    <select
                      className="auth-input-control"
                      style={{ cursor: 'pointer', background: 'transparent' }}
                      value={portal}
                      onChange={(e) => handlePortalChange(e.target.value)}
                    >
                      {PORTALS.map((p) => (
                        <option key={p.value} value={p.value}>
                          {p.flag} {p.label}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              </div>

              <div className="auth-field-group">
                <label className="auth-field-label">Username</label>
                <div className="auth-input-box">
                  <input
                    type="text"
                    className="auth-input-control"
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    placeholder="julietux"
                    required
                  />
                  <Check size={16} className="auth-check-icon" strokeWidth={2.8} />
                </div>
              </div>
            </div>

            {/* Field 4: Password with Eye Toggle & Requirements Note */}
            <div className="auth-field-group">
              <label className="auth-field-label">Password</label>
              <div className="auth-input-box">
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="auth-input-control"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••••••"
                  autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                  required
                />
                <button
                  type="button"
                  className="auth-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label="Toggle password visibility"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              <div className="auth-input-note">
                At least 12 characters, no more than 20 characters.<br />
                Uppercase letters, lowercase letters, numbers, and symbols.
              </div>
            </div>

            {/* Primary "Continue" Button */}
            <button
              type="submit"
              className="auth-continue-btn"
              disabled={loading}
            >
              {loading ? (
                'Processing…'
              ) : (
                <>
                  <span>Continue</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          {/* Switch Mode Prompt: "Already have an account? Log in" */}
          <div className="auth-switch-prompt">
            {mode === 'signup' ? (
              <>
                <span>Already have an account?</span>
                <button
                  type="button"
                  className="auth-switch-link"
                  style={{ background: 'none', border: 'none', font: 'inherit', padding: 0 }}
                  onClick={() => setMode('login')}
                >
                  Log in
                </button>
              </>
            ) : (
              <>
                <span>Already have an account?</span>
                <button
                  type="button"
                  className="auth-switch-link"
                  style={{ background: 'none', border: 'none', font: 'inherit', padding: 0 }}
                  onClick={() => setMode(mode === 'login' ? 'signup' : 'login')}
                >
                  {mode === 'login' ? 'Log in' : 'Join us'}
                </button>
              </>
            )}
          </div>

          {/* "Or" Divider */}
          <div className="auth-divider-row">
            <div className="auth-divider-line" />
            <span className="auth-divider-text">Or</span>
            <div className="auth-divider-line" />
          </div>

          {/* Social Google Sign-Up Button */}
          <button
            type="button"
            className="auth-google-btn"
            onClick={() => handleQuickBypass('customer')}
            title="Quick test via Google SSO simulation"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
              <path
                fill="#4285F4"
                d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"
              />
              <path
                fill="#34A853"
                d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24z"
              />
              <path
                fill="#FBBC05"
                d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.99 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
              />
              <path
                fill="#EA4335"
                d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
              />
            </svg>
            <span>{mode === 'signup' ? 'Sign up with Google' : 'Sign up with Google'}</span>
          </button>

          {/*   1-Click Instant Demo Bypass (Requirement Compliance) */}
          <div className="auth-bypass-container">
            <div className="auth-bypass-header">
              <span className="auth-bypass-title">  Instant Demo Bypass</span>
              <button
                type="button"
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#2563eb',
                  fontSize: '11px',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
                onClick={() => setFakeModalOpen(true)}
              >
                Modal View
              </button>
            </div>
            <div className="auth-bypass-pill-grid">
              <button
                type="button"
                className="auth-bypass-pill"
                onClick={() => handleQuickBypass('customer')}
                title="Bypass as Customer"
              >
                🏠 Customer
              </button>
              <button
                type="button"
                className="auth-bypass-pill"
                onClick={() => handleQuickBypass('sales')}
                title="Bypass as Sales Officer"
              >
                📈 Sales
              </button>
              <button
                type="button"
                className="auth-bypass-pill"
                onClick={() => handleQuickBypass('technician')}
                title="Bypass as Field Technician"
              >
                🔧 Tech
              </button>
              <button
                type="button"
                className="auth-bypass-pill"
                onClick={() => handleQuickBypass('warehouse')}
                title="Bypass as Warehouse Manager"
              >
                📦 Warehouse
              </button>
              <button
                type="button"
                className="auth-bypass-pill"
                onClick={() => handleQuickBypass('support')}
                title="Bypass as Support Specialist"
              >
                🎧 Support
              </button>
              <button
                type="button"
                className="auth-bypass-pill"
                onClick={() => handleQuickBypass('admin')}
                title="Bypass as Administrator"
              >
                🛡️ Admin
              </button>
            </div>
          </div>

          {/* Legal Disclaimer Note */}
          <p className="auth-disclaimer-note">
            By signing up I confirm that I carefully have read and agree to the SolarOps{' '}
            <a href="#privacy">Privacy Policy</a> and <a href="#terms">Terms of Service</a>.
          </p>
        </div>
      </section>

      {/* Modal View for Full Persona Switcher */}
      <FakeLoginModal
        isOpen={fakeModalOpen}
        onClose={() => setFakeModalOpen(false)}
      />
    </div>
  );
}

export default Login;
