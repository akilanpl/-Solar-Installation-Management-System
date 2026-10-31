import React, { useState, useEffect } from 'react';
import { CheckCircle2, ArrowLeft, Download, Home } from 'lucide-react';
import './ReceiptPrinter.css';

// Calculate sawtooth tear edge points
const receiptToothCount = 36;
const receiptToothDepth = 4;
const receiptToothPoints = Array.from(
  { length: receiptToothCount * 2 },
  (_, index) => {
    const x = 100 - ((index + 1) * 100) / (receiptToothCount * 2);
    const y = index % 2 === 0 ? '100%' : `calc(100% - ${receiptToothDepth}px)`;
    return `${x}% ${y}`;
  }
).join(', ');

export const receiptClipPath = `polygon(0 0, 100% 0, 100% calc(100% - ${receiptToothDepth}px), ${receiptToothPoints})`;

// Helper to retrieve project stats & amounts from the website's persistent local DB
function getLocalDbStats() {
  try {
    const storedEnquiries = typeof window !== 'undefined'
      ? JSON.parse(localStorage.getItem('solarops_enquiries') || '[]')
      : [];
    const storedUser = typeof window !== 'undefined'
      ? JSON.parse(localStorage.getItem('solarops_current_user') || 'null')
      : null;
    const activeEnquiry = storedEnquiries[0] || {};

    const capacityKw = activeEnquiry.preferred_capacity_w
      ? activeEnquiry.preferred_capacity_w / 1000
      : 5;
    const customerName = storedUser?.full_name || activeEnquiry.customer_name || 'Arun Kumar';
    const roofType = activeEnquiry.roof_type || 'Reinforced Concrete (Flat)';
    const roofArea = activeEnquiry.roof_area_sqft || 850;

    return {
      title: `${capacityKw} kW Solar System`,
      subtitle: `Milestone 1 Advance · ${roofArea} sq.ft ${roofType}`,
      amount: '₹78,000.00',
      billId: 'INV-SURYA-2026-9912',
      orderId: 'order_PMSG_2026_9912',
      utrNumber: 'RZP91823902381',
      customerName,
      accountNumber: '•••• 4921',
      date: '31 Oct 2026',
      items: [
        { name: `${capacityKw} kW Bifacial Mono PERC Modules`, qty: '10x', cost: '₹1,80,000' },
        { name: `${capacityKw} kVA Solar Hybrid Inverter`, qty: '1x', cost: '₹82,000' },
        { name: 'Rooftop Mounting Structure & BOS', qty: '1 set', cost: '₹40,000' },
        { name: 'Central Subsidy (PM Surya Ghar)', qty: 'Credit', cost: '-₹78,000' },
      ],
    };
  } catch {
    return {
      title: '5 kW Solar System',
      subtitle: 'Milestone 1 Advance · 850 sq.ft Flat RCC Roof',
      amount: '₹78,000.00',
      billId: 'INV-SURYA-2026-9912',
      orderId: 'order_PMSG_2026_9912',
      utrNumber: 'RZP91823902381',
      customerName: 'Arun Kumar',
      accountNumber: '•••• 4921',
      date: '31 Oct 2026',
      items: [
        { name: '5 kW Bifacial Mono PERC Modules', qty: '10x', cost: '₹1,80,000' },
        { name: '5 kVA Solar Hybrid Inverter', qty: '1x', cost: '₹82,000' },
        { name: 'Rooftop Mounting Structure & BOS', qty: '1 set', cost: '₹40,000' },
        { name: 'Central Subsidy (PM Surya Ghar)', qty: 'Credit', cost: '-₹78,000' },
      ],
    };
  }
}

/**
 * ReceiptPrinter Component
 * Displays the project stats and settlement amount directly from the website local DB:
 * - Matte dark charcoal chassis (#202020) with Star sparkle badge & Home button
 * - Inset LCD screen displaying system stats & ₹78,000.00 amount from local DB
 * - Stepped paper feed animation with itemized solar bill and sawtooth tear edge
 */
export function ReceiptPrinter({
  stage = 'printing', // 'processing' | 'printing' | 'complete'
  title,
  subtitle,
  amount,
  billDetails,
  onClose,
  onDownload,
}) {
  const [currentStage, setCurrentStage] = useState(stage);
  const localDb = getLocalDbStats();

  useEffect(() => {
    if (stage === 'processing') {
      setCurrentStage('processing');
      const printTimer = setTimeout(() => {
        setCurrentStage('printing');
      }, 1000);
      const completeTimer = setTimeout(() => {
        setCurrentStage('complete');
      }, 3000);
      return () => {
        clearTimeout(printTimer);
        clearTimeout(completeTimer);
      };
    } else {
      setCurrentStage(stage);
    }
  }, [stage]);

  const isPrinting = currentStage === 'printing';
  const isComplete = currentStage === 'complete';

  // Extract display values (defaults to website local DB stats & amount)
  const displayTitle = billDetails?.title || title || localDb.title;
  const displaySubtitle = billDetails?.subtitle || subtitle || localDb.subtitle;
  const displayAmount = billDetails?.amount || amount || localDb.amount;
  const activeBill = { ...localDb, ...(billDetails || {}) };

  return (
    <div className="receipt-printer-modal-overlay">
      <div className="receipt-printer-root" data-stage={currentStage}>
        {/* ================================================================
            PRINTER MACHINE CHASSIS (Exact match to reference design)
            ================================================================ */}
        <div className="receipt-machine">
          {/* Top Bar: Sparkle badge on left, Home pill button on right */}
          <div className="receipt-top-bar">
            <div className="receipt-sparkle-badge" aria-label="Brand Emblem">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M12 2C12 7.5 7.5 12 2 12C7.5 12 12 16.5 12 22C12 16.5 16.5 12 22 12C16.5 12 12 7.5 12 2Z" />
              </svg>
            </div>
            <button
              type="button"
              className="receipt-home-btn"
              onClick={onClose}
              title="Return to Home"
            >
              <Home size={14} className="receipt-home-icon" />
              <span>Home</span>
            </button>
          </div>

          {/* Inner Inset LCD Screen */}
          <div className="receipt-lcd-screen">
            <div className="receipt-lcd-top-row">
              <div className="receipt-lcd-left">
                <h3 className="receipt-plan-title">{displayTitle}</h3>
                <p className="receipt-plan-sub">{displaySubtitle}</p>
              </div>
              <div className="receipt-lcd-right">
                <span className="receipt-total-label">Total</span>
                <span className="receipt-total-value">{displayAmount}</span>
              </div>
            </div>

            {/* Bottom Status Row: Circular Notch Spinner & Status Text */}
            <div className="receipt-lcd-status-row">
              {isComplete ? (
                <CheckCircle2 size={15} color="#10b981" className="receipt-status-check" />
              ) : (
                <span className="receipt-notch-spinner" />
              )}
              <span className="receipt-status-text">
                {currentStage === 'processing'
                  ? 'Processing your payment...'
                  : currentStage === 'printing'
                  ? 'Printing your receipt'
                  : 'Receipt printed'}
              </span>
            </div>
          </div>

          {/* Machine Paper Output Slot Slit */}
          <div className="receipt-slit-slot" />
        </div>

        {/* ================================================================
            PAPER OUTPUT & STEPPED FEED ANIMATION
            ================================================================ */}
        <div className="receipt-output-viewport">
          <div
            className={`receipt-paper-wrapper ${
              isPrinting ? 'anim-stepped-feed' : isComplete ? 'feed-complete' : 'feed-hidden'
            }`}
          >
            <article
              className="receipt-paper"
              style={{ clipPath: receiptClipPath }}
              role="document"
              aria-label="Solar Bill Receipt"
            >
              {/* Subtle perforated guide line right below printer slot */}
              <div className="paper-perforation-line" />

              {/* Receipt Header */}
              <div className="paper-header">
                <div className="paper-brand-emblem">☀ SolarOps</div>
                <p className="paper-subhead">PM Surya Ghar National Portal Escrow</p>
                <p className="paper-tax-id">GSTIN: 29AAACS0921M1Z8 · TAX INVOICE</p>
                <div className="paper-dash-line" />
              </div>

              {/* Bill Metadata */}
              <div className="paper-meta-grid">
                <div>
                  <span className="meta-label">Invoice:</span>
                  <strong className="meta-val">{activeBill.billId}</strong>
                </div>
                <div>
                  <span className="meta-label">Date:</span>
                  <strong className="meta-val">{activeBill.date}</strong>
                </div>
                <div>
                  <span className="meta-label">Customer:</span>
                  <strong className="meta-val">{activeBill.customerName}</strong>
                </div>
                <div>
                  <span className="meta-label">Account:</span>
                  <strong className="meta-val">{activeBill.accountNumber}</strong>
                </div>
              </div>

              <div className="paper-dash-line" />

              {/* Line Items */}
              <div className="paper-items-table">
                <div className="paper-item-row header">
                  <span>ITEM</span>
                  <span style={{ textAlign: 'center' }}>QTY</span>
                  <span style={{ textAlign: 'right' }}>AMOUNT</span>
                </div>
                {activeBill.items.map((item, i) => (
                  <div key={i} className="paper-item-row">
                    <span className="item-name">{item.name}</span>
                    <span className="item-qty">{item.qty}</span>
                    <span className="item-cost">{item.cost}</span>
                  </div>
                ))}
              </div>

              <div className="paper-dash-line" />

              {/* Totals */}
              <div className="paper-totals-box">
                <div className="paper-total-row net">
                  <span>NET TOTAL:</span>
                  <span>{displayAmount}</span>
                </div>
                <div className="paper-total-sub">
                  <span>PAYMENT METHOD: INSTANT SETTLEMENT</span>
                </div>
                <div className="paper-total-sub">
                  <span>BANK REF (UTR): {activeBill.utrNumber}</span>
                </div>
              </div>

              <div className="paper-dash-line" />

              {/* Barcode & Footer */}
              <div className="paper-footer">
                <div className="paper-barcode-svg">
                  <svg viewBox="0 0 180 32" width="160" height="28">
                    <path
                      d="M2 0v32M6 0v32M9 0v32M14 0v32M17 0v32M22 0v32M28 0v32M32 0v32M37 0v32M42 0v32M45 0v32M50 0v32M55 0v32M61 0v32M65 0v32M70 0v32M74 0v32M80 0v32M84 0v32M88 0v32M94 0v32M99 0v32M104 0v32M108 0v32M114 0v32M118 0v32M124 0v32M129 0v32M134 0v32M140 0v32M145 0v32M149 0v32M155 0v32M160 0v32M165 0v32M170 0v32M175 0v32"
                      stroke="#0f172a"
                      strokeWidth="2"
                    />
                  </svg>
                </div>
                <p className="paper-barcode-text">*{activeBill.orderId}*</p>
                <p className="paper-thankyou">Thank you for accelerating clean energy.</p>
                <div className="paper-stamp">✓ VERIFIED & SETTLED</div>
              </div>
            </article>
          </div>
        </div>

        {/* Action Controls when printing completes */}
        {isComplete && (
          <div className="receipt-actions-bar">
            <button
              type="button"
              className="receipt-action-btn primary"
              onClick={onDownload || (() => window.print())}
            >
              <Download size={15} />
              <span>Print / Save Bill</span>
            </button>
            <button
              type="button"
              className="receipt-action-btn secondary"
              onClick={onClose}
            >
              <ArrowLeft size={15} />
              <span>Done</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default ReceiptPrinter;
