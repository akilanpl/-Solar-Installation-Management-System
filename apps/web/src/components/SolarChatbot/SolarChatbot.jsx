import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  Send,
  X,
  AlertTriangle,
  CheckCircle2,
  Wrench,
  Calendar,
  ShoppingBag,
  ExternalLink,
  ShieldCheck,
  RotateCcw,
  Bot,
  User,
  ArrowRight,
  PhoneCall,
} from 'lucide-react';
import { useRouter } from '../../router/Router';
import { useAuth } from '../../context/AuthContext';
import './SolarChatbot.css';

const INITIAL_MESSAGES = [
  {
    id: 'msg-1',
    sender: 'bot',
    text: "Hello Arun! 👋 I'm your SolarFlow AI Assistant. I can diagnose rooftop solar faults, file official warranty service complaints, book technician visits, or help you order panels & accessories. How can I help you today?",
    timestamp: 'Just now',
    chips: [
      { id: 'chip-inverter', label: '🚨 Inverter Red Alarm / E-04', action: 'inverter_fault' },
      { id: 'chip-complaint', label: '📝 File Warranty Complaint', action: 'file_complaint' },
      { id: 'chip-book', label: '📅 Book Rooftop Maintenance', action: 'book_maintenance' },
      { id: 'chip-order', label: '🛒 Order Solar Products', action: 'order_store' },
      { id: 'chip-generation', label: '📉 Low Solar Generation', action: 'low_generation' },
      { id: 'chip-subsidy', label: '💰 PM Surya Ghar Subsidy', action: 'check_subsidy' },
    ],
  },
];

export function SolarChatbot({ isOpen, onClose, onOpenStore }) {
  const { showToast, user } = useAuth();
  const { navigate } = useRouter();
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const addMessage = (message) => {
    setMessages((prev) => [...prev, message]);
  };

  const handleActionClick = (action) => {
    switch (action) {
      case 'inverter_fault':
        handleSend("My inverter is showing a red alarm light with Error Code E-04");
        break;
      case 'file_complaint':
        handleSend("I want to file an official service complaint for my solar system");
        break;
      case 'book_maintenance':
        handleSend("I would like to book a technician rooftop maintenance visit");
        break;
      case 'order_store':
        handleSend("I want to order solar panels, batteries, or accessories");
        break;
      case 'low_generation':
        handleSend("My solar panels are generating less electricity than expected");
        break;
      case 'check_subsidy':
        handleSend("What is the status of my PM Surya Ghar national portal subsidy?");
        break;
      default:
        break;
    }
  };

  const processBotResponse = (userText) => {
    setIsTyping(true);
    const query = userText.toLowerCase();

    setTimeout(() => {
      setIsTyping(false);

      // 1. Inverter Fault / Error Code E-04
      if (query.includes('e-04') || query.includes('red alarm') || query.includes('red light') || query.includes('inverter error')) {
        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "⚠️ **Problem Diagnosed: Inverter Error E-04 (Grid Disconnect / DC Ground Leakage)**\n\nThis indicates an AC grid phase imbalance from BESCOM or insulation breakdown in the DC array wiring. For your safety, the inverter has entered protection mode.",
          cardType: 'diagnostic',
          diagnosticData: {
            code: 'E-04',
            severity: 'Urgent',
            steps: [
              'Keep away from exposed rooftop DC cabling.',
              'Verify that the main 4-pole AC MCB switch in your DB is ON.',
              'Do not disconnect MC4 connectors under live daylight.',
            ],
            ticketRecommended: true,
          },
          chips: [
            { id: 'btn-create-tk', label: '🚨 File Urgent Field Repair Ticket', action: 'auto_file_e04' },
            { id: 'btn-call-desk', label: '📞 Call Emergency (+91 80 4000 7800)', action: 'call_support' },
          ],
          timestamp: 'Just now',
        });
      }
      // 2. Auto-file complaint for E-04
      else if (query.includes('file urgent') || query.includes('auto_file_e04')) {
        const ticketNum = 'TK-' + Math.floor(1000 + Math.random() * 9000);
        // Persist to local storage tickets
        try {
          const existing = JSON.parse(localStorage.getItem('solarops_tickets') || '[]');
          existing.unshift({
            id: ticketNum,
            customerName: user?.name || 'Arun Kumar',
            address: '#42, 4th Cross, Indiranagar, Bengaluru',
            category: 'Technical',
            issue: 'Inverter Red LED Trip E-04 DC Ground Leakage',
            priority: 'Urgent',
            status: 'Assigned to Karthik Raja (Field Technician)',
            createdAt: new Date().toISOString(),
          });
          localStorage.setItem('solarops_tickets', JSON.stringify(existing));
        } catch (e) {
          // ignore storage error
        }

        if (showToast) {
          showToast({
            type: 'success',
            title: 'Service Ticket Registered',
            message: `Ticket #${ticketNum} assigned to Field Engineer Karthik Raja.`,
          });
        }

        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: `✅ **Official Warranty Complaint Filed Successfully!**\n\nYour service request has been logged and prioritized under your 10-Year Inverter Replacement Warranty.`,
          cardType: 'ticket',
          ticketData: {
            ticketId: ticketNum,
            customer: user?.name || 'Arun Kumar',
            issue: 'Inverter Red LED E-04 Ground Leakage',
            priority: 'Urgent (Same-Day Response)',
            assignedTo: 'Karthik Raja · Field Technician',
            eta: 'Today within 2 hours',
          },
          chips: [
            { id: 'btn-open-supp', label: '📋 View in Support Desk', action: 'go_support' },
            { id: 'btn-order-acc', label: '🛒 Browse Solar Accessories', action: 'order_store' },
          ],
          timestamp: 'Just now',
        });
      }
      // 3. File general complaint
      else if (query.includes('file') && query.includes('complaint')) {
        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "I can help you file a complaint immediately with our engineering team. Please select the category of the issue:",
          chips: [
            { id: 'c1', label: 'Inverter Tripping / Noise', action: 'inverter_fault' },
            { id: 'c2', label: 'Physical Solar Panel Issue', action: 'panel_damage' },
            { id: 'c3', label: 'BESCOM Net-Metering Delay', action: 'discom_delay' },
            { id: 'c4', label: 'Billing / Subsidy Dispute', action: 'check_subsidy' },
          ],
          timestamp: 'Just now',
        });
      }
      // 4. Low Generation
      else if (query.includes('low generation') || query.includes('less electricity') || query.includes('generation')) {
        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "📉 **Solar Yield Diagnostic**\n\nBased on your 5 kW Bifacial Mono-PERC system in Bengaluru:\n• Normal dry season output: **22-26 kWh/day**\n• Dust & soiling can degrade output by **15%-25%** after 3 weeks without rain.\n\n**Recommended Solution:** Clean panels early morning using soft microfiber squeegee and plain water.",
          cardType: 'product_recommendation',
          productData: {
            name: 'Solar Rooftop Sprinkler Cleaning Kit',
            price: '₹4,999',
            mrp: '₹6,500',
            discount: '23% OFF',
            desc: '10-Nozzle high pressure automated cleaning kit with WiFi timer.',
          },
          chips: [
            { id: 'btn-buy-clean', label: '🛒 Order Cleaning Kit (₹4,999)', action: 'order_cleaning_kit' },
            { id: 'btn-book-clean', label: '📅 Book Professional Cleaning (₹1,499)', action: 'book_cleaning_service' },
          ],
          timestamp: 'Just now',
        });
      }
      // 5. Order stuffs & Solar Store
      else if (query.includes('order') || query.includes('buy') || query.includes('store') || query.includes('product') || query.includes('battery') || query.includes('panel')) {
        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "🛒 **SolarFlow Hardware Marketplace**\n\nYou can order genuine Tier-1 solar equipment, lithium battery storage, automated cleaning kits, and BOS accessories directly with free delivery across Bengaluru!",
          cardType: 'store_showcase',
          storeProducts: [
            {
              name: 'Waaree 540W Mono PERC Bifacial Panel',
              spec: '21.3% Efficiency · 25-Yr Warranty',
              price: '₹13,500',
            },
            {
              name: 'SolarFlow 5.12 kWh LiFePO4 Battery',
              spec: '6000 Cycles · Built-in Smart BMS',
              price: '₹1,24,000',
            },
            {
              name: 'Rooftop Sprinkler Cleaning Kit',
              spec: '10-Nozzle High Pressure · WiFi Timer',
              price: '₹4,999',
            },
          ],
          chips: [
            { id: 'btn-go-store', label: '🛍️ Open Solar Ecommerce Store', action: 'go_store' },
            { id: 'btn-order-kit', label: '⚡ Quick Order Cleaning Kit', action: 'order_cleaning_kit' },
          ],
          timestamp: 'Just now',
        });
      }
      // 6. Quick order cleaning kit
      else if (query.includes('cleaning kit') || query.includes('order_cleaning_kit')) {
        const orderId = 'ORD-2026-' + Math.floor(1000 + Math.random() * 9000);
        try {
          const orders = JSON.parse(localStorage.getItem('solarops_orders') || '[]');
          orders.unshift({
            orderId,
            item: 'Solar Rooftop Sprinkler Cleaning Kit',
            amount: 4999,
            customer: user?.name || 'Arun Kumar',
            address: '#42, 4th Cross, 100ft Road, Indiranagar, Bengaluru - 560038',
            status: 'Confirmed · Preparing Dispatch',
            date: new Date().toLocaleDateString('en-IN'),
          });
          localStorage.setItem('solarops_orders', JSON.stringify(orders));
        } catch (e) {
          // ignore
        }

        if (showToast) {
          showToast({
            type: 'success',
            title: 'Order Placed!',
            message: `Order #${orderId} confirmed. Dispatched within 24 hours.`,
          });
        }

        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: `🎉 **Order Confirmed: ${orderId}**\n\n• **Item:** Solar Rooftop Sprinkler Cleaning Kit (10-Nozzle WiFi)\n• **Total:** ₹4,999 (Free Bengaluru Delivery)\n• **Delivery Address:** #42, 4th Cross, Indiranagar\n• **Est. Delivery:** Tomorrow by 4:00 PM IST`,
          chips: [
            { id: 'btn-view-store', label: '🛍️ Continue Shopping', action: 'go_store' },
            { id: 'btn-help-more', label: '❓ Ask Another Question', action: 'ask_more' },
          ],
          timestamp: 'Just now',
        });
      }
      // 7. Book Maintenance
      else if (query.includes('book') || query.includes('maintenance') || query.includes('visit')) {
        const bookingRef = 'BOOK-2026-' + Math.floor(1000 + Math.random() * 9000);
        if (showToast) {
          showToast({
            type: 'success',
            title: 'Technician Visit Booked',
            message: `Booking #${bookingRef} scheduled for Saturday, 10:00 AM.`,
          });
        }

        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: `📅 **Rooftop Maintenance Scheduled!**\n\n• **Booking Reference:** ${bookingRef}\n• **Slot:** Saturday, 18 May 2026 (10:00 AM - 12:30 PM)\n• **Assigned Engineer:** Karthik Raja\n• **Scope:** Thermal drone scan, MC4 torque check, string Voc verification, and rooftop module washing.`,
          chips: [
            { id: 'btn-more-products', label: '🛒 Browse Replacement Parts', action: 'go_store' },
            { id: 'btn-ask-more', label: '⚡ Inverter Health Check', action: 'inverter_fault' },
          ],
          timestamp: 'Just now',
        });
      }
      // 8. Subsidy Query
      else if (query.includes('subsidy') || query.includes('surya ghar')) {
        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "💰 **PM Surya Ghar: Muft Bijli Yojana Subsidy Status**\n\n• **Eligible Central Subsidy:** ₹78,000 (Maximum ceiling for 3 kW+ residential)\n• **Claim Status:** **Portal Approved** (Reference: `SUB-KA-2026-0042`)\n• **Disbursement Mode:** Direct Benefit Transfer (DBT) directly into your linked Canara Bank A/c within 30 days of net-meter sync.",
          chips: [
            { id: 'btn-order-more', label: '🛒 Upgrade with LiFePO4 Storage', action: 'go_store' },
            { id: 'btn-ask-help', label: '❓ Check Inverter Status', action: 'inverter_fault' },
          ],
          timestamp: 'Just now',
        });
      }
      // Fallback
      else {
        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: `Thank you for your message! I'm trained on your solar plant data. I can help resolve error codes, file an official warranty ticket, book on-site technician maintenance, or help you order panels and accessories.`,
          chips: [
            { id: 'f1', label: '🚨 Diagnose Inverter Error', action: 'inverter_fault' },
            { id: 'f2', label: '📝 File Service Complaint', action: 'file_complaint' },
            { id: 'f3', label: '📅 Book Maintenance Visit', action: 'book_maintenance' },
            { id: 'f4', label: '🛒 Shop Solar Store', action: 'order_store' },
          ],
          timestamp: 'Just now',
        });
      }
    }, 650);
  };

  const handleSend = (textToSend = null) => {
    const text = textToSend || inputValue;
    if (!text.trim()) return;

    addMessage({
      id: `user-${Date.now()}`,
      sender: 'user',
      text,
      timestamp: 'Just now',
    });

    if (!textToSend) {
      setInputValue('');
    }

    processBotResponse(text);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChipClick = (chip) => {
    if (chip.action === 'go_store' || chip.action === 'order_store') {
      if (onOpenStore) {
        onOpenStore();
      } else {
        navigate('/customer/store');
      }
      return;
    }
    if (chip.action === 'go_support') {
      navigate('/customer/support');
      return;
    }
    if (chip.action === 'call_support') {
      window.open('tel:+918040007800');
      return;
    }
    handleActionClick(chip.action);
  };

  const handleReset = () => {
    setMessages(INITIAL_MESSAGES);
    if (showToast) {
      showToast({
        type: 'info',
        title: 'Chat Reset',
        message: 'Assistant history cleared.',
      });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="dock-chat-panel" aria-label="SolarFlow AI Assistant">
      {/* Chat Header */}
      <div className="dock-chat-header">
        <div className="chat-header-identity">
          <div className="bot-avatar-badge">
            <Sparkles size={17} color="#ffffff" />
          </div>
          <div>
            <div className="bot-name-row">
              <h4 className="bot-title">SolarFlow AI Copilot</h4>
              <span className="live-pill">Active</span>
            </div>
            <span className="bot-subtext">Diagnose faults, file complaints & order</span>
          </div>
        </div>

        <div className="chat-header-actions">
          <button
            type="button"
            className="chat-icon-btn"
            title="Reset Chat"
            onClick={handleReset}
          >
            <RotateCcw size={14} />
          </button>
          <button
            type="button"
            className="chat-icon-btn close"
            title="Close Assistant"
            onClick={onClose}
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Quick Status Notice */}
      <div className="chat-system-status-bar">
        <ShieldCheck size={13} color="#10b981" />
        <span>Connected to 5 kW Hybrid Inverter & Local DB</span>
      </div>

      {/* Messages Thread */}
      <div className="dock-chat-messages">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`chat-bubble-row ${msg.sender === 'user' ? 'user-side' : 'bot-side'}`}
          >
            {msg.sender === 'bot' && (
              <div className="bot-msg-avatar">
                <Bot size={14} color="#4f46e5" />
              </div>
            )}

            <div className="chat-bubble-container">
              <div className={`chat-bubble ${msg.sender === 'user' ? 'user-bubble' : 'bot-bubble'}`}>
                <div className="msg-text-content" style={{ whiteSpace: 'pre-line' }}>
                  {msg.text}
                </div>

                {/* Diagnostic Card */}
                {msg.cardType === 'diagnostic' && msg.diagnosticData && (
                  <div className="chat-diagnostic-card">
                    <div className="diag-header">
                      <AlertTriangle size={14} color="#ef4444" />
                      <span className="diag-title">Priority Diagnostic: {msg.diagnosticData.code}</span>
                      <span className="diag-badge">{msg.diagnosticData.severity}</span>
                    </div>
                    <ul className="diag-list">
                      {msg.diagnosticData.steps.map((st, i) => (
                        <li key={i}>{st}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Ticket Created Card */}
                {msg.cardType === 'ticket' && msg.ticketData && (
                  <div className="chat-ticket-card">
                    <div className="ticket-card-header">
                      <span className="ticket-num">{msg.ticketData.ticketId}</span>
                      <span className="ticket-status-pill">Dispatched</span>
                    </div>
                    <div className="ticket-card-body">
                      <div><strong>Issue:</strong> {msg.ticketData.issue}</div>
                      <div><strong>Technician:</strong> {msg.ticketData.assignedTo}</div>
                      <div><strong>ETA:</strong> {msg.ticketData.eta}</div>
                    </div>
                  </div>
                )}

                {/* Product Recommendation Card */}
                {msg.cardType === 'product_recommendation' && msg.productData && (
                  <div className="chat-product-card">
                    <div className="product-card-top">
                      <span className="prod-name">{msg.productData.name}</span>
                      <span className="prod-discount">{msg.productData.discount}</span>
                    </div>
                    <p className="prod-desc">{msg.productData.desc}</p>
                    <div className="prod-price-row">
                      <span className="prod-price">{msg.productData.price}</span>
                      <span className="prod-mrp">{msg.productData.mrp}</span>
                    </div>
                  </div>
                )}

                {/* Store Showcase */}
                {msg.cardType === 'store_showcase' && msg.storeProducts && (
                  <div className="chat-store-showcase">
                    {msg.storeProducts.map((p, idx) => (
                      <div key={idx} className="showcase-item">
                        <div className="showcase-left">
                          <span className="showcase-title">{p.name}</span>
                          <span className="showcase-spec">{p.spec}</span>
                        </div>
                        <span className="showcase-price">{p.price}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Action Chips */}
              {msg.chips && msg.chips.length > 0 && (
                <div className="chat-chips-row">
                  {msg.chips.map((chip) => (
                    <button
                      key={chip.id}
                      type="button"
                      className="chat-action-chip"
                      onClick={() => handleChipClick(chip)}
                    >
                      <span>{chip.label}</span>
                    </button>
                  ))}
                </div>
              )}

              <span className="msg-timestamp">{msg.timestamp}</span>
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="chat-bubble-row bot-side">
            <div className="bot-msg-avatar">
              <Bot size={14} color="#4f46e5" />
            </div>
            <div className="chat-typing-indicator">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="dock-chat-input-bar">
        <textarea
          rows={1}
          className="chat-textarea"
          placeholder="Ask a question, report an error, or order…"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          type="button"
          className="chat-send-btn"
          disabled={!inputValue.trim()}
          onClick={() => handleSend()}
          title="Send message"
        >
          <Send size={15} />
        </button>
      </div>
    </div>
  );
}

export default SolarChatbot;

