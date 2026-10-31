import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useRouter, Link } from '../../router/Router';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { TextField } from '../../components/TextField/TextField';
import { ErrorState } from '../../components/ErrorState/ErrorState';
import { Zap } from 'lucide-react';
import './Signup.css';
import '../Login/Login.css';

export function Signup() {
  const { signup } = useAuth();
  const { navigate } = useRouter();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [addressLine1, setAddressLine1] = useState('');
  const [city, setCity] = useState('Bengaluru');
  const [state, setState] = useState('Karnataka');
  const [postalCode, setPostalCode] = useState('560001');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await signup({
        full_name: fullName,
        email,
        phone,
        password,
        address: `${addressLine1}, ${city}, ${state} ${postalCode}`,
      });
      navigate(`/verify-email?email=${encodeURIComponent(email)}`);
    } catch (err) {
      setError(err.message || 'Signup failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="signup-container">
      <div className="signup-card-wrapper">
        <div className="login-header-branding">
          <div className="login-brand-logo">
            <div className="login-brand-icon">
              <Zap size={24} fill="#000000" />
            </div>
            <span>SolarOps</span>
          </div>
          <p className="login-tagline">Rooftop Solar Customer Onboarding</p>
        </div>

        <Card elevated accent="lime">
          <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '8px' }}>Create Your Account</h2>
          <p style={{ color: 'var(--color-white-dim)', fontSize: '13px', marginBottom: '20px' }}>
            Register to request custom solar capacity calculations, quotations, and live rooftop installation tracking.
          </p>

          {error && <ErrorState message={error} />}

          <form onSubmit={handleSubmit}>
            <TextField
              label="Full Name"
              name="fullName"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Rahul Verma"
              required
            />

            <div className="signup-grid-2">
              <TextField
                label="Email Address"
                name="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="rahul@example.com"
                required
              />

              <TextField
                label="Mobile Phone"
                name="phone"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+91 98765 43210"
                required
              />
            </div>

            <TextField
              label="Password (min 8 characters)"
              name="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            <TextField
              label="Installation Address Line 1"
              name="addressLine1"
              value={addressLine1}
              onChange={(e) => setAddressLine1(e.target.value)}
              placeholder="House/Villa/Building No, Street"
              required
            />

            <div className="signup-grid-2">
              <TextField
                label="City"
                name="city"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                required
              />

              <TextField
                label="Postal Code (PIN)"
                name="postalCode"
                value={postalCode}
                onChange={(e) => setPostalCode(e.target.value)}
                required
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              fullWidth
              size="lg"
              disabled={loading}
              style={{ marginTop: '12px' }}
            >
              {loading ? 'Creating Account…' : 'Submit Registration'}
            </Button>
          </form>

          <div className="login-footer-links">
            <span>Already registered? </span>
            <Link href="/login">Sign in here</Link>
          </div>
        </Card>
      </div>
    </div>
  );
}

