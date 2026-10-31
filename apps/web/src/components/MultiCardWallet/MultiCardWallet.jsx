import React, { useState } from 'react';
import { CheckCircle2, ShieldCheck } from 'lucide-react';
import './MultiCardWallet.css';

export function MultiCardWallet({
  selectedCard = 'stripe',
  onSelectCard,
  balance = '$12,450.00',
}) {
  const [activeCard, setActiveCard] = useState(selectedCard);

  const handleCardClick = (cardId, cardData) => {
    setActiveCard(cardId);
    if (onSelectCard) {
      onSelectCard(cardId, cardData);
    }
  };

  const currentActive = selectedCard || activeCard;

  return (
    <div className="multi-card-wallet-wrapper">
      <div className="wallet-outer-box">
        <div className="wallet" title="Hover to inspect cards · Click to select payment card">
          <div className="wallet-back" />

          {/* 1. Stripe Card */}
          <div
            className={`card stripe ${currentActive === 'stripe' ? 'selected' : ''}`}
            onClick={() =>
              handleCardClick('stripe', {
                brand: 'Stripe',
                holder: 'ALEX SMITH',
                number: '5524 9910 4242',
                exp: '08/29',
                cvc: '892',
              })
            }
            role="button"
            tabIndex={0}
            aria-label="Select Stripe Card (Alex Smith)"
          >
            <div className="card-inner">
              <div className="card-top">
                <div className="card-brand-label">
                  <span>Stripe</span>
                  {currentActive === 'stripe' && (
                    <span className="card-active-check">✓ Active</span>
                  )}
                </div>
                <div className="chip" />
              </div>
              <div className="card-bottom">
                <div className="card-info">
                  <span className="label">Holder</span>
                  <span className="value">ALEX SMITH</span>
                </div>
                <div className="card-number-wrapper">
                  <span className="hidden-stars">**** 4242</span>
                  <span className="card-number">5524 9910 4242</span>
                </div>
              </div>
            </div>
          </div>

          {/* 2. Wise Card */}
          <div
            className={`card wise ${currentActive === 'wise' ? 'selected' : ''}`}
            onClick={() =>
              handleCardClick('wise', {
                brand: 'Wise',
                holder: 'STUDIO LLC',
                number: '9012 4432 8810',
                exp: '11/28',
                cvc: '417',
              })
            }
            role="button"
            tabIndex={0}
            aria-label="Select Wise Business Card (Studio LLC)"
          >
            <div className="card-inner">
              <div className="card-top">
                <div className="card-brand-label">
                  <span>Wise</span>
                  {currentActive === 'wise' && (
                    <span className="card-active-check dark">✓ Active</span>
                  )}
                </div>
                <div className="chip" />
              </div>
              <div className="card-bottom">
                <div className="card-info">
                  <span className="label">Business</span>
                  <span className="value">STUDIO LLC</span>
                </div>
                <div className="card-number-wrapper">
                  <span className="hidden-stars">**** 8810</span>
                  <span className="card-number">9012 4432 8810</span>
                </div>
              </div>
            </div>
          </div>

          {/* 3. PayPal Card */}
          <div
            className={`card paypal ${currentActive === 'paypal' ? 'selected' : ''}`}
            onClick={() =>
              handleCardClick('paypal', {
                brand: 'PayPal',
                holder: 'hello@work.com',
                number: '3312 0045 0094',
                exp: '05/27',
                cvc: '109',
              })
            }
            role="button"
            tabIndex={0}
            aria-label="Select PayPal Card (hello@work.com)"
          >
            <div className="card-inner">
              <div className="card-top">
                <div className="card-brand-label">
                  <span>
                    Pay<b style={{ color: '#0079C1' }}>Pal</b>
                  </span>
                  {currentActive === 'paypal' && (
                    <span className="card-active-check blue">✓ Active</span>
                  )}
                </div>
                <div className="chip" />
              </div>
              <div className="card-bottom">
                <div className="card-info">
                  <span className="label">Email</span>
                  <span className="value">hello@work.com</span>
                </div>
                <div className="card-number-wrapper">
                  <span className="hidden-stars">**** 0094</span>
                  <span className="card-number">3312 0045 0094</span>
                </div>
              </div>
            </div>
          </div>

          {/* Leather Wallet Pocket */}
          <div className="pocket">
            <svg className="pocket-svg" viewBox="0 0 280 160" fill="none">
              <path
                d="M 0 20 C 0 10, 5 10, 10 10 C 20 10, 25 25, 40 25 L 240 25 C 255 25, 260 10, 270 10 C 275 10, 280 10, 280 20 L 280 120 C 280 155, 260 160, 240 160 L 40 160 C 20 160, 0 155, 0 120 Z"
                fill="#1e341e"
              />
              <path
                d="M 8 22 C 8 16, 12 16, 15 16 C 23 16, 27 29, 40 29 L 240 29 C 253 29, 257 16, 265 16 C 268 16, 272 16, 272 22 L 272 120 C 272 150, 255 152, 240 152 L 40 152 C 25 152, 8 152, 8 120 Z"
                stroke="#3d5635"
                strokeWidth="1.5"
                strokeDasharray="6 4"
              />
            </svg>

            <div className="pocket-content">
              <div style={{ position: 'relative', height: 24, width: '100%' }}>
                <div className="balance-stars">******</div>
                <div className="balance-real">{balance}</div>
              </div>
              <div style={{ color: '#88a682', fontSize: 12, fontWeight: 600 }}>
                Available Balance
              </div>
              <div className="eye-icon-wrapper">
                <svg
                  className="eye-icon eye-slash"
                  width={20}
                  height={20}
                  viewBox="0 0 24 24"
                  fill="none"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx={12} cy={12} r={3} />
                  <line x1={3} y1={3} x2={21} y2={21} />
                </svg>
                <svg
                  className="eye-icon eye-open"
                  style={{ opacity: 0 }}
                  width={20}
                  height={20}
                  viewBox="0 0 24 24"
                  fill="none"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx={12} cy={12} r={3} />
                </svg>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Selected Card Confirmation Card */}
      <div className="selected-card-confirmation">
        <div className="confirmation-left">
          <CheckCircle2 size={16} color="#10b981" />
          <span>
            Selected Card:{' '}
            <strong>
              {currentActive === 'stripe'
                ? 'Stripe · Alex Smith (**** 4242)'
                : currentActive === 'wise'
                ? 'Wise · Studio LLC (**** 8810)'
                : 'PayPal · hello@work.com (**** 0094)'}
            </strong>
          </span>
        </div>
        <span className="card-switch-hint">Click any card to switch</span>
      </div>
    </div>
  );
}

export default MultiCardWallet;
