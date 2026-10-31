import React from 'react';
import { AppShell } from '../../components/AppShell/AppShell';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { Card } from '../../components/Card/Card';
import { Button } from '../../components/Button/Button';
import { Badge } from '../../components/Badge/Badge';
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
          <Card accent="violet">
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

        {/* Subsidy Info */}
        <div>
          <Card accent="lime">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
              <Landmark size={22} color="var(--color-lime)" />
              <h3 style={{ fontSize: '17px', fontWeight: '700' }}>Direct Benefit Subsidy</h3>
            </div>

            <div style={{ padding: '16px', background: 'var(--color-black-surface)', borderRadius: 'var(--radius-sm)', marginBottom: '16px' }}>
              <span style={{ fontSize: '11px', color: 'var(--color-white-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                National PM Surya Ghar Portal
              </span>
              <div style={{ fontSize: '26px', fontWeight: '800', color: 'var(--color-lime)', marginTop: '4px' }}>
                ₹78,000
              </div>
              <p style={{ fontSize: '12px', color: 'var(--color-white-muted)', marginTop: '6px' }}>
                Government subsidy credited directly to your Aadhaar-linked bank account within 30 days of bidirectional meter installation.
              </p>
            </div>

            <div style={{ fontSize: '13px', color: 'var(--color-white-dim)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Application ID:</span>
                <strong style={{ color: 'var(--color-white)' }}>PMSG-KA-2026-9912</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>DISCOM:</span>
                <strong style={{ color: 'var(--color-white)' }}>BESCOM Bengaluru</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Status:</span>
                <Badge variant="info">Document Verified</Badge>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

