import React, { useState } from 'react';
import { useRouter } from '../../router/Router';
import './TransactionCard.css';

/**
 * Interactive POS Terminal Component
 *
 * Implements the card-swipe POS terminal animation on hover and click,
 * redirecting to the live payment checkout.
 */
export function TransactionCard({
  currencySymbol = '₹',
}) {
  const { navigate } = useRouter();
  const [isProcessing, setIsProcessing] = useState(false);

  const handleTriggerTransaction = () => {
    setIsProcessing(true);
    // Play terminal swipe animation, then redirect to Razorpay payment page
    setTimeout(() => {
      navigate('/customer/payments/razorpay');
    }, 420);
  };

  return (
    <div className="pos-transaction-wrapper">
      {/* ANIMATED POS TERMINAL & CARD SWIPE */}
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
    </div>
  );
}

export default TransactionCard;
