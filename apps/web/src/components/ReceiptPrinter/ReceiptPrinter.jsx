import React, { useState, useEffect } from 'react';
import { CheckCircle2, Loader2, ArrowLeft, Download, ShieldCheck, Printer } from 'lucide-react';
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

/**
 * ReceiptPrinter Component
 * Realistic POS Thermal Receipt Machine with stepped paper feed animation,
 * dark textured chassis, LCD status screen, and itemized solar bill paper.
 */
export function ReceiptPrinter({
  stage = 'printing', // 'processing' | 'printing' | 'complete'
  billDetails = {
    billId: 'INV-SURYA-2026-9912',
    orderId: 'order_PMSG_2026_9912',
    utrNumber: 'RZP91823902381',
    customerName: 'Arun Kumar',
    accountNumber: '•••• 4921',
    amount: '₹78,000.00',
    date: '31 Oct 2026',
    items: [
      { name: '5 kW Bifacial Mono PERC Modules', qty: '10x', cost: '₹1,80,000' },
      { name: '5 kVA Solar Hybrid Inverter', qty: '1x', cost: '₹82,000' },
      { name: 'Rooftop Mounting Structure & BOS', qty: '1 set', cost: '₹40,000' },
      { name: 'Central Subsidy (PM Surya Ghar)', qty: 'Credit', cost: '-₹78,000' },
    ],
  },
  onClose,
  onDownload,
}) {
  const [currentStage, setCurrentStage] = useState(stage);

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
  const isReceiptVisible = currentStage !== 'processing';

  return (
    <div className="receipt-printer-modal-overlay">
      <div className="receipt-printer-root" data-stage={currentStage}>
        {/* ================================================================
            PRINTER MACHINE CHASSIS
            ================================================================ */}
        <div className="receipt-machine">
          {/* Header Bar */}
          <div className="receipt-header">
            <div className="receipt-brand">
              <Printer size={16} color="#38bdf8" />
              <span>SolarOps ESCROW PRINTER-80X</span>
            </div>
            <div className="receipt-power-dot" />
          </div>

          {/* Machine LCD Screen */}
          <div className="receipt-screen">
            <div className="receipt-screen-content">
              <div className="receipt-screen-top">
                <span className="receipt-screen-label">Order Subsidy Invoice</span>
                <strong className="receipt-screen-amount">{billDetails.amount}</strong>
              </div>

              {/* Status Indicator */}
              <div className="receipt-status-line">
                {isComplete ? (
                  <span className="receipt-status-icon complete">
                    <CheckCircle2 size={16} color="#10b981" />
                  </span>
                ) : (
                  <span className="receipt-status-icon working">
                    <Loader2 size={16} color="#38bdf8" className="spin-icon" />
                  </span>
                )}
                <span className="receipt-status-text">
                  {currentStage === 'processing'
                    ? 'Connecting gateway & generating bill...'
                    : currentStage === 'printing'
                    ? 'Printing verified tax invoice...'
                    : 'Invoice generated & order complete'}
                </span>
              </div>
            </div>
          </div>

          {/* Machine Paper Output Ejector Slot */}
          <div className="receipt-slot-slit" />
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
                  <strong className="meta-val">{billDetails.billId}</strong>
                </div>
                <div>
                  <span className="meta-label">Date:</span>
                  <strong className="meta-val">{billDetails.date}</strong>
                </div>
                <div>
                  <span className="meta-label">Customer:</span>
                  <strong className="meta-val">{billDetails.customerName}</strong>
                </div>
                <div>
                  <span className="meta-label">Account:</span>
                  <strong className="meta-val">{billDetails.accountNumber}</strong>
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
                {billDetails.items.map((item, i) => (
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
                  <span>NET ESCROW SETTLED:</span>
                  <span>{billDetails.amount}</span>
                </div>
                <div className="paper-total-sub">
                  <span>DISBURSEMENT: DIRECT BANK TRANSFER (IMPS)</span>
                </div>
                <div className="paper-total-sub">
                  <span>BANK REF (UTR): {billDetails.utrNumber}</span>
                </div>
              </div>

              <div className="paper-dash-line" />

              {/* Barcode & Footer */}
              <div className="paper-footer">
                <div className="paper-barcode-svg">
                  {/* Barcode pattern */}
                  <svg viewBox="0 0 180 32" width="160" height="28">
                    <path
                      d="M2 0v32M6 0v32M9 0v32M14 0v32M17 0v32M22 0v32M28 0v32M32 0v32M37 0v32M42 0v32M45 0v32M50 0v32M55 0v32M61 0v32M65 0v32M70 0v32M74 0v32M80 0v32M84 0v32M88 0v32M94 0v32M99 0v32M104 0v32M108 0v32M114 0v32M118 0v32M124 0v32M129 0v32M134 0v32M140 0v32M145 0v32M149 0v32M155 0v32M160 0v32M165 0v32M170 0v32M175 0v32"
                      stroke="#0f172a"
                      strokeWidth="2"
                    />
                  </svg>
                </div>
                <p className="paper-barcode-text">*{billDetails.orderId}*</p>
                <p className="paper-thankyou">Thank you for accelerating clean energy.</p>
                <div className="paper-stamp">✓ RAZORPAY VERIFIED</div>
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
              <span>Back to Payment</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default ReceiptPrinter;
