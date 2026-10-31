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
  TrendingDown,
  Coins,
  FileText,
  ThumbsUp,
  ThumbsDown,
  Copy,
  Check,
  Zap,
  Cpu,
  Clock,
  Sparkle,
} from 'lucide-react';
import { useRouter } from '../../router/Router';
import { useAuth } from '../../context/AuthContext';
import './SolarChatbot.css';

const INITIAL_MESSAGES = [
  {
    id: 'msg-1',
    sender: 'bot',
    text: "Hello Arun! I'm your SolarFlow AI Engineering Assistant. I can diagnose rooftop inverter faults, file official warranty service requests, book on-site technician visits, or help you order panels & accessories. How can I assist you today?",
    timestamp: 'Just now',
    chips: [
      { id: 'chip-inverter', label: 'Inverter Red Alarm / E-04', icon: 'alert', action: 'inverter_fault' },
      { id: 'chip-complaint', label: 'File Warranty Complaint', icon: 'file', action: 'file_complaint' },
      { id: 'chip-book', label: 'Book Rooftop Maintenance', icon: 'calendar', action: 'book_maintenance' },
      { id: 'chip-order', label: 'Order Solar Products', icon: 'cart', action: 'order_store' },
      { id: 'chip-generation', label: 'Low Solar Generation', icon: 'trending', action: 'low_generation' },
      { id: 'chip-subsidy', label: 'PM Surya Ghar Subsidy', icon: 'coins', action: 'check_subsidy' },
    ],
  },
];

export function SolarChatbot({ isOpen, onClose, onOpenStore }) {
  const { showToast, user } = useAuth();
  const { navigate } = useRouter();
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [feedbackState, setFeedbackState] = useState({});
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen, isTyping]);

  const addMessage = (message) => {
    setMessages((prev) => [...prev, message]);
  };

  const handleCopyMessage = (msgId, text) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedId(msgId);
      setTimeout(() => setCopiedId(null), 2000);
      if (showToast) {
        showToast({
          type: 'info',
          title: 'Copied to Clipboard',
          message: 'AI response copied for your records.',
        });
      }
    }
  };

  const handleFeedback = (msgId, type) => {
    setFeedbackState((prev) => ({ ...prev, [msgId]: type }));
    if (showToast) {
      showToast({
        type: 'success',
        title: type === 'up' ? 'Helpful Response' : 'Feedback Logged',
        message:
          type === 'up'
            ? 'Thank you! Your feedback improves our diagnostic model.'
            : 'Feedback noted. Our engineering support desk has been flagged.',
      });
    }
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
          text: "Problem Diagnosed: Inverter Error E-04 (Grid Disconnect / DC Ground Leakage)\n\nThis indicates an AC grid phase imbalance from BESCOM or insulation breakdown in the DC array wiring. For your safety, the inverter has entered protection mode.",
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
            { id: 'btn-create-tk', label: 'File Urgent Field Repair Ticket', icon: 'alert', action: 'auto_file_e04' },
            { id: 'btn-call-desk', label: 'Call Emergency Desk (+91 80 4000 7800)', icon: 'phone', action: 'call_support' },
          ],
          timestamp: 'Just now',
        });
      }
      // 2. Auto-file complaint for E-04
      else if (query.includes('file urgent') || query.includes('auto_file_e04')) {
        const ticketNum = 'TK-' + Math.floor(1000 + Math.random() * 9000);
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
          text: `Official Warranty Complaint Filed Successfully!\n\nYour service request has been logged and prioritized under your 10-Year Inverter Replacement Warranty.`,
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
            { id: 'btn-open-supp', label: 'View in Support Desk', icon: 'file', action: 'go_support' },
            { id: 'btn-order-acc', label: 'Browse Solar Accessories', icon: 'cart', action: 'order_store' },
          ],
          timestamp: 'Just now',
        });
      }
      // 3. File general complaint
      else if (query.includes('file') && query.includes('complaint')) {
        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "I can help you file a complaint immediately with our engineering team. Please select the specific issue category:",
          chips: [
            { id: 'c1', label: 'Inverter Tripping / Noise', icon: 'alert', action: 'inverter_fault' },
            { id: 'c2', label: 'Physical Solar Panel Issue', icon: 'tool', action: 'panel_damage' },
            { id: 'c3', label: 'BESCOM Net-Metering Delay', icon: 'trending', action: 'discom_delay' },
            { id: 'c4', label: 'Billing / Subsidy Dispute', icon: 'coins', action: 'check_subsidy' },
          ],
          timestamp: 'Just now',
        });
      }
      // 4. Low Generation
      else if (query.includes('low generation') || query.includes('less electricity') || query.includes('generation')) {
        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "Solar Yield Diagnostic Analysis\n\nBased on your 5 kW Bifacial Mono-PERC system in Bengaluru:\n• Normal dry season output: 22-26 kWh/day\n• Dust & soiling degrades output by 15%-25% after 3 weeks without rain.\n\nRecommended Action: Clean panels early morning using soft microfiber squeegee and plain water, or install automated sprinkler nozzles.",
          cardType: 'product_recommendation',
          productData: {
            name: 'Solar Rooftop Sprinkler Cleaning Kit',
            price: '₹4,999',
            mrp: '₹6,500',
            discount: '23% OFF',
            desc: '10-Nozzle high pressure automated cleaning kit with WiFi timer.',
          },
          chips: [
            { id: 'btn-buy-clean', label: 'Order Cleaning Kit (₹4,999)', icon: 'cart', action: 'order_cleaning_kit' },
            { id: 'btn-book-clean', label: 'Book Professional Cleaning (₹1,499)', icon: 'calendar', action: 'book_cleaning_service' },
          ],
          timestamp: 'Just now',
        });
      }
      // 5. Order stuffs & Solar Store
      else if (query.includes('order') || query.includes('buy') || query.includes('store') || query.includes('product') || query.includes('battery') || query.includes('panel')) {
        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "SolarFlow Hardware Marketplace\n\nYou can order genuine Tier-1 solar equipment, lithium battery storage, automated cleaning kits, and BOS accessories directly with free delivery across Bengaluru!",
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
            { id: 'btn-go-store', label: 'Open Solar Ecommerce Store', icon: 'cart', action: 'go_store' },
            { id: 'btn-order-kit', label: 'Quick Order Cleaning Kit', icon: 'zap', action: 'order_cleaning_kit' },
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
            title: 'Order Dispatched',
            message: `Order #${orderId} confirmed for ₹4,999. Free Bengaluru delivery.`,
          });
        }

        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: `Order Confirmed: #${orderId}\n\n1x Automatic Solar Rooftop Sprinkler Cleaning Kit has been placed. Dispatched from Peenya Warehouse.\n\nDelivery Address: #42, 4th Cross, Indiranagar, Bengaluru\nPayment Method: Pay on Delivery & Inspection`,
          chips: [
            { id: 'btn-order-more', label: 'Upgrade with LiFePO4 Storage', icon: 'cart', action: 'go_store' },
            { id: 'btn-ask-help', label: 'Check Inverter Status', icon: 'alert', action: 'inverter_fault' },
          ],
          timestamp: 'Just now',
        });
      }
      // Fallback
      else {
        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: `Thank you for your message! I'm synchronized with your 5 kW hybrid solar plant data. I can assist with error diagnosis, warranty claim filing, scheduling technician visits, or ordering panels & accessories.`,
          chips: [
            { id: 'f1', label: 'Diagnose Inverter Error', icon: 'alert', action: 'inverter_fault' },
            { id: 'f2', label: 'File Service Complaint', icon: 'file', action: 'file_complaint' },
            { id: 'f3', label: 'Book Maintenance Visit', icon: 'calendar', action: 'book_maintenance' },
            { id: 'f4', label: 'Shop Solar Store', icon: 'cart', action: 'order_store' },
          ],
          timestamp: 'Just now',
        });
      }
    }, 600);
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
        message: 'Assistant conversation cleared.',
      });
    }
  };

  const renderChipIcon = (icon) => {
    switch (icon) {
      case 'alert':
        return <AlertTriangle size={13} color="#ef4444" />;
      case 'file':
        return <FileText size={13} color="#2563eb" />;
      case 'calendar':
        return <Calendar size={13} color="#8b5cf6" />;
      case 'cart':
        return <ShoppingBag size={13} color="#4f46e5" />;
      case 'trending':
        return <TrendingDown size={13} color="#f59e0b" />;
      case 'coins':
        return <Coins size={13} color="#10b981" />;
      case 'tool':
        return <Wrench size={13} color="#0284c7" />;
      case 'phone':
        return <PhoneCall size={13} color="#10b981" />;
      case 'zap':
        return <Zap size={13} color="#2563eb" />;
      default:
        return <Sparkles size={13} color="#4f46e5" />;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="dock-chat-panel" aria-label="SolarFlow AI Assistant">
      {/* Sleek Copilot Header */}
      <div className="dock-chat-header">
        <div className="chat-header-identity">
          <div className="bot-avatar-badge">
            <Sparkles size={18} color="#ffffff" />
            <span className="ai-core-ping" />
          </div>
          <div>
            <div className="bot-name-row">
              <h4 className="bot-title">SolarFlow AI Copilot</h4>
              <span className="live-telemetry-badge">
                <span className="live-pulse-dot" />
                <span>ACTIVE</span>
              </span>
            </div>
            <span className="bot-subtext">Diagnostic reasoning & instant solutions</span>
          </div>
        </div>

        <div className="chat-header-actions">
          <button
            type="button"
            className="chat-icon-btn"
            title="Reset Chat Session"
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

      {/* IoT Inverter Live Sync Bar */}
      <div className="chat-system-status-bar">
        <div className="status-indicator-group">
          <ShieldCheck size={14} color="#10b981" />
          <span>Synced: 5 kW Hybrid Inverter (E-04 Alert) · Local SQLite Active</span>
        </div>
        <span className="latency-chip">12ms</span>
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
                <Bot size={15} color="#4f46e5" />
              </div>
            )}

            <div className="chat-bubble-container">
              <div className={`chat-bubble ${msg.sender === 'user' ? 'user-bubble' : 'bot-bubble'}`}>
                <div className="msg-text-content" style={{ whiteSpace: 'pre-line' }}>
                  {msg.text}
                </div>

                {/* Priority Diagnostic Card */}
                {msg.cardType === 'diagnostic' && msg.diagnosticData && (
                  <div className="chat-diagnostic-card">
                    <div className="diag-header">
                      <div className="diag-title-group">
                        <AlertTriangle size={15} color="#ef4444" />
                        <span className="diag-title">Critical Fault: {msg.diagnosticData.code}</span>
                      </div>
                      <span className="diag-badge">{msg.diagnosticData.severity}</span>
                    </div>
                    <ul className="diag-list">
                      {msg.diagnosticData.steps.map((st, i) => (
                        <li key={i}>{st}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Verified Ticket Card */}
                {msg.cardType === 'ticket' && msg.ticketData && (
                  <div className="chat-ticket-card">
                    <div className="ticket-card-header">
                      <div className="ticket-ref-group">
                        <Wrench size={14} color="#2563eb" />
                        <span className="ticket-num">{msg.ticketData.ticketId}</span>
                      </div>
                      <span className="ticket-status-pill">Dispatched</span>
                    </div>
                    <div className="ticket-card-body">
                      <div className="ticket-field-row">
                        <span className="t-label">Issue:</span>
                        <span className="t-val">{msg.ticketData.issue}</span>
                      </div>
                      <div className="ticket-field-row">
                        <span className="t-label">Technician:</span>
                        <span className="t-val highlight">{msg.ticketData.assignedTo}</span>
                      </div>
                      <div className="ticket-field-row">
                        <span className="t-label">Arrival Window:</span>
                        <span className="t-val">{msg.ticketData.eta}</span>
                      </div>
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

                {/* Store Showcase Table */}
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

                {/* Assistant Message Micro-Interactions (Feedback & Copy) */}
                {msg.sender === 'bot' && (
                  <div className="msg-micro-actions-row">
                    <span className="msg-timestamp">{msg.timestamp}</span>
                    <div className="micro-btn-group">
                      <button
                        type="button"
                        className="micro-action-btn"
                        onClick={() => handleCopyMessage(msg.id, msg.text)}
                        title="Copy Response"
                      >
                        {copiedId === msg.id ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                      </button>
                      <button
                        type="button"
                        className={`micro-action-btn ${feedbackState[msg.id] === 'up' ? 'active-feedback' : ''}`}
                        onClick={() => handleFeedback(msg.id, 'up')}
                        title="Helpful"
                      >
                        <ThumbsUp size={12} />
                      </button>
                      <button
                        type="button"
                        className={`micro-action-btn ${feedbackState[msg.id] === 'down' ? 'active-feedback' : ''}`}
                        onClick={() => handleFeedback(msg.id, 'down')}
                        title="Not Helpful"
                      >
                        <ThumbsDown size={12} />
                      </button>
                    </div>
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
                      <span className="chip-icon-box">{renderChipIcon(chip.icon)}</span>
                      <span>{chip.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="chat-bubble-row bot-side">
            <div className="bot-msg-avatar">
              <Bot size={15} color="#4f46e5" />
            </div>
            <div className="chat-typing-container">
              <div className="chat-typing-indicator">
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </div>
              <span className="typing-label">SolarFlow AI is analyzing system telemetry…</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Floating Prompt Shortcuts Row */}
      <div className="chat-quick-hints-row">
        <button
          type="button"
          className="hint-pill"
          onClick={() => handleSend("Diagnose my 5 kW hybrid inverter status")}
        >
          Check Inverter Status
        </button>
        <button
          type="button"
          className="hint-pill"
          onClick={() => handleSend("What is the next scheduled rooftop maintenance visit?")}
        >
          Maintenance Visit
        </button>
        <button
          type="button"
          className="hint-pill"
          onClick={() => handleSend("I want to order solar panels")}
        >
          Store Catalog
        </button>
      </div>

      {/* Input Bar */}
      <div className="dock-chat-input-bar">
        <div className="input-textarea-wrapper">
          <textarea
            rows={1}
            className="chat-textarea"
            placeholder="Ask a question, diagnose a fault, or order…"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>
        <button
          type="button"
          className={`chat-send-btn ${inputValue.trim() ? 'active' : ''}`}
          disabled={!inputValue.trim()}
          onClick={() => handleSend()}
          title="Send message (Enter ↵)"
        >
          <Send size={15} />
        </button>
      </div>
    </div>
  );
}

export default SolarChatbot;
