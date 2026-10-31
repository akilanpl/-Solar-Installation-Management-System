import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from '../../router/Router';
import { AppShell } from '../../components/AppShell/AppShell';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { TextField } from '../../components/TextField/TextField';
import { SelectField } from '../../components/SelectField/SelectField';
import { ErrorState } from '../../components/ErrorState/ErrorState';
import { api } from '../../services/api';
import { formatInrFromPaise, formatCapacity } from '../../lib/format';
import { Zap, Sun, ShieldCheck, ArrowLeft, Send } from 'lucide-react';
import './NewEnquiry.css';
import '../Signup/Signup.css';

const PRESETS = [
  { watts: 3000, label: '3 kW (Small Home)' },
  { watts: 5000, label: '5 kW (3BHK Villa)' },
  { watts: 8000, label: '8 kW (Large Home)' },
  { watts: 10000, label: '10 kW (Commercial)' },
];

export function NewEnquiry() {
  const { user } = useAuth();
  const { navigate } = useRouter();

  const [capacityWatts, setCapacityWatts] = useState(5000);
  const [monthlyBill, setMonthlyBill] = useState(6500);
  const [gridPreference, setGridPreference] = useState('on_grid');
  const [roofType, setRoofType] = useState('Reinforced Concrete (Flat)');
  const [roofAreaSqft, setRoofAreaSqft] = useState(750);
  const [addressLine1, setAddressLine1] = useState(user?.address?.split(',')[0] || '42 Green Energy Avenue');
  const [addressLine2, setAddressLine2] = useState('Koramangala 4th Block');
  const [city, setCity] = useState('Bengaluru');
  const [state, setState] = useState('Karnataka');
  const [postalCode, setPostalCode] = useState('560034');
  const [phone, setPhone] = useState(user?.phone || '+91 98765 43210');
  const [notes, setNotes] = useState('Looking to offset peak air conditioning daytime usage.');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Estimator Calculations
  const kw = capacityWatts / 1000;
  const estimatedPanels = Math.ceil(capacityWatts / 540); // 540W Mono PERC
  const dailyKwh = (kw * 4.3).toFixed(1); // 4.3 peak sun hours avg
  const monthlyKwh = Math.round(dailyKwh * 30);
  const estimatedSavingsRupees = Math.round(monthlyKwh * 7.5); // Rs 7.5/unit

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const payload = {
        preferred_capacity_w: Number(capacityWatts),
        monthly_bill_rupees: Number(monthlyBill),
        grid_preference: gridPreference,
        roof_type: roofType,
        roof_area_sqft: Number(roofAreaSqft),
        installation_address_line1: addressLine1,
        installation_address_line2: addressLine2,
        city,
        state,
        postal_code: postalCode,
        contact_phone: phone,
        notes,
      };

      const result = await api.createEnquiry(payload);
      navigate(`/customer/enquiries/${result.id}`);
    } catch (err) {
      setError(err.message || 'Failed to submit enquiry.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell requiredRole="customer">
      <PageHeader
        title="Submit New Solar Connection Enquiry"
        description="Provide site parameters and electrical utility details for engineering qualification."
        action={
          <Button variant="outline" icon={<ArrowLeft size={16} />} onClick={() => navigate('/customer')}>
            Back to Dashboard
          </Button>
        }
      />

      {error && <ErrorState message={error} />}

      <form onSubmit={handleSubmit}>
        <div className="enquiry-layout-grid">
          {/* Main Form Fields */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <Card accent="violet">
              <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px' }}>
                1. System Sizing & Energy Consumption
              </h3>

              <div style={{ marginBottom: '14px' }}>
                <label className="field-label" style={{ marginBottom: '8px' }}>
                  Quick Sizing Presets
                </label>
                <div className="capacity-preset-row">
                  {PRESETS.map((p) => (
                    <button
                      key={p.watts}
                      type="button"
                      className={`capacity-preset-btn ${capacityWatts === p.watts ? 'selected' : ''}`}
                      onClick={() => setCapacityWatts(p.watts)}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="signup-grid-2">
                <TextField
                  label="Target Solar System Capacity (Watts)"
                  name="capacityWatts"
                  type="number"
                  step="500"
                  min="1000"
                  max="50000"
                  value={capacityWatts}
                  onChange={(e) => setCapacityWatts(e.target.value)}
                  required
                  hint={`Equivalent to ${(capacityWatts / 1000).toFixed(1)} kW`}
                />

                <TextField
                  label="Average Monthly Electricity Bill (₹)"
                  name="monthlyBill"
                  type="number"
                  min="500"
                  value={monthlyBill}
                  onChange={(e) => setMonthlyBill(e.target.value)}
                  required
                  hint="Used to compute financial payback period"
                />
              </div>

              <div className="signup-grid-2">
                <SelectField
                  label="Grid Architecture Preference"
                  name="gridPreference"
                  value={gridPreference}
                  onChange={(e) => setGridPreference(e.target.value)}
                  required
                >
                  <option value="on_grid">On-Grid (Net Metering with DISCOM)</option>
                  <option value="hybrid">Hybrid (Grid + Battery Storage Backup)</option>
                  <option value="off_grid">Off-Grid (Stand-Alone Battery Only)</option>
                </SelectField>

                <SelectField
                  label="Roof Structural Composition"
                  name="roofType"
                  value={roofType}
                  onChange={(e) => setRoofType(e.target.value)}
                  required
                >
                  <option value="Reinforced Concrete (Flat)">Reinforced Concrete (Flat)</option>
                  <option value="Sloped Clay Tile">Sloped Clay Tile</option>
                  <option value="Industrial Metal Sheet">Industrial Metal Sheet</option>
                  <option value="Tin / Asbestos Shed">Tin / Asbestos Shed</option>
                </SelectField>
              </div>

              <TextField
                label="Available Shadow-Free Roof Area (Approx. sq. ft.)"
                name="roofAreaSqft"
                type="number"
                value={roofAreaSqft}
                onChange={(e) => setRoofAreaSqft(e.target.value)}
                hint="Approximately 100 sq. ft. required per 1 kW"
                required
              />
            </Card>

            <Card accent="lime">
              <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px' }}>
                2. Site Location & Contact Details
              </h3>

              <TextField
                label="Site Address Line 1"
                name="addressLine1"
                value={addressLine1}
                onChange={(e) => setAddressLine1(e.target.value)}
                required
              />

              <TextField
                label="Site Address Line 2 (Landmark / Area)"
                name="addressLine2"
                value={addressLine2}
                onChange={(e) => setAddressLine2(e.target.value)}
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
                  label="State"
                  name="state"
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                  required
                />
              </div>

              <div className="signup-grid-2">
                <TextField
                  label="Postal Code (PIN)"
                  name="postalCode"
                  value={postalCode}
                  onChange={(e) => setPostalCode(e.target.value)}
                  required
                />

                <TextField
                  label="Site Contact Mobile Number"
                  name="phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  required
                />
              </div>

              <TextField
                label="Additional Requirements / Roof Access Notes"
                name="notes"
                as="textarea"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. Existing 3-phase meter, parapet height 3ft, lift room on North side…"
              />
            </Card>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              icon={<Send size={18} />}
              disabled={loading}
            >
              {loading ? 'Transmitting Enquiry to Sales Queue…' : 'Submit Solar Connection Enquiry'}
            </Button>
          </div>

          {/* Real-time System Estimator Widget */}
          <div>
            <div className="estimator-summary-box">
              <div className="estimator-heading">
                <Sun size={20} />
                <span>Solar Feasibility Engine</span>
              </div>

              <div className="estimator-metric-row">
                <span className="estimator-metric-label">Target System</span>
                <span className="estimator-metric-val">{formatCapacity(capacityWatts)}</span>
              </div>

              <div className="estimator-metric-row">
                <span className="estimator-metric-label">Estimated Modules</span>
                <span className="estimator-metric-val">{estimatedPanels}x 540W Bifacial</span>
              </div>

              <div className="estimator-metric-row">
                <span className="estimator-metric-label">Roof Area Required</span>
                <span className="estimator-metric-val">~{Math.round(kw * 95)} sq. ft.</span>
              </div>

              <div className="estimator-metric-row">
                <span className="estimator-metric-label">Avg. Daily Generation</span>
                <span className="estimator-metric-val">{dailyKwh} kWh / day</span>
              </div>

              <div className="estimator-metric-row">
                <span className="estimator-metric-label">Monthly Generation</span>
                <span className="estimator-metric-val">{monthlyKwh} Units</span>
              </div>

              <div className="estimator-highlight">
                <div className="estimator-highlight-val">
                  {formatInrFromPaise(estimatedSavingsRupees * 100)}
                </div>
                <div className="estimator-highlight-label">Est. Monthly Bill Reduction</div>
              </div>

              <div style={{ marginTop: '16px', display: 'flex', gap: '8px', alignItems: 'center', fontSize: '11px', color: 'var(--color-white-dim)' }}>
                <ShieldCheck size={16} color="var(--color-lime)" />
                <span>Eligible for Central Subsidy up to ₹78,000 under PM Surya Ghar.</span>
              </div>
            </div>
          </div>
        </div>
      </form>
    </AppShell>
  );
}

