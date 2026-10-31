import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useRouter, Link } from '../../router/Router';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { TextField } from '../../components/TextField/TextField';
import { ErrorState } from '../../components/ErrorState/ErrorState';
import { api } from '../../services/api';
import { Zap, MailCheck } from 'lucide-react';
import './VerifyEmail.css';
import '../Login/Login.css';

export function VerifyEmail() {
  const { verifyEmail } = useAuth();
  const { navigate, query } = useRouter();

  const [email, setEmail] = useState(query.email || 'customer@solarops.dev');
  const [code, setCode] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [devCode, setDevCode] = useState(null);

  useEffect(() => {
    if (email) {
      api.getDevMailboxCode(email).then((c) => {
        if (c) setDevCode(c);
      });
    }
  }, [email]);

  const handleUseDevCode = () => {
    if (devCode) setCode(devCode);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await verifyEmail(email, code);
      navigate('/login?verified=1');
    } catch (err) {
      setError(err.message || 'Verification code invalid.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="verify-container">
      <div className="verify-card-wrapper">
        <div className="login-header-branding">
          <div className="login-brand-logo">
            <div className="login-brand-icon">
              <MailCheck size={24} color="#000000" />
            </div>
            <span>SolarOps</span>
          </div>
          <p className="login-tagline">Security Verification</p>
        </div>

        <Card elevated>
          <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '8px' }}>Verify Your Email</h2>
          <p style={{ color: 'var(--color-white-dim)', fontSize: '13px', marginBottom: '20px' }}>
            We dispatched a 6-digit verification code to <strong>{email}</strong>.
          </p>

          {devCode && (
            <div className="dev-mailbox-helper-box">
              <span className="dev-mailbox-helper-text">
                Dev Mailbox OTP: <strong>{devCode}</strong>
              </span>
              <Button size="sm" variant="secondary" onClick={handleUseDevCode}>
                Autofill
              </Button>
            </div>
          )}

          {error && <ErrorState message={error} />}

          <form onSubmit={handleSubmit}>
            <TextField
              label="Account Email"
              name="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

            <div className="otp-input-group">
              <TextField
                label="6-Digit Verification Code"
                name="code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="123456"
                maxLength={6}
                required
                hint="Enter the code sent to your email or dev mailbox"
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              fullWidth
              size="lg"
              disabled={loading || code.length < 4}
            >
              {loading ? 'Verifying Code…' : 'Verify & Continue to Login'}
            </Button>
          </form>

          <div className="login-footer-links">
            <Link href="/login">Return to Sign In</Link>
          </div>
        </Card>
      </div>
    </div>
  );
}

