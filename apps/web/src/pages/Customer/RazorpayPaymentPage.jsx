import React, { useState, useEffect } from 'react';
import { useRouter } from '../../router/Router';
import { useAuth } from '../../context/AuthContext';
import {
  Shield,
  Lock,
  ArrowLeft,
  CheckCircle2,
  CreditCard,
  QrCode,
  Building,
  Smartphone,
  ChevronRight,
  ExternalLink,
  Zap,
} from 'lucide-react';
import './RazorpayPaymentPage.css';

export function RazorpayPaymentPage() {
  const { navigate } = useRouter();
  const { showToast, user } = useAuth();

  const [activeTab, setActiveTab] = useState('upi'); // 'upi' | 'card' | 'netbanking'
  const [upiMethod, setUpiMethod] = useState('qr'); // 'qr' | 'id'
  const [upiId, setUpiId] = useState('customer@oksbi');
  const [cardNumber, setCardNumber] = useState('4532 •••• •••• 9821');
  const [cardExpiry, setCardExpiry] = useState('08/29');
  const [cardCvv, setCardCvv] = useState('•••');
  const [selectedBank, setSelectedBank] = useState('sbi');

  const [paymentState, setPaymentState] = useState('idle'); // 'idle' | 'processing' | 'otp' | 'success'
  const [otpInput, setOtpInput] = useState('482910');

  // Amount details
  const amountNumber = 78000;
  const formattedAmount = '₹78,000.00';
  const orderId = 'order_PMSG_2026_9912';

  const handlePay = () => {
    setPaymentState('processing');
    setTimeout(() => {
      setPaymentState('otp');
    }, 900);
  };

  const handleVerifyOtp = () => {
    setPaymentState('processing');
    setTimeout(() => {
      setPaymentState('success');
    }, 1100);
  };

  // On success, wait 2.2 seconds and redirect back with toast
  useEffect(() => {
    if (paymentState === 'success') {
      const timer = setTimeout(() => {
        showToast({
          type: 'success',
          title: 'Razorpay Payment Settled',
          message: `${formattedAmount} successfully credited via Razorpay Route.`,
        });
        navigate('/customer/payments');
      }, 2400);
      return () => clearTimeout(timer);
    }
  }, [paymentState, navigate, showToast]);

  return (
    <div className="rzp-checkout-page">
      {/* Top Razorpay Header Bar */}
      <header className="rzp-top-header">
        <div className="rzp-top-container">
          <div className="rzp-brand-group">
            <button
              type="button"
              className="rzp-back-btn"
              onClick={() => navigate('/customer/payments')}
              title="Return to SolarOps"
            >
              <ArrowLeft size={18} />
              <span>Cancel & Return</span>
            </button>
            <div className="rzp-logo-lockup">
              {/* Razorpay Classic Slanted Emblem */}
              <svg
                className="rzp-main-logo"
                viewBox="0 0 120 30"
                height="24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M14.8 2L5 18.2H12.4L9.5 28L23.5 12H16L19.2 2H14.8Z"
                  fill="#0284c7"
                />
                <text
                  x="28"
                  y="20"
                  fill="#0c2340"
                  fontSize="18"
                  fontWeight="800"
                  fontFamily="system-ui, -apple-system, sans-serif"
                  letterSpacing="-0.5px"
                >
                  Razorpay
                </text>
              </svg>
            </div>
          </div>

          <div className="rzp-security-badge">
            <Lock size={14} color="#10b981" />
            <span>256-bit SSL Secure Checkout</span>
          </div>
        </div>
      </header>

      {/* Main Checkout Viewport Container */}
      <main className="rzp-checkout-main">
        <div className="rzp-checkout-card">
          {/* ================================================================
              LEFT MERCHANT SUMMARY PANEL
              ================================================================ */}
          <aside className="rzp-summary-panel">
            <div className="rzp-merchant-info">
              <div className="rzp-merchant-avatar">
                <Zap size={22} color="#ffffff" />
              </div>
              <div className="rzp-merchant-text">
                <h3 className="rzp-merchant-name">SolarOps Energy Pvt Ltd</h3>
                <span className="rzp-merchant-desc">PM Surya Ghar Solar Escrow</span>
              </div>
            </div>

            <div className="rzp-order-details-box">
              <div className="rzp-order-item">
                <span className="rzp-order-label">Order Reference:</span>
                <span className="rzp-order-val mono">{orderId}</span>
              </div>
              <div className="rzp-order-item">
                <span className="rzp-order-label">Beneficiary Account:</span>
                <span className="rzp-order-val">A/C •••• 4921</span>
              </div>
              <div className="rzp-order-item">
                <span className="rzp-order-label">Disbursement Route:</span>
                <span className="rzp-order-val">Direct Subsidy (DBT)</span>
              </div>
            </div>

            <div className="rzp-amount-highlight">
              <span className="rzp-amount-caption">Total Amount to Process</span>
              <div className="rzp-amount-large">{formattedAmount}</div>
              <span className="rzp-amount-badge">Instant Bank Credit</span>
            </div>

            <div className="rzp-trust-badges">
              <div className="rzp-trust-item">
                <CheckCircle2 size={14} color="#10b981" />
                <span>PCI-DSS Level 1 Compliant</span>
              </div>
              <div className="rzp-trust-item">
                <CheckCircle2 size={14} color="#10b981" />
                <span>NPCI UPI Certified</span>
              </div>
            </div>
          </aside>

          {/* ================================================================
              RIGHT PAYMENT INTERACTION AREA
              ================================================================ */}
          <section className="rzp-interaction-panel">
            {paymentState === 'idle' && (
              <>
                {/* Method Navigation Tabs */}
                <div className="rzp-method-nav">
                  <button
                    type="button"
                    className={`rzp-nav-btn ${activeTab === 'upi' ? 'active' : ''}`}
                    onClick={() => setActiveTab('upi')}
                  >
                    <Smartphone size={16} />
                    <span>UPI & QR</span>
                  </button>
                  <button
                    type="button"
                    className={`rzp-nav-btn ${activeTab === 'card' ? 'active' : ''}`}
                    onClick={() => setActiveTab('card')}
                  >
                    <CreditCard size={16} />
                    <span>Cards</span>
                  </button>
                  <button
                    type="button"
                    className={`rzp-nav-btn ${activeTab === 'netbanking' ? 'active' : ''}`}
                    onClick={() => setActiveTab('netbanking')}
                  >
                    <Building size={16} />
                    <span>Net Banking</span>
                  </button>
                </div>

                {/* Tab 1: UPI & QR */}
                {activeTab === 'upi' && (
                  <div className="rzp-tab-content">
                    <div className="rzp-upi-toggle">
                      <button
                        type="button"
                        className={`rzp-sub-toggle ${upiMethod === 'qr' ? 'active' : ''}`}
                        onClick={() => setUpiMethod('qr')}
                      >
                        <QrCode size={15} />
                        <span>Scan QR Code</span>
                      </button>
                      <button
                        type="button"
                        className={`rzp-sub-toggle ${upiMethod === 'id' ? 'active' : ''}`}
                        onClick={() => setUpiMethod('id')}
                      >
                        <Smartphone size={15} />
                        <span>Enter UPI ID</span>
                      </button>
                    </div>

                    {upiMethod === 'qr' ? (
                      <div className="rzp-qr-wrapper">
                        <div className="rzp-qr-frame">
                          {/* Live Dynamic QR SVG */}
                          <svg
                            viewBox="0 0 160 160"
                            width="140"
                            height="140"
                            className="rzp-qr-svg"
                          >
                            <rect width="160" height="160" fill="#ffffff" />
                            {/* Standard QR Code visual blocks */}
                            <path
                              d="M10 10h40v40h-40z M20 20v20h20v-20z M25 25h10v10h-10z M110 10h40v40h-40z M120 20v20h20v-20z M125 25h10v10h-10z M10 110h40v40h-40z M20 120v20h20v-20z M25 125h10v10h-10z"
                              fill="#0c2340"
                            />
                            <path
                              d="M60 15h10v10h-10z M80 15h15v10h-15z M60 35h20v10h-20z M90 35h10v10h-10z M15 65h15v10h-15z M40 65h10v15h-10z M65 60h30v15h-30z M110 65h20v10h-20z M140 65h10v20h-10z M15 90h20v10h-20z M45 90h15v20h-15z M70 85h15v15h-15z M95 85h25v10h-25z M130 90h20v15h-20z M60 115h20v10h-20z M90 115h15v25h-15z M115 115h10v10h-10z M135 115h15v20h-15z M65 135h15v15h-15z M110 135h20v15h-20z"
                              fill="#0c2340"
                            />
                            {/* Center brand badge inside QR */}
                            <circle cx="80" cy="80" r="14" fill="#0284c7" />
                            <text
                              x="80"
                              y="85"
                              fill="#ffffff"
                              fontSize="12"
                              fontWeight="bold"
                              textAnchor="middle"
                            >
                              ₹
                            </text>
                          </svg>
                        </div>
                        <p className="rzp-qr-hint">
                          Scan with any UPI app: <strong>GPay, PhonePe, Paytm, BHIM</strong>
                        </p>
                      </div>
                    ) : (
                      <div className="rzp-input-group">
                        <label className="rzp-input-label">Virtual Payment Address (UPI ID)</label>
                        <input
                          type="text"
                          className="rzp-input-field"
                          value={upiId}
                          onChange={(e) => setUpiId(e.target.value)}
                          placeholder="mobilenumber@upi"
                        />
                        <span className="rzp-input-hint">
                          A payment request will be sent to your UPI app.
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Tab 2: Credit / Debit Cards */}
                {activeTab === 'card' && (
                  <div className="rzp-tab-content">
                    <div className="rzp-input-group">
                      <label className="rzp-input-label">Card Number</label>
                      <input
                        type="text"
                        className="rzp-input-field"
                        value={cardNumber}
                        onChange={(e) => setCardNumber(e.target.value)}
                        placeholder="•••• •••• •••• ••••"
                      />
                    </div>
                    <div className="rzp-two-col">
                      <div className="rzp-input-group">
                        <label className="rzp-input-label">Expiry (MM/YY)</label>
                        <input
                          type="text"
                          className="rzp-input-field"
                          value={cardExpiry}
                          onChange={(e) => setCardExpiry(e.target.value)}
                        />
                      </div>
                      <div className="rzp-input-group">
                        <label className="rzp-input-label">CVV</label>
                        <input
                          type="password"
                          className="rzp-input-field"
                          value={cardCvv}
                          onChange={(e) => setCardCvv(e.target.value)}
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Tab 3: Net Banking */}
                {activeTab === 'netbanking' && (
                  <div className="rzp-tab-content">
                    <label className="rzp-input-label">Select Your Bank</label>
                    <div className="rzp-bank-grid">
                      {[
                        { id: 'sbi', name: 'State Bank of India', code: 'SBI' },
                        { id: 'hdfc', name: 'HDFC Bank', code: 'HDFC' },
                        { id: 'icici', name: 'ICICI Bank', code: 'ICICI' },
                        { id: 'axis', name: 'Axis Bank', code: 'AXIS' },
                        { id: 'kotak', name: 'Kotak Mahindra', code: 'KOTAK' },
                        { id: 'bob', name: 'Bank of Baroda', code: 'BOB' },
                      ].map((bank) => (
                        <button
                          key={bank.id}
                          type="button"
                          className={`rzp-bank-card ${selectedBank === bank.id ? 'selected' : ''}`}
                          onClick={() => setSelectedBank(bank.id)}
                        >
                          <span className="rzp-bank-code">{bank.code}</span>
                          <span className="rzp-bank-name">{bank.name}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Submit Action Button */}
                <button type="button" className="rzp-submit-btn" onClick={handlePay}>
                  <span>Authorize & Process {formattedAmount}</span>
                  <ChevronRight size={18} />
                </button>
              </>
            )}

            {/* State: Processing Spinner */}
            {paymentState === 'processing' && (
              <div className="rzp-state-screen">
                <div className="rzp-spinner-ring" />
                <h4 className="rzp-state-title">Contacting Bank Gateway...</h4>
                <p className="rzp-state-desc">
                  Please do not refresh or close this window. Securely communicating with{' '}
                  <strong>Razorpay Route (AES-256)</strong>.
                </p>
              </div>
            )}

            {/* State: 3D Secure OTP Verification */}
            {paymentState === 'otp' && (
              <div className="rzp-state-screen">
                <div className="rzp-otp-badge">
                  <Shield size={20} color="#0284c7" />
                  <span>Bank 3D-Secure Authorization</span>
                </div>
                <h4 className="rzp-state-title">Enter Bank Authentication OTP</h4>
                <p className="rzp-state-desc">
                  A one-time passcode has been dispatched to beneficiary phone{' '}
                  <strong>+91 ••••• •4921</strong> for transaction verification.
                </p>

                <div className="rzp-otp-input-box">
                  <input
                    type="text"
                    className="rzp-otp-field"
                    value={otpInput}
                    onChange={(e) => setOtpInput(e.target.value)}
                    maxLength={6}
                  />
                  <button type="button" className="rzp-submit-btn" onClick={handleVerifyOtp}>
                    Verify OTP & Complete Settlement
                  </button>
                </div>
              </div>
            )}

            {/* State: Payment Success Celebration */}
            {paymentState === 'success' && (
              <div className="rzp-state-screen success">
                <div className="rzp-success-circle">
                  <CheckCircle2 size={48} color="#10b981" />
                </div>
                <h3 className="rzp-success-title">Payment Settlement Successful!</h3>
                <div className="rzp-success-amount">{formattedAmount}</div>
                <p className="rzp-success-sub">
                  Payment Reference: <strong className="mono">pay_PMSG_9912847291</strong>
                  <br />
                  Direct subsidy credited to Aadhaar-linked Bank A/C •••• 4921.
                </p>
                <div className="rzp-redirect-bar">
                  <div className="rzp-progress-fill" />
                  <span>Auto-returning to SolarOps Escrow Schedule...</span>
                </div>
              </div>
            )}
          </section>
        </div>
      </main>

      {/* Razorpay Footer */}
      <footer className="rzp-bottom-footer">
        <div className="rzp-footer-content">
          <span>Powered by Razorpay Payments India</span>
          <span>•</span>
          <span>Terms & Privacy Policy</span>
          <span>•</span>
          <span>Merchant ID: MID_SOLAROPS_BLR</span>
        </div>
      </footer>
    </div>
  );
}

export default RazorpayPaymentPage;
