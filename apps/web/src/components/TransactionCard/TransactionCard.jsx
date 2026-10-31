import React, { useState } from 'react';
import { CheckCircle2, ArrowRight, Zap, ShieldCheck } from 'lucide-react';
import { useRouter } from '../../router/Router';
import { useAuth } from '../../context/AuthContext';
import './TransactionCard.css';

/**
 * Interactive POS Terminal & Razorpay Settlement Card
 *
 * Implements the card-swipe POS terminal animation on hover and click,
 * paired with real-time Razorpay settlement status indicating funds
 * were just credited to the customer's Aadhaar-linked bank account.
 */
export function TransactionCard({
  amount = '₹78,000.00',
  accountNumber = '•••• 4921',
  utrNumber = 'RZP91823902381',
  beneficiary = 'Arun Kumar',
  currencySymbol = '₹',
}) {
  const { navigate } = useRouter();
  const { showToast } = useAuth();
  const [isProcessing, setIsProcessing] = useState(false);
  const [settledTime, setSettledTime] = useState('Just now');

  const handleTriggerTransaction = () => {
    setIsProcessing(true);
    // Play terminal swipe animation, then redirect to Razorpay payment page
    setTimeout(() => {
      navigate('/customer/payments/razorpay');
    }, 420);
  };

  return (
    <div className="pos-transaction-wrapper">
      {/* ===================================================================
          ANIMATED POS TERMINAL & CARD SWIPE (User Reference Component)
          =================================================================== */}
      <div
        className={`pos-container ${isProcessing ? 'active-swipe' : ''}`}
        onClick={handleTriggerTransaction}
        role="button"
        tabIndex={0}
        title="Click to view live settlement details"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleTriggerTransaction();
          }
        }}
      >
        <div className="pos-left-side">
          <div className="pos-card">
            <div className="pos-card-line" />
            <div className="pos-buttons" />
          </div>
          <div className="pos-post">
            <div className="pos-post-line" />
            <div className="pos-screen">
              <div className="pos-dollar">{currencySymbol}</div>
            </div>
            <div className="pos-numbers" />
            <div className="pos-numbers-line2" />
          </div>
        </div>

        <div className="pos-right-side">
          <div className="pos-new">New Transaction</div>
          <svg
            viewBox="0 0 451.846 451.847"
            xmlns="http://www.w3.org/2000/svg"
            className="pos-arrow"
            aria-hidden="true"
          >
            <path
              fill="#94a3b8"
              d="M345.441 248.292L151.154 442.573c-12.359 12.365-32.397 12.365-44.75 0-12.354-12.354-12.354-32.391 0-44.744L278.318 225.92 106.409 54.017c-12.354-12.359-12.354-32.394 0-44.748 12.354-12.359 32.391-12.359 44.75 0l194.287 194.284c6.177 6.18 9.262 14.271 9.262 22.366 0 8.099-3.091 16.196-9.267 22.373z"
            />
          </svg>
        </div>
      </div>

      {/* ===================================================================
          RAZORPAY PROCESSED DISBURSEMENT CARD ("Just Credited")
          =================================================================== */}
      <div className="rzp-settlement-card">
        {/* Header: Razorpay Route & Credited Status */}
        <div className="rzp-settlement-header">
          <div className="rzp-brand-badge">
            <div className="rzp-logo-mark">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M13.5 2L5 13h5l-2 9 11-12h-5.5z" />
              </svg>
            </div>
            <span className="rzp-brand-name">Razorpay Route</span>
            <span className="rzp-verified-chip">
              <ShieldCheck size={12} color="#0284c7" />
              <span>Verified Payout</span>
            </span>
          </div>

          <span className="rzp-status-pill credited">
            <span className="rzp-status-dot" />
            Just Credited
          </span>
        </div>

        {/* Amount & Direct Settlement Row */}
        <div className="rzp-amount-row">
          <div className="rzp-amount-col">
            <span className="rzp-amount-label">Net Disbursed Subsidy</span>
            <span className="rzp-amount-value">{amount}</span>
          </div>
          <div className="rzp-instant-chip">
            <Zap size={12} />
            <span>Instant IMPS</span>
          </div>
        </div>

        {/* Detailed Banking & Reconciliation Metadata */}
        <div className="rzp-details-list">
          <div className="rzp-detail-item">
            <span className="rzp-detail-label">Beneficiary Account:</span>
            <strong className="rzp-detail-value">
              {beneficiary} (A/C {accountNumber})
            </strong>
          </div>

          <div className="rzp-detail-item">
            <span className="rzp-detail-label">Bank Reference UTR:</span>
            <strong className="rzp-detail-value mono">{utrNumber}</strong>
          </div>

          <div className="rzp-detail-item">
            <span className="rzp-detail-label">Settlement Route:</span>
            <span className="rzp-detail-value">DBT Direct Credit · National Portal</span>
          </div>

          <div className="rzp-detail-item">
            <span className="rzp-detail-label">Status:</span>
            <span className="rzp-detail-status">
              <CheckCircle2 size={13} color="#10b981" />
              <strong style={{ color: '#047857' }}>Credited · {settledTime}</strong>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TransactionCard;

