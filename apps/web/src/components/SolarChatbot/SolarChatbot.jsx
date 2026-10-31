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
  Mic,
  MicOff,
  Volume2,
  VolumeX,
} from 'lucide-react';
import { useRouter } from '../../router/Router';
import { useAuth } from '../../context/AuthContext';
import './SolarChatbot.css';

const DEFAULT_CONTEXT = {
  title: 'Rooftop Solar Assistant',
  subtitle: '5 kW Bifacial System · Live Telemetry Online',
};

const INITIAL_MESSAGES = [
  {
    id: 'msg-u1',
    sender: 'user',
    text: "Check my solar system health and generation status.",
    timestamp: '2m ago',
  },
  {
    id: 'msg-b1',
    sender: 'bot',
    text: "All 10 Bifacial Mono PERC modules and 5 kW Hybrid Inverter are operating at peak efficiency.\n\nToday's rooftop solar generation is 22.4 kWh with 92% battery reserve and active BESCOM net-meter export.",
    statusCard: {
      badgeText: '4.8 kW',
      primaryText: 'System Operating Normally',
      secondaryText: '22.4 kWh Generated · 92% Battery SOC · Grid Connected',
    },
    followUpText: 'Quick diagnostic topics & service actions:',
    chips: [
      { id: 'chip-inverter', label: 'Inverter Red Alarm (E-04)', variant: 'accent', action: 'inverter_fault' },
      { id: 'chip-subsidy', label: 'PM Surya Ghar Subsidy (₹78k)', variant: 'outline', action: 'check_subsidy' },
      { id: 'chip-battery', label: 'Battery Backup Level', variant: 'outline', action: 'check_battery' },
      { id: 'chip-maintenance', label: 'Book Technician Visit', variant: 'outline', action: 'book_maintenance' },
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

  // Accessibility: Speech to Text (Mic Dictation) & Read Aloud (Screen Reader)
  const [isListening, setIsListening] = useState(false);
  const [autoReadAloud, setAutoReadAloud] = useState(false);
  const [speakingMsgId, setSpeakingMsgId] = useState(null);
  const recognitionRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen, isTyping]);

  // Clean up speech synthesis and recognition on unmount or close
  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
    };
  }, [isOpen]);

  // Read Aloud using SpeechSynthesis for visually impaired customers
  const speakText = (text, msgId = null) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      showToast({
        type: 'info',
        title: 'Speech Synthesis Unavailable',
        message: 'Speech synthesis is not supported on this browser device.',
      });
      return;
    }

    if (speakingMsgId === msgId && msgId !== null) {
      window.speechSynthesis.cancel();
      setSpeakingMsgId(null);
      return;
    }

    window.speechSynthesis.cancel();
    const cleanText = text
      .replace(/[*_#`~[\]]/g, '')
      .replace(/\(https?:\/\/[^\)]+\)/g, '')
      .trim();

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 0.94;
    utterance.pitch = 1.0;
    utterance.lang = 'en-IN';

    utterance.onstart = () => {
      setSpeakingMsgId(msgId);
    };

    utterance.onend = () => {
      setSpeakingMsgId(null);
    };

    utterance.onerror = () => {
      setSpeakingMsgId(null);
    };

    window.speechSynthesis.speak(utterance);
  };

  // Speech to Text Microphone Dictation for disabled/motor-impaired customers
  const handleToggleSpeechToText = () => {
    if (isListening) {
      stopListening();
      return;
    }

    const SpeechRecognition =
      typeof window !== 'undefined' &&
      (window.SpeechRecognition || window.webkitSpeechRecognition);

    if (!SpeechRecognition) {
      showToast({
        type: 'info',
        title: 'Voice Input Demo',
        message: 'Speech recognition simulated for this browser device.',
      });
      setInputValue('How much solar electricity did my 5 kW rooftop generate today?');
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-IN';

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        if (transcript) {
          setInputValue(transcript);
        }
      };

      recognition.onerror = (e) => {
        console.warn('Speech recognition notice:', e);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.warn('Speech recognition start failed:', err);
      setIsListening(false);
      setInputValue('Check my solar panel generation and PM Surya Ghar subsidy');
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
      recognitionRef.current = null;
    }
    setIsListening(false);
  };

  const addMessage = (message) => {
    setMessages((prev) => [...prev, message]);
    if (message.sender === 'bot' && autoReadAloud) {
      speakText(message.text, message.id);
    }
  };

  const handleActionClick = (action) => {
    switch (action) {
      case 'inverter_fault':
        handleSend("My inverter is showing a red alarm light with Error Code E-04");
        break;
      case 'check_subsidy':
        handleSend("What is the status of my PM Surya Ghar national portal subsidy?");
        break;
      case 'check_generation':
        handleSend("How much power did my solar panels generate today?");
        break;
      case 'check_battery':
        handleSend("What is my battery level and backup runtime for power outages?");
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
      default:
        break;
    }
  };

  const processBotResponse = (userText) => {
    setIsTyping(true);
    const query = userText.toLowerCase();

    setTimeout(() => {
      setIsTyping(false);

      // 1. PM Surya Ghar Subsidy
      if (
        query.includes('subsidy') ||
        query.includes('surya ghar') ||
        query.includes('national portal') ||
        query.includes('dbt') ||
        query.includes('78000') ||
        query.includes('78k')
      ) {
        setActiveContext({
          title: 'PM Surya Ghar Subsidy',
          subtitle: 'Ref #PMSG-BLR-2026-9912 · Approved',
        });

        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "PM Surya Ghar National Portal Status: ₹78,000 central government subsidy has been approved for your 5 kW rooftop installation!\n\nBidirectional net-meter synchronization verified by BESCOM. Direct Benefit Transfer (DBT) will be credited directly to your Aadhaar-linked bank account.",
          statusCard: {
            badgeText: '₹78k',
            primaryText: 'Subsidy Sanctioned (Stage 4/5)',
            secondaryText: 'DBT Credit scheduled in 4-6 business days',
          },
          followUpText: 'Recommended subsidy actions:',
          chips: [
            { id: 'btn-store-sub', label: 'Apply Balance in Store', variant: 'accent', action: 'order_store' },
            { id: 'btn-gen-sub', label: 'Check Solar Generation', variant: 'outline', action: 'check_generation' },
          ],
          timestamp: 'Just now',
        });
      }
      // 2. Solar Generation & Savings Telemetry
      else if (
        query.includes('generation') ||
        query.includes('generate') ||
        query.includes('how much power') ||
        query.includes('kwh') ||
        query.includes('savings') ||
        query.includes('production')
      ) {
        setActiveContext({
          title: 'Generation Telemetry',
          subtitle: '5 kW Mono PERC · Indiranagar',
        });

        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "Today's rooftop solar generation is 22.4 kWh (peak output 4.8 kW at 1:15 PM).\n\n• Self-consumption: 14.2 kWh (63%)\n• Exported to BESCOM Grid: 8.2 kWh (37%)\n• Estimated electricity bill savings this month: ₹4,650.",
          statusCard: {
            badgeText: '22.4',
            primaryText: '22.4 kWh Generated Today',
            secondaryText: 'CO₂ Avoided: 18.2 kg · Grid Export: 8.2 kWh',
          },
          followUpText: 'System optimization directives:',
          chips: [
            { id: 'btn-clean-gen', label: 'Auto Cleaning Kit (₹4,999)', variant: 'accent', action: 'order_store' },
            { id: 'btn-inv-gen', label: 'Check Inverter Status', variant: 'outline', action: 'inverter_fault' },
          ],
          timestamp: 'Just now',
        });
      }
      // 3. Battery Storage & Power Outage Backup
      else if (
        query.includes('battery') ||
        query.includes('backup') ||
        query.includes('soc') ||
        query.includes('power cut') ||
        query.includes('blackout') ||
        query.includes('outage')
      ) {
        setActiveContext({
          title: 'Battery Energy Storage',
          subtitle: '5.12 kWh LiFePO4 · Smart BMS Active',
        });

        addMessage({
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: "Battery State of Charge is currently 92% (4.7 kWh stored energy).\n\nIn the event of a grid power cut, your essential rooftop loads (refrigerator, WiFi, lights, and fans) will run autonomously for ~9.5 hours.",
          statusCard: {
            badgeText: '92%',
            primaryText: 'Backup Ready: ~9.5 Hours',
            secondaryText: '51.2V · 100Ah · Battery Health 99%',
          },
          followUpText: 'Energy management options:',
          chips: [
            { id: 'btn-store-bat', label: '5kWh Expansion Battery', variant: 'accent', action: 'order_store' },
            { id: 'btn-sub-bat', label: 'Check Subsidy Status', variant: 'outline', action: 'check_subsidy' },
          ],
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
          text: "I'm your SolarFlow AI Assistant. I can help diagnose inverter alarms (E-04), report real-time solar generation, track your PM Surya Ghar subsidy, or schedule rooftop maintenance.",
          statusCard: {
            badgeText: 'AI',
            primaryText: 'Telemetry Synced & Active',
            secondaryText: '5 kW Inverter · Indiranagar Substation Grid Sync',
          },
          followUpText: 'Quick diagnostic topics:',
          chips: [
            { id: 'f1', label: 'Inverter Red Alarm E-04', variant: 'accent', action: 'inverter_fault' },
            { id: 'f2', label: 'PM Surya Ghar Subsidy (₹78k)', variant: 'outline', action: 'check_subsidy' },
            { id: 'f3', label: 'Solar Generation Status', variant: 'outline', action: 'check_generation' },
            { id: 'f4', label: 'Browse Solar Store', variant: 'outline', action: 'order_store' },
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
      handleSend("Where is my solar hardware delivery right now?");
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
            {/* Auto Read Aloud Accessibility Switch for Visually Impaired Customers */}
            <button
              type="button"
              className={`lemon-speech-toggle-btn ${autoReadAloud ? 'active' : ''}`}
              onClick={() => {
                const next = !autoReadAloud;
                setAutoReadAloud(next);
                if (next) {
                  showToast({
                    type: 'info',
                    title: 'Auto Read Aloud Enabled',
                    message: 'Responses will now be read aloud automatically for visually impaired users.',
                  });
                } else {
                  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
                    window.speechSynthesis.cancel();
                  }
                  setSpeakingMsgId(null);
                }
              }}
              title={autoReadAloud ? 'Auto Read Aloud Active (Click to mute)' : 'Enable Auto Read Aloud (Visually Impaired Mode)'}
              aria-label="Toggle auto read aloud for visually impaired customers"
            >
              {autoReadAloud ? <Volume2 size={16} /> : <VolumeX size={16} />}
            </button>

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
                    {/* Read Aloud Bar for Visually Impaired Customers */}
                    <div className="lemon-bot-card-top-bar">
                      <span className="lemon-bot-tag">SolarFlow AI</span>
                      <button
                        type="button"
                        className={`lemon-listen-btn ${speakingMsgId === msg.id ? 'active-speaking' : ''}`}
                        onClick={() => speakText(msg.text, msg.id)}
                        title={speakingMsgId === msg.id ? 'Stop reading' : 'Read aloud for visually impaired'}
                        aria-label="Read message aloud"
                      >
                        {speakingMsgId === msg.id ? <VolumeX size={13} /> : <Volume2 size={13} />}
                        <span>{speakingMsgId === msg.id ? 'Stop' : 'Read Aloud'}</span>
                      </button>
                    </div>

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

      {/* Speech-to-Text Listening Banner */}
      {isListening && (
        <div className="speech-listening-banner" role="status" aria-live="polite">
          <span className="listening-pulse-dot" />
          <span className="listening-text">Listening to your voice... Speak now</span>
          <button
            type="button"
            className="listening-stop-btn"
            onClick={stopListening}
          >
            Done
          </button>
        </div>
      )}

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
            placeholder={isListening ? "Listening to your voice..." : "Ask or speak about inverter errors, solar generation, subsidy..."}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            aria-label="Ask about solar operations or use speech to text"
          />

          {/* Speech-to-Text Microphone Dictation Button */}
          <button
            type="button"
            className={`lemon-voice-btn ${isListening ? 'listening' : ''}`}
            onClick={handleToggleSpeechToText}
            title={isListening ? 'Stop listening' : 'Voice input (Speech to Text)'}
            aria-label="Voice input speech to text"
          >
            {isListening ? <MicOff size={16} /> : <Mic size={16} />}
          </button>
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
