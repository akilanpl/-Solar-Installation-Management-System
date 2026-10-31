import React from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { Badge } from '../../components/Badge/Badge';
import { TransactionCard } from '../../components/TransactionCard/TransactionCard';
import { useAuth } from '../../context/AuthContext';
import { CreditCard, CheckCircle2, Clock, Landmark, ArrowUpRight } from 'lucide-react';
import './CustomerPayments.css';

const MILESTONES = [
  {
    title: 'Milestone 1: Project Engineering & Design Advance',
    percent: '10%',
    amount: '₹34,000',
    status: 'paid',
    date: 'Paid on 24 Oct 2026 · Ref #TXN-9028',
    actionText: 'Download Receipt',
  },
  {
    title: 'Milestone 2: Material Dispatch from Warehouse',
    percent: '50%',
    amount: '₹1,70,000',
    status: 'pending',
    date: 'Due upon technical qualification & BOM allocation',
    actionText: 'Pay via UPI / Netbanking',
  },
  {
    title: 'Milestone 3: Structural Mounting & Module Placement',
    percent: '30%',
    amount: '₹1,02,000',
    status: 'upcoming',
    date: 'Due after technician roof rail torque test',
    actionText: 'Locked',
  },
  {
    title: 'Milestone 4: BESCOM Net Metering & System Commissioning',
    percent: '10%',
    amount: '₹34,000',
    status: 'upcoming',
    date: 'Due upon bidirectional meter turn-on',
    actionText: 'Locked',
  },
];

export function CustomerPayments() {
  const { showToast } = useAuth();

  const handlePay = (title) => {
    showToast(`Payment portal simulation opened for: ${title}`);
  };

  return (
    <AppShell requiredRole="customer">
      <PageHeader
        title="Escrow Milestones & Payment Schedule"
        description="Structured milestone disbursements tied directly to physical engineering inspection and delivery."
      />

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
        <div>
          <Card>
            <h3 style={{ fontSize: '17px', fontWeight: '700', marginBottom: '4px' }}>
              Installation Milestones (5 kW Hybrid Project)
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-white-dim)', marginBottom: '16px' }}>
              Total Contract Value: <strong>₹3,40,000</strong> (before ₹78,000 central subsidy credit)
            </p>

            <div className="payment-milestones-list">
              {MILESTONES.map((m, idx) => (
                <div
                  key={idx}
                  className={`payment-milestone-card ${m.status === 'paid' ? 'paid' : ''}`}
                >
                  <div className="payment-info-col">
                    <span className="payment-title">
                      {m.status === 'paid' ? (
                        <CheckCircle2 size={18} color="var(--color-lime)" />
                      ) : (
                        <Clock size={18} color="var(--color-white-dim)" />
                      )}
                      <span>{m.title}</span>
                    </span>
                    <span className="payment-desc">{m.date}</span>
                  </div>

                  <div className="payment-amount-col">
                    <span className="payment-amount">{m.amount}</span>
                    {m.status === 'paid' ? (
                      <Badge variant="success">Completed</Badge>
                    ) : m.status === 'pending' ? (
                      <Button size="sm" variant="primary" onClick={() => handlePay(m.title)}>
                        <span>Pay Milestone</span>
                        <ArrowUpRight size={14} />
                      </Button>
                    ) : (
                      <Badge variant="neutral">Upcoming</Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Right Column: Subsidy Info & Razorpay Processed Transaction Card */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
              <Landmark size={22} color="#10b981" />
              <h3 style={{ fontSize: '17px', fontWeight: '700', color: '#111827' }}>Direct Benefit Subsidy</h3>
            </div>

            <div style={{ padding: '16px', background: '#f8fafc', border: '1px solid #edf0f5', borderRadius: '14px', marginBottom: '16px' }}>
              <span style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '700' }}>
                National PM Surya Ghar Portal
              </span>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#10b981', marginTop: '4px', letterSpacing: '-0.5px' }}>
                ₹78,000
              </div>
              <p style={{ fontSize: '12.5px', color: '#475569', marginTop: '6px', lineHeight: '1.45' }}>
                Government subsidy credited directly to your Aadhaar-linked bank account within 30 days of bidirectional meter installation.
              </p>
            </div>

            <div style={{ fontSize: '13px', color: '#64748b', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Application ID:</span>
                <strong style={{ color: '#0f172a', fontWeight: '700' }}>PMSG-KA-2026-9912</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>DISCOM:</span>
                <strong style={{ color: '#0f172a', fontWeight: '700' }}>BESCOM Bengaluru</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Status:</span>
                <span style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  background: '#f0f9ff',
                  border: '1px solid #bae6fd',
                  color: '#0284c7',
                  fontSize: '11px',
                  fontWeight: '700',
                  padding: '3px 10px',
                  borderRadius: '9999px',
                  letterSpacing: '0.04em',
                }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#0284c7' }} />
                  DOCUMENT VERIFIED
                </span>
              </div>
            </div>
          </Card>

          {/* New Transaction Interactive POS Terminal */}
          <TransactionCard currencySymbol="₹" />
        </div>
      </div>
    </AppShell>
  );
}

