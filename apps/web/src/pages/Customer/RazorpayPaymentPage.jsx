import React, { useState } from 'react';
import { useRouter } from '../../router/Router';
import { useAuth } from '../../context/AuthContext';
import { ChevronRight } from 'lucide-react';
import ReceiptPrinter from '../../components/ReceiptPrinter/ReceiptPrinter';
import './RazorpayPaymentPage.css';

export function RazorpayPaymentPage() {
  const { navigate, query } = useRouter();
  const { showToast } = useAuth();

  // Selected payment method pill: 'card' (default as per design) | 'paypal'
  const [selectedMethod, setSelectedMethod] = useState('card');

  // Interactive Card Form inputs (matching the underline fields on the blue card)
  const [fullName, setFullName] = useState('Arun Kumar');
  const [cardNumber, setCardNumber] = useState('4532 8920 1928 4921');
  const [expireDate, setExpireDate] = useState('08/29');
  const [cvc, setCvc] = useState('892');

  // Receipt Printer Animation Modal state
  const [showPrinter, setShowPrinter] = useState(false);
  const [printerStage, setPrinterStage] = useState('processing');

  // Load customer profile and project stats dynamically from website local DB
  const [localDbStats] = useState(() => {
    try {
      // Check if store pending payment exists
      const pendingStore = JSON.parse(localStorage.getItem('solarops_pending_payment') || 'null');
      if (pendingStore && (query?.source === 'store' || pendingStore.source === 'store')) {
        return {
          customerName: pendingStore.customerName || 'Arun Kumar',
          systemTitle: `Solar Hardware Order #${pendingStore.orderId}`,
          systemSubtitle: `${pendingStore.items.length} Products · Delivery: ${pendingStore.address}`,
          amount: `₹${pendingStore.grandTotal.toLocaleString('en-IN')}.00`,
          refId: pendingStore.orderId,
          isStoreOrder: true,
          items: pendingStore.items.map((it) => ({
            name: it.name,
            qty: `x${it.quantity}`,
            cost: `₹${(it.price * it.quantity).toLocaleString('en-IN')}`,
          })),
        };
      }

      const storedEnquiries = JSON.parse(localStorage.getItem('solarops_enquiries') || '[]');
      const storedUser = JSON.parse(localStorage.getItem('solarops_current_user') || 'null');
      const activeEnquiry = storedEnquiries[0] || {};

      const capacityKw = activeEnquiry.preferred_capacity_w
        ? activeEnquiry.preferred_capacity_w / 1000
        : 5;
      const customerName = storedUser?.full_name || activeEnquiry.customer_name || 'Arun Kumar';
      const roofType = activeEnquiry.roof_type || 'Flat RCC Roof';
      const roofArea = activeEnquiry.roof_area_sqft || 850;
      const refId = activeEnquiry.reference || 'ENQ-2026-001';

      return {
        customerName,
        systemTitle: `${capacityKw} kW Solar System`,
        systemSubtitle: `Milestone 1 Advance · ${roofArea} sq.ft ${roofType}`,
        amount: '₹78,000.00',
        refId,
        isStoreOrder: false,
        items: [
          { name: `${capacityKw} kW Bifacial Mono PERC Modules`, qty: '10x', cost: '₹1,80,000' },
          { name: `${capacityKw} kVA Solar Hybrid Inverter`, qty: '1x', cost: '₹82,000' },
          { name: 'Rooftop Mounting Structure & BOS', qty: '1 set', cost: '₹40,000' },
          { name: 'Central Subsidy (PM Surya Ghar)', qty: 'Credit', cost: '-₹78,000' },
        ],
      };
    } catch {
      return {
        customerName: 'Arun Kumar',
        systemTitle: '5 kW Solar System',
        systemSubtitle: 'Milestone 1 Advance · 850 sq.ft Flat RCC Roof',
        amount: '₹78,000.00',
        refId: 'ENQ-2026-001',
        isStoreOrder: false,
        items: [
          { name: '5 kW Bifacial Mono PERC Modules', qty: '10x', cost: '₹1,80,000' },
          { name: '5 kVA Solar Hybrid Inverter', qty: '1x', cost: '₹82,000' },
          { name: 'Rooftop Mounting Structure & BOS', qty: '1 set', cost: '₹40,000' },
          { name: 'Central Subsidy (PM Surya Ghar)', qty: 'Credit', cost: '-₹78,000' },
        ],
      };
    }
  });

  // Bill metadata tied directly to website local DB
  const billInfo = {
    title: localDbStats.systemTitle,
    subtitle: localDbStats.systemSubtitle,
    amount: localDbStats.amount,
    billId: localDbStats.isStoreOrder ? `INV-${localDbStats.refId}` : 'INV-SURYA-2026-9912',
    orderId: localDbStats.isStoreOrder ? `order_${localDbStats.refId}` : 'order_PMSG_2026_9912',
    utrNumber: 'RZP91823902381',
    customerName: fullName || localDbStats.customerName,
    accountNumber: `•••• ${cardNumber ? cardNumber.replace(/\s+/g, '').slice(-4) : '4921'}`,
    date: '31 Oct 2026',
    items: localDbStats.items,
  };

  const handleProceedPayment = (e) => {
    e.preventDefault();
    setShowPrinter(true);
    setPrinterStage('processing');

    // Smooth sequence: processing -> printing -> complete
    setTimeout(() => {
      setPrinterStage('printing');
    }, 1200);

    setTimeout(() => {
      setPrinterStage('complete');

      // If store order, mark as paid in solarops_orders
      try {
        const pending = JSON.parse(localStorage.getItem('solarops_pending_payment') || 'null');
        if (pending) {
          const orders = JSON.parse(localStorage.getItem('solarops_orders') || '[]');
          const idx = orders.findIndex((o) => o.orderId === pending.orderId);
          if (idx >= 0) {
            orders[idx].status = 'Paid via Razorpay · Staged at Bengaluru Warehouse';
          } else {
            orders.unshift({
              ...pending,
              status: 'Paid via Razorpay · Staged at Bengaluru Warehouse',
            });
          }
          localStorage.setItem('solarops_orders', JSON.stringify(orders));
        }
      } catch (err) {
        // ignore
      }

      showToast({
        type: 'success',
        title: 'Settlement Confirmed',
        message: 'Payment verified via Razorpay Route. Receipt printed.',
      });
    }, 3400);
  };

  const handleClosePrinter = () => {
    setShowPrinter(false);
    if (query?.source === 'store' || localDbStats.isStoreOrder) {
      navigate('/customer/store');
    } else {
      navigate('/customer');
    }
  };

  return (
    <div className="io-payment-viewport">
      {/* ================================================================
          TOP HEADER: BRAND LOGO + RETURN BUTTON
          ================================================================ */}
      <header className="io-top-header">
        <div className="io-brand-mark">
          {/* Isometric Hexagon Brand Glyph matching reference image */}
          <svg
            className="io-hex-logo"
            viewBox="0 0 36 36"
            width="32"
            height="32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M18 2L32 10.08V26.24L18 34.32L4 26.24V10.08L18 2Z"
              stroke="#2f57ef"
              strokeWidth="2.5"
              strokeLinejoin="round"
            />
            <path
              d="M18 10L27 15.2V25.6L18 30.8L9 25.6V15.2L18 10Z"
              stroke="#2f57ef"
              strokeWidth="1.8"
              strokeLinejoin="round"
            />
            <path
              d="M18 10V2L27 15.2L32 10.08M18 30.8V34.32M9 25.6L4 26.24"
              stroke="#2f57ef"
              strokeWidth="1.5"
            />
          </svg>
          <span className="io-brand-title">SolarOps</span>
        </div>

        <button
          type="button"
          className="io-nav-pill-btn"
          onClick={() => {
            if (query?.source === 'store' || localDbStats.isStoreOrder) {
              navigate('/customer/store');
            } else {
              navigate('/customer');
            }
          }}
        >
          {query?.source === 'store' || localDbStats.isStoreOrder ? 'Back to Solar Store' : 'Return to Dashboard'}
        </button>
      </header>

      {/* ================================================================
          MAIN CONTENT CONTAINER
          ================================================================ */}
      <main className="io-main-container">
        {/* Top Horizontal Bill Capsule */}
        <section className="io-bill-capsule" aria-label="Bill Overview">
          <div className="io-bill-left">
            <span className="io-bill-heading">Your bill</span>
          </div>
          <div className="io-bill-items">
            <span className="io-bill-tag title">
              {localDbStats.isStoreOrder ? 'SolarFlow Hardware Store' : 'SolarOps PM Surya Ghar'}
            </span>
            <span className="io-bill-tag tier">
              {localDbStats.isStoreOrder ? 'Cart Checkout' : 'VIP Site Commissioning'}
            </span>
            <span className="io-bill-tag calculation">
              {billInfo.title} = <strong>{billInfo.amount}</strong>
            </span>
          </div>
        </section>

        {/* Section Heading */}
        <div className="io-heading-group">
          <h1 className="io-main-title">Select a payment method</h1>
          <p className="io-main-subtitle">
            Select a payment method you want to use to pay for your rooftop solar milestone.
          </p>
        </div>

        {/* Two-Column Payment Layout */}
        <div className="io-payment-grid">
          {/* ============================================================
              LEFT COLUMN: PAYMENT METHOD PILLS + PROCEED BUTTON
              ============================================================ */}
          <div className="io-methods-column">
            {/* Pill 1: Paypal / UPI */}
            <div
              className={`io-method-pill ${selectedMethod === 'paypal' ? 'active' : ''}`}
              onClick={() => setSelectedMethod('paypal')}
              role="button"
              tabIndex={0}
            >
              <span className="io-pill-label">Paypal</span>
              <div className="io-pill-right">
                <div className="io-paypal-badge">
                  <span className="pp-p1">P</span>
                  <span className="pp-p2">P</span>
                  <span className="pp-text">PayPal</span>
                </div>
                <ChevronRight size={18} className="io-pill-arrow" />
              </div>
            </div>

            {/* Pill 2: Card (ACTIVE WITH TOPOGRAPHICAL WAVE PATTERN) */}
            <div
              className={`io-method-pill card-pill ${selectedMethod === 'card' ? 'active' : ''}`}
              onClick={() => setSelectedMethod('card')}
              role="button"
              tabIndex={0}
            >
              <span className="io-pill-label">Card</span>
              <div className="io-pill-right">
                <div className="io-card-brand-badges">
                  <span className="brand-badge visa">VISA</span>
                  <span className="brand-badge amex">AMEX</span>
                  <div className="brand-badge mc" title="Mastercard">
                    <span className="circle red" />
                    <span className="circle yellow" />
                  </div>
                  <span className="brand-badge discover">DISCOVER</span>
                </div>
                <ChevronRight size={18} className="io-pill-arrow" />
              </div>
            </div>

            {/* Proceed Payment Pill Button */}
            <div className="io-proceed-wrapper">
              <button
                type="button"
                className="io-proceed-btn"
                onClick={handleProceedPayment}
              >
                Proceed payment
              </button>
            </div>
          </div>

          {/* ============================================================
              RIGHT COLUMN: ROYAL BLUE CREDIT CARD WITH UNDERLINE INPUTS
              ============================================================ */}
          <div className="io-card-column">
            <div className="io-credit-card">
              {/* Decorative Subtle Wave Lines */}
              <div className="io-card-wave-bg">
                <svg viewBox="0 0 500 320" preserveAspectRatio="none" className="card-waves-svg">
                  <path
                    d="M-50,160 C120,60 280,260 550,140"
                    fill="none"
                    stroke="rgba(255, 255, 255, 0.16)"
                    strokeWidth="1.6"
                  />
                  <path
                    d="M-50,110 C140,20 290,210 550,90"
                    fill="none"
                    stroke="rgba(255, 255, 255, 0.12)"
                    strokeWidth="1.2"
                  />
                  <path
                    d="M-50,210 C100,100 270,310 550,190"
                    fill="none"
                    stroke="rgba(255, 255, 255, 0.14)"
                    strokeWidth="1.4"
                  />
                </svg>
              </div>

              {/* Card Top Row: Brand Badges */}
              <div className="io-card-top-row">
                <div className="io-card-badges-group">
                  <span className="card-top-badge visa">VISA</span>
                  <span className="card-top-badge amex">AMEX</span>
                  <div className="card-top-badge mc">
                    <span className="circle red" />
                    <span className="circle yellow" />
                  </div>
                  <span className="card-top-badge discover">DISCOVER</span>
                </div>
              </div>

              {/* Interactive Card Surface Fields */}
              <div className="io-card-fields-wrapper">
                {/* Field 1: Your Full Name */}
                <div className="io-card-field-group">
                  <label className="io-card-field-label">Your Full name</label>
                  <input
                    type="text"
                    className="io-card-underline-input"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Arun Kumar"
                    spellCheck="false"
                  />
                </div>

                {/* Field 2: Card Number */}
                <div className="io-card-field-group">
                  <label className="io-card-field-label">Card Number</label>
                  <input
                    type="text"
                    className="io-card-underline-input"
                    value={cardNumber}
                    onChange={(e) => setCardNumber(e.target.value)}
                    placeholder="4532 8920 1928 4921"
                    maxLength={19}
                    spellCheck="false"
                  />
                </div>

                {/* Row with Expire Date, CVC, and EMV Chip */}
                <div className="io-card-bottom-row">
                  <div className="io-card-inputs-subgrid">
                    <div className="io-card-field-group">
                      <label className="io-card-field-label">Expire date</label>
                      <input
                        type="text"
                        className="io-card-underline-input short"
                        value={expireDate}
                        onChange={(e) => setExpireDate(e.target.value)}
                        placeholder="08/29"
                        maxLength={5}
                      />
                    </div>
                    <div className="io-card-field-group">
                      <label className="io-card-field-label">CVC</label>
                      <input
                        type="password"
                        className="io-card-underline-input short"
                        value={cvc}
                        onChange={(e) => setCvc(e.target.value)}
                        placeholder="892"
                        maxLength={4}
                      />
                    </div>
                  </div>

                  {/* EMV Smart Chip */}
                  <div className="io-emv-chip" aria-label="EMV Smart Chip">
                    <div className="chip-inner-trace t1" />
                    <div className="chip-inner-trace t2" />
                    <div className="chip-inner-trace t3" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* ================================================================
          BOTTOM FOOTER: COPYRIGHT / STUDIO CREDIT
          ================================================================ */}
      <footer className="io-bottom-footer">
        <span>SolarOps © all right reserved 2026</span>
      </footer>

      {/* ================================================================
          BILL GENERATION ANIMATION MODAL (RECEIPT PRINTER)
          ================================================================ */}
      {showPrinter && (
        <ReceiptPrinter
          stage={printerStage}
          billDetails={billInfo}
          onClose={handleClosePrinter}
          onDownload={() => window.print()}
        />
      )}
    </div>
  );
}

export default RazorpayPaymentPage;
