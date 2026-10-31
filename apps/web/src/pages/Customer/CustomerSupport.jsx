import React, { useState } from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { TextField } from '../../components/TextField/TextField';
import { SelectField } from '../../components/SelectField/SelectField';
import { Badge } from '../../components/Badge/Badge';
import { useAuth } from '../../context/AuthContext';
import { LifeBuoy, Send, PhoneCall, HelpCircle, ShieldAlert } from 'lucide-react';
import './CustomerSupport.css';

const FAQ = [
  { q: 'How long does net-metering commissioning take?', a: 'DISCOM bidirectional inspection takes between 14 to 21 working days after physical solar structure installation.' },
  { q: 'Do solar panels generate power during cloudy/rainy days?', a: 'Yes. Bifacial mono-PERC panels utilize diffuse ultraviolet irradiance, generating 25%–35% of peak capacity during monsoon days.' },
  { q: 'When is inverter warranty service available?', a: 'SunPower provides same-day rapid field service in Bengaluru with 10-year replacement warranty on hybrid inverters.' },
];

export function CustomerSupport() {
  const { showToast } = useAuth();
  const [subject, setSubject] = useState('');
  const [category, setCategory] = useState('technical');
  const [message, setMessage] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitted(true);
    showToast('Support ticket logged with reference #TK-1088. An engineer will contact you.');
  };

  return (
    <AppShell requiredRole="customer">
      <PageHeader
        title="Customer Support & Warranty Assistance"
        description="24/7 technical operations desk for grid interconnection, inverter telemetry, and PM Surya Ghar assistance."
      />

      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '20px' }}>
        <div>
          <Card accent="violet">
            <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px' }}>
              Create Support Request
            </h3>

            {submitted ? (
              <div style={{ padding: '24px', textAlign: 'center', background: 'var(--color-black-surface)', borderRadius: 'var(--radius-sm)' }}>
                <span style={{ fontSize: '36px' }}> </span>
                <h4 style={{ fontSize: '18px', fontWeight: '700', marginTop: '12px' }}>Ticket Submitted!</h4>
                <p style={{ color: 'var(--color-white-dim)', fontSize: '13px', marginTop: '6px' }}>
                  Your service ticket <strong>#TK-1088</strong> is assigned to our customer support engineer.
                </p>
                <Button variant="outline" size="sm" style={{ marginTop: '16px' }} onClick={() => setSubmitted(false)}>
                  Submit Another Query
                </Button>
              </div>
            ) : (
              <form onSubmit={handleSubmit}>
                <SelectField
                  label="Inquiry Category"
                  name="category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  required
                >
                  <option value="technical">Technical / Inverter Error Code</option>
                  <option value="grid">Net Metering & BESCOM DISCOM Status</option>
                  <option value="subsidy">National Portal Subsidy Clarification</option>
                  <option value="billing">Billing & Payment Milestone Query</option>
                  <option value="warranty">Annual Maintenance & Warranty Claim</option>
                </SelectField>

                <TextField
                  label="Subject / Issue Summary"
                  name="subject"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="e.g. WiFi monitoring module offline after power cut"
                  required
                />

                <TextField
                  label="Detailed Description"
                  name="message"
                  as="textarea"
                  rows={4}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Provide any error codes, panel noise, or specific questions…"
                  required
                />

                <Button type="submit" variant="primary" icon={<Send size={16} />}>
                  Dispatch Ticket to Support Desk
                </Button>
              </form>
            )}
          </Card>
        </div>

        {/* Hotlines and FAQ */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <Card accent="lime">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
              <PhoneCall size={20} color="var(--color-lime)" />
              <h3 style={{ fontSize: '16px', fontWeight: '700' }}>Direct Operations Hotline</h3>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--color-white-dim)', marginBottom: '14px' }}>
              For electrical inverter trip emergencies or rooftop storm damage:
            </p>
            <div style={{ padding: '12px', background: 'var(--color-black-surface)', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
              <span style={{ fontSize: '18px', fontWeight: '800', color: 'var(--color-lime)', fontFamily: 'var(--font-mono)' }}>
                1800-425-SOLAR (76527)
              </span>
              <p style={{ fontSize: '11px', color: 'var(--color-white-dim)', marginTop: '4px' }}>
                Mon-Sat 8:00 AM – 8:00 PM IST
              </p>
            </div>
          </Card>

          <Card>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
              <HelpCircle size={20} color="var(--color-violet-light)" />
              <h3 style={{ fontSize: '16px', fontWeight: '700' }}>Frequently Asked Questions</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {FAQ.map((item, idx) => (
                <div key={idx} style={{ paddingBottom: '10px', borderBottom: idx < FAQ.length - 1 ? '1px solid var(--color-border-subtle)' : 'none' }}>
                  <h4 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-white)' }}>{item.q}</h4>
                  <p style={{ fontSize: '12px', color: 'var(--color-white-dim)', marginTop: '4px' }}>{item.a}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

