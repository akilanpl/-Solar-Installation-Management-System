import React, { useState, useEffect, useRef } from 'react';
import {
  ChevronLeft,
  Info,
  Plus,
  ArrowUp,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Wrench,
  Calendar,
  ShoppingBag,
  RotateCcw,
  Bot,
  Copy,
  Check,
  Zap,
} from 'lucide-react';
import { useRouter } from '../../router/Router';
import { useAuth } from '../../context/AuthContext';
import './SolarChatbot.css';

const DEFAULT_CONTEXT = {
  title: 'Delayed order',
  subtitle: '#48213 · 3 items',
};

const INITIAL_MESSAGES = [
  {
    id: 'msg-u1',
    sender: 'user',
    text: "Status hasn't changed in two days.",
    timestamp: '2m ago',
  },
  {
    id: 'msg-b1',
    sender: 'bot',
    text: "Held up at the sorting hub. It's out for delivery today.",
    statusCard: {
      badgeText: '24',
      primaryText: 'Today, Thu',
      secondaryText: '6-9 PM · Bengaluru Central Hub',
    },
    followUpText: 'A little something for the wait:',
    chips: [
      { id: 'chip-points', label: '300 points', variant: 'accent', action: 'claim_points' },
      { id: 'chip-shipping', label: 'Free shipping', variant: 'outline', action: 'free_shipping' },
    ],
    timestamp: 'Just now',
  },
];

export function SolarChatbot({ isOpen, onClose, onOpenStore }) {
  const { showToast, user } = useAuth();
  const { navigate } = useRouter();

  const [activeContext, setActiveContext] = useState(DEFAULT_CONTEXT);
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showInfoBanner, setShowInfoBanner] = useState(false);
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

  const handleActionClick = (action) => {
    switch (action) {
      case 'claim_points':
        handleSend("I would like to claim the 300 reward points");
        break;
      case 'free_shipping':
        handleSend("Please apply free shipping to my order");
        break;
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

      // 1. Claim points
      if (query.includes('300 points') || query.includes('claim')) {
        if (showToast) {
          showToast({
            type: 'success',
            title: 'Reward Credited',
            message: '300 points credited to your SolarOps customer account.',
          });
        }
        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "300 loyalty points have been credited to your account! You can redeem them as a ₹300 discount on any hardware in our Solar Store.",
          statusCard: {
            badgeText: '✓',
            primaryText: '300 Points Added',
            secondaryText: 'Wallet Balance: ₹300 Escrow Credit',
          },
          followUpText: 'Next steps:',
          chips: [
            { id: 'btn-store', label: 'Browse Solar Store', variant: 'accent', action: 'order_store' },
            { id: 'btn-track', label: 'Track Delivery Live', variant: 'outline', action: 'track_delivery' },
          ],
          timestamp: 'Just now',
        });
      }
      // 2. Free shipping
      else if (query.includes('free shipping')) {
        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "Free priority dispatch has been confirmed for your shipment. Your solar inverter & battery combo will arrive with zero delivery charges.",
          statusCard: {
            badgeText: '0₹',
            primaryText: 'Free Priority Delivery',
            secondaryText: 'Standard Courier Fee Waived',
          },
          timestamp: 'Just now',
        });
      }
      // 3. Inverter Fault / Error Code E-04
      else if (
        query.includes('e-04') ||
        query.includes('red alarm') ||
        query.includes('red light') ||
        query.includes('inverter')
      ) {
        setActiveContext({
          title: 'Inverter Red Alarm',
          subtitle: '#WO-2026-088 · Fault E-04 Ground Leakage',
        });

        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "Problem Diagnosed: Inverter Error E-04 (Grid Disconnect / DC Ground Leakage).\n\nFor your safety, the inverter has triggered protective anti-islanding isolation.",
          statusCard: {
            badgeText: 'E-04',
            primaryText: 'Priority Dispatch Staged',
            secondaryText: 'Assigned: Karthik Raja · Field Technician',
          },
          followUpText: 'Recommended action directives:',
          chips: [
            { id: 'btn-create-tk', label: 'File Urgent Field Ticket', variant: 'accent', action: 'auto_file_e04' },
            { id: 'btn-call-desk', label: 'Call Hotline (080 4000 7800)', variant: 'outline', action: 'call_support' },
          ],
          timestamp: 'Just now',
        });
      }
      // 4. Auto-file complaint for E-04
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
          // ignore
        }

        if (showToast) {
          showToast({
            type: 'success',
            title: 'Service Ticket Logged',
            message: `Ticket #${ticketNum} assigned to Field Engineer Karthik Raja.`,
          });
        }

        setActiveContext({
          title: 'Warranty Ticket Filed',
          subtitle: `${ticketNum} · Karthik Raja En Route`,
        });

        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: `Official Warranty Complaint Filed Successfully!\n\nYour service request has been logged under your 10-Year Inverter Replacement Warranty.`,
          statusCard: {
            badgeText: '✓',
            primaryText: `${ticketNum} Assigned`,
            secondaryText: 'Arrival ETA: Today within 2 hours',
          },
          followUpText: 'Additional actions:',
          chips: [
            { id: 'btn-open-supp', label: 'View in Support Desk', variant: 'accent', action: 'go_support' },
            { id: 'btn-order-acc', label: 'Browse Solar Store', variant: 'outline', action: 'order_store' },
          ],
          timestamp: 'Just now',
        });
      }
      // 5. Order stuffs & Solar Store
      else if (
        query.includes('order') ||
        query.includes('buy') ||
        query.includes('store') ||
        query.includes('product') ||
        query.includes('battery') ||
        query.includes('panel')
      ) {
        setActiveContext({
          title: 'Solar Marketplace',
          subtitle: 'Tier-1 Certified Spares & Kits',
        });

        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "SolarFlow Hardware Marketplace is active. You can order genuine Tier-1 solar panels, hybrid inverters, LiFePO4 batteries, and automated sprinkler kits with free 24h delivery across Bengaluru.",
          statusCard: {
            badgeText: 'PV',
            primaryText: 'Warehouse In Stock',
            secondaryText: 'Fast 24h Staging at Bengaluru Depot',
          },
          followUpText: 'Explore hardware items:',
          chips: [
            { id: 'sc-open', label: 'Open Solar Store', variant: 'accent', action: 'order_store' },
            { id: 'sc-sprinkler', label: 'Auto Cleaning Kit (₹4,999)', variant: 'outline', action: 'order_store' },
          ],
          timestamp: 'Just now',
        });
      }
      // 6. Maintenance
      else if (query.includes('maintenance') || query.includes('cleaning') || query.includes('inspection')) {
        setActiveContext({
          title: 'Rooftop Maintenance',
          subtitle: 'Quarterly Service Slot',
        });

        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "Rooftop Solar Maintenance Scheduled. A certified field technician will perform deep panel washing, MC4 torque check, and thermographic hotspot analysis.",
          statusCard: {
            badgeText: '10',
            primaryText: 'Tomorrow, Fri',
            secondaryText: '9-11 AM · Indiranagar Premise',
          },
          followUpText: 'Confirm maintenance visit:',
          chips: [
            { id: 'm-confirm', label: 'Confirm Slot (Fri 9 AM)', variant: 'accent', action: 'confirm_maint' },
            { id: 'm-reschedule', label: 'Change Time Window', variant: 'outline', action: 'reschedule_maint' },
          ],
          timestamp: 'Just now',
        });
      }
      // 7. General fallback
      else {
        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "I'm here to help you resolve rooftop solar problems, track hardware orders, or file official complaints.",
          statusCard: {
            badgeText: 'AI',
            primaryText: 'System Telemetry Synced',
            secondaryText: 'Local DB Active · 5 kW Hybrid Inverter',
          },
          followUpText: 'Quick diagnostic topics:',
          chips: [
            { id: 'f1', label: 'Inverter Red Alarm E-04', variant: 'accent', action: 'inverter_fault' },
            { id: 'f2', label: 'Delayed order #48213', variant: 'outline', action: 'status_delayed' },
            { id: 'f3', label: 'Shop Solar Store', variant: 'outline', action: 'order_store' },
          ],
          timestamp: 'Just now',
        });
      }
    }, 450);
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
    if (chip.action === 'order_store' || chip.action === 'go_store') {
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
    if (chip.action === 'track_delivery') {
      handleSend("Where is my delivery right now?");
      return;
    }
    if (chip.action === 'status_delayed') {
      setActiveContext(DEFAULT_CONTEXT);
      handleSend("Status hasn't changed in two days.");
      return;
    }
    handleActionClick(chip.action);
  };

  const handleReset = () => {
    setMessages(INITIAL_MESSAGES);
    setActiveContext(DEFAULT_CONTEXT);
    setShowInfoBanner((prev) => !prev);
    if (showToast) {
      showToast({
        type: 'info',
        title: 'Chat Session Ready',
        message: 'Assistant context synchronized with local DB.',
      });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="dock-chat-panel" aria-label="SolarFlow AI Assistant">
      {/* Top Banner Card matching Reference Layout & Dashboard Color Theme */}
      <div className="lemon-chat-header">
        <div className="lemon-header-top-row">
          <div className="lemon-bot-identity">
            <div className="lemon-avatar-circle">
              <span className="lemon-avatar-letter">S</span>
            </div>
            <div className="lemon-identity-text">
              <span className="lemon-bot-name">SolarFlow AI</span>
              <span className="lemon-bot-status">
                <span className="lemon-status-dot" />
                <span>online</span>
              </span>
            </div>
          </div>

          <div className="lemon-header-actions">
            <button
              type="button"
              className="lemon-circle-btn"
              onClick={onClose}
              title="Close / Minimize Assistant"
              aria-label="Back / Minimize"
            >
              <ChevronLeft size={18} />
            </button>
            <button
              type="button"
              className="lemon-circle-btn"
              onClick={handleReset}
              title="Reset / Diagnostic Info"
              aria-label="Info / Reset"
            >
              <Info size={16} />
            </button>
          </div>
        </div>

        <div className="lemon-header-bottom-row">
          <h3 className="lemon-context-title">{activeContext.title}</h3>
          <span className="lemon-context-subtitle">{activeContext.subtitle}</span>
        </div>
      </div>

      {/* Info Pill Banner when toggled */}
      {showInfoBanner && (
        <div className="lemon-system-info-bar">
          <span>Synced with 5 kW Inverter · Bescom Meter #8812 · Local DB Active</span>
        </div>
      )}

      {/* Inner White Messages Container */}
      <div className="lemon-messages-card">
        <div className="lemon-messages-scroll">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`lemon-msg-row ${msg.sender === 'user' ? 'user-side' : 'bot-side'}`}
            >
              {msg.sender === 'user' ? (
                <div className="lemon-user-bubble">
                  {msg.text}
                </div>
              ) : (
                <div className="lemon-bot-bubble-wrapper">
                  <div className="lemon-bot-dark-card">
                    <p className="lemon-bot-text" style={{ whiteSpace: 'pre-line' }}>
                      {msg.text}
                    </p>

                    {/* Inset Status Pill / Capsule (matches "[24] Today, Thu · 6-9 PM") */}
                    {msg.statusCard && (
                      <div className="lemon-status-capsule">
                        <div className="lemon-capsule-badge">
                          {msg.statusCard.badgeText}
                        </div>
                        <div className="lemon-capsule-info">
                          <span className="lemon-capsule-primary">{msg.statusCard.primaryText}</span>
                          <span className="lemon-capsule-secondary">{msg.statusCard.secondaryText}</span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Follow-up Prompt line if chips exist */}
                  {msg.followUpText && (
                    <div className="lemon-followup-label">
                      {msg.followUpText}
                    </div>
                  )}

                  {/* Action Chips: Filled accent pill, White outline pill, and Dark 3-dots pill */}
                  {msg.chips && msg.chips.length > 0 && (
                    <div className="lemon-action-chips-row">
                      {msg.chips.map((chip, idx) => (
                        <button
                          key={chip.id || idx}
                          type="button"
                          className={`lemon-chip-pill ${chip.variant || (idx === 0 ? 'accent' : 'outline')}`}
                          onClick={() => handleChipClick(chip)}
                        >
                          {chip.label}
                        </button>
                      ))}
                      <button
                        type="button"
                        className="lemon-chip-pill more-dots"
                        title="More options"
                        onClick={() => handleSend("What other options are available?")}
                      >
                        <span>···</span>
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {isTyping && (
            <div className="lemon-msg-row bot-side">
              <div className="lemon-bot-bubble-wrapper">
                <div className="lemon-bot-dark-card typing">
                  <div className="lemon-typing-dots">
                    <span className="dot" />
                    <span className="dot" />
                    <span className="dot" />
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Floating Bottom Input Bar */}
      <div className="lemon-input-bar">
        <div className="lemon-input-pill">
          <button
            type="button"
            className="lemon-attach-btn"
            title="Options & Quick Diagnostics"
            onClick={() => handleSend("Diagnose my 5 kW hybrid inverter status")}
          >
            <Plus size={16} />
          </button>
          <input
            type="text"
            className="lemon-text-input"
            placeholder="Message..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>

        <button
          type="button"
          className={`lemon-send-circle-btn ${inputValue.trim() ? 'active' : ''}`}
          onClick={() => handleSend()}
          disabled={!inputValue.trim()}
          title="Send message"
          aria-label="Send message"
        >
          <ArrowUp size={20} />
        </button>
      </div>
    </div>
  );
}

export default SolarChatbot;
