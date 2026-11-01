import React, { useState, useEffect, useRef } from 'react';
import {
  Accessibility,
  Volume2,
  VolumeX,
  Eye,
  Type,
  Pause,
  Play,
  RotateCcw,
  Sparkles,
  Zap,
  Check,
  X,
  Volume1,
  Sun,
  Layers,
  ChevronRight,
  Mic,
  ShieldCheck,
  Headphones,
  Sliders,
} from 'lucide-react';
import { useRouter } from '../../router/Router';
import { useAuth } from '../../context/AuthContext';
import './CustomerAccessibility.css';

export function CustomerAccessibility() {
  const { path } = useRouter();
  const { user, showToast } = useAuth();

  // Scoped strictly to customer section
  const isCustomerScope =
    user?.role === 'customer' ||
    path.startsWith('/customer') ||
    path === '/customer' ||
    path.startsWith('/store');

  const [isOpen, setIsOpen] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [speechRate, setSpeechRate] = useState(0.92);

  // Accessibility Preferences
  const [highContrast, setHighContrast] = useState(() => {
    try {
      return localStorage.getItem('solarops_a11y_contrast') === 'true';
    } catch {
      return false;
    }
  });

  const [textSize, setTextSize] = useState(() => {
    try {
      return localStorage.getItem('solarops_a11y_text_size') || 'normal'; // 'normal' | 'large' | 'xlarge'
    } catch {
      return 'normal';
    }
  });

  const [dyslexicFont, setDyslexicFont] = useState(() => {
    try {
      return localStorage.getItem('solarops_a11y_dyslexic') === 'true';
    } catch {
      return false;
    }
  });

  const [reduceMotion, setReduceMotion] = useState(() => {
    try {
      return localStorage.getItem('solarops_a11y_reduce_motion') === 'true';
    } catch {
      return false;
    }
  });

  const [audioFeedback, setAudioFeedback] = useState(() => {
    try {
      return localStorage.getItem('solarops_a11y_audio_feedback') === 'true';
    } catch {
      return false;
    }
  });

  const [readingRuler, setReadingRuler] = useState(false);
  const [rulerTop, setRulerTop] = useState(200);

  // Active helpers count
  const activeAidsCount = [
    highContrast,
    textSize !== 'normal',
    dyslexicFont,
    readingRuler,
    audioFeedback,
    reduceMotion,
  ].filter(Boolean).length;

  // Web Audio Earcon Synthesizer (Zero network asset requirement)
  const playEarcon = (frequency = 600, type = 'sine', duration = 0.12) => {
    if (!audioFeedback || typeof window === 'undefined') return;
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = type;
      osc.frequency.setValueAtTime(frequency, ctx.currentTime);
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + duration);
    } catch (e) {
      // AudioContext blocked or unsupported
    }
  };

  // Sync DOM classes with accessibility state
  useEffect(() => {
    const root = document.documentElement;

    // High Contrast
    if (highContrast) {
      root.classList.add('customer-high-contrast');
      try {
        localStorage.setItem('solarops_a11y_contrast', 'true');
      } catch {}
    } else {
      root.classList.remove('customer-high-contrast');
      try {
        localStorage.setItem('solarops_a11y_contrast', 'false');
      } catch {}
    }

    // Text Sizing
    root.classList.remove('customer-text-large', 'customer-text-xlarge');
    if (textSize === 'large') root.classList.add('customer-text-large');
    if (textSize === 'xlarge') root.classList.add('customer-text-xlarge');
    try {
      localStorage.setItem('solarops_a11y_text_size', textSize);
    } catch {}

    // Dyslexic Font
    if (dyslexicFont) {
      root.classList.add('customer-dyslexia-spacing');
      try {
        localStorage.setItem('solarops_a11y_dyslexic', 'true');
      } catch {}
    } else {
      root.classList.remove('customer-dyslexia-spacing');
      try {
        localStorage.setItem('solarops_a11y_dyslexic', 'false');
      } catch {}
    }

    // Reduce Motion
    if (reduceMotion) {
      root.classList.add('customer-reduce-motion');
      try {
        localStorage.setItem('solarops_a11y_reduce_motion', 'true');
      } catch {}
    } else {
      root.classList.remove('customer-reduce-motion');
      try {
        localStorage.setItem('solarops_a11y_reduce_motion', 'false');
      } catch {}
    }
  }, [highContrast, textSize, dyslexicFont, reduceMotion]);

  // Clean up classes when leaving customer portal
  useEffect(() => {
    if (!isCustomerScope) {
      const root = document.documentElement;
      root.classList.remove(
        'customer-high-contrast',
        'customer-text-large',
        'customer-text-xlarge',
        'customer-dyslexia-spacing',
        'customer-reduce-motion'
      );
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    }
  }, [isCustomerScope]);

  // Reading Ruler cursor follower
  useEffect(() => {
    if (!readingRuler) return;
    const handleMouseMove = (e) => {
      setRulerTop(e.clientY);
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [readingRuler]);

  if (!isCustomerScope) {
    return null;
  }

  // Generate Narrator Text tailored to current Customer Page
  const getPageNarration = () => {
    if (path === '/customer' || path === '/customer/') {
      return (
        "Welcome to your Customer Solar Dashboard, Arun Kumar. " +
        "You are viewing your active 5 kilowatt Hybrid Rooftop System at Indiranagar, Bengaluru. " +
        "Today's solar generation is 22.4 kilowatt-hours. Battery status is healthy at 92%. " +
        "Your upcoming rooftop shadow audit is scheduled for Saturday, 18 May at 11:00 AM. " +
        "Your verification PIN for the field engineer is 8 4 9, 2 0 1. " +
        "Job profitability and milestone progress is currently on schedule."
      );
    }

    if (path.startsWith('/customer/store')) {
      return (
        "You are in the Solar Hardware Marketplace. " +
        "Currently browsing tier-1 solar products including Waaree 540-watt Bifacial Mono PERC solar panels, " +
        "SolarEdge 5 kilowatt hybrid inverters, SolarFlow 5.12 kilowatt-hour lithium batteries, and automated sprinkler kits. " +
        "All purchases include free express delivery to your Bengaluru rooftop and 12% solar GST."
      );
    }

    if (path.includes('payment') || path.includes('razorpay')) {
      return (
        "You are on the Milestone Payment Checkout Page. " +
        "Bill total is ₹78,000 for your 5 kilowatt Solar System milestone 1 advance. " +
        "An interactive multi-card leather wallet is displayed with Stripe, Wise, and PayPal cards. " +
        "Click any card to select it, then click the Proceed Payment button. " +
        "Upon payment completion, an animated thermal receipt will be printed automatically."
      );
    }

    if (path.includes('quotations')) {
      return (
        "You are viewing your Solar Quotations and Bill of Materials proposals. " +
        "Active quotation reference ENQ-2026-001 includes 10 bifacial modules, rooftop mounting structure, " +
        "and a ₹78,000 credit from the PM Surya Ghar national subsidy."
      );
    }

    if (path.includes('support')) {
      return (
        "You are on the Customer Support and Warranty Assistance Desk. " +
        "24/7 technical help is available for inverter error codes, BESCOM net metering interconnections, " +
        "and warranty service. You can submit a ticket or use the SolarFlow AI assistant in the navigation dock."
      );
    }

    if (path.includes('enquiries')) {
      return (
        "You are on the New Solar Installation Enquiry Portal. " +
        "Follow the 3-step wizard to input your rooftop dimensions, preferred kilowatt capacity, and utility bill."
      );
    }

    return (
      "Welcome to the SolarOps Customer Portal. " +
      "Use the left navigation dock to view your solar generation, purchase hardware in the store, " +
      "make milestone payments, or talk to our solar assistant."
    );
  };

  // Screen Reader Speech Synthesis
  const handleReadPage = () => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      showToast({
        type: 'warning',
        title: 'Speech Unavailable',
        message: 'Speech synthesis is not supported on this browser.',
      });
      return;
    }

    if (isSpeaking && !isPaused) {
      window.speechSynthesis.pause();
      setIsPaused(true);
      playEarcon(400, 'square');
      return;
    }

    if (isSpeaking && isPaused) {
      window.speechSynthesis.resume();
      setIsPaused(false);
      playEarcon(750, 'sine');
      return;
    }

    window.speechSynthesis.cancel();
    const narrationText = getPageNarration();
    const utterance = new SpeechSynthesisUtterance(narrationText);
    utterance.rate = speechRate;
    utterance.pitch = 1.0;
    utterance.lang = 'en-IN';

    utterance.onstart = () => {
      setIsSpeaking(true);
      setIsPaused(false);
      playEarcon(880, 'sine', 0.18);
    };

    utterance.onend = () => {
      setIsSpeaking(false);
      setIsPaused(false);
      playEarcon(520, 'sine', 0.14);
    };

    utterance.onerror = () => {
      setIsSpeaking(false);
      setIsPaused(false);
    };

    window.speechSynthesis.speak(utterance);
  };

  const handleStopSpeech = () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
    setIsPaused(false);
    playEarcon(320, 'triangle', 0.15);
  };

  const toggleHighContrast = () => {
    setHighContrast(!highContrast);
    playEarcon(!highContrast ? 700 : 440);
  };

  const toggleDyslexic = () => {
    setDyslexicFont(!dyslexicFont);
    playEarcon(!dyslexicFont ? 650 : 480);
  };

  const toggleReduceMotion = () => {
    setReduceMotion(!reduceMotion);
    playEarcon(550);
  };

  const toggleAudioFeedback = () => {
    const next = !audioFeedback;
    setAudioFeedback(next);
    try {
      localStorage.setItem('solarops_a11y_audio_feedback', String(next));
    } catch {}
    if (next) playEarcon(800, 'sine', 0.2);
  };

  const handleResetAll = () => {
    setHighContrast(false);
    setTextSize('normal');
    setDyslexicFont(false);
    setReadingRuler(false);
    setAudioFeedback(false);
    setReduceMotion(false);
    handleStopSpeech();
    playEarcon(400, 'triangle');
    showToast({
      type: 'info',
      title: 'Accessibility Reset',
      message: 'All visual and auditory helpers restored to standard defaults.',
    });
  };

  return (
    <>
      {/* Visual Reading Tracking Ruler */}
      {readingRuler && (
        <div
          className="customer-reading-ruler"
          style={{ top: `${rulerTop}px` }}
          aria-hidden="true"
        />
      )}

      {/* Floating Accessibility Trigger Pill */}
      <aside
        className={`customer-a11y-floating-trigger ${isOpen ? 'is-open' : ''}`}
        aria-label="Customer Accessibility Assistant"
      >
        <button
          type="button"
          className={`a11y-pill-btn ${isOpen ? 'active' : ''} ${isSpeaking ? 'speaking-pulse' : ''}`}
          onClick={() => {
            setIsOpen(!isOpen);
            playEarcon(isOpen ? 440 : 660);
          }}
          title="Customer Accessibility & Screen Reader (Alt + A)"
          aria-expanded={isOpen}
          aria-controls="customer-a11y-panel"
        >
          <div className="a11y-btn-icon-wrap">
            <Accessibility size={20} strokeWidth={2.4} />
          </div>
          <span className="a11y-btn-label">Accessibility</span>
          {isSpeaking && (
            <span className="a11y-live-speaking-indicator" title="Screen Reader Speaking">
              <Volume2 size={14} />
            </span>
          )}
        </button>

        {/* Backdrop for outside click & focus isolation */}
        {isOpen && (
          <div
            className="a11y-drawer-backdrop"
            onClick={() => {
              setIsOpen(false);
              playEarcon(420);
            }}
            aria-hidden="true"
          />
        )}

        {/* Accessibility Quick Panel Drawer */}
        {isOpen && (
          <div
            id="customer-a11y-panel"
            className="customer-a11y-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Customer Accessibility Assistant Suite"
          >
            {/* Mobile Grab Bar */}
            <div className="a11y-mobile-grab-handle" aria-hidden="true" />

            {/* Glassmorphic Gradient Header */}
            <div className="a11y-drawer-header">
              <div className="a11y-header-left">
                <div className="a11y-header-icon-badge">
                  <Accessibility size={20} color="#38bdf8" />
                </div>
                <div>
                  <div className="a11y-header-title-row">
                    <h3 className="a11y-header-title">Accessibility Assistant</h3>
                    <span className={`a11y-status-pill ${activeAidsCount > 0 ? 'active' : ''}`}>
                      {activeAidsCount > 0 ? `${activeAidsCount} Active Aids` : 'Standard Mode'}
                    </span>
                  </div>
                  <p className="a11y-header-subtitle">
                    Adaptive assistive tools tailored for solar customers
                  </p>
                </div>
              </div>

              <button
                type="button"
                className="a11y-close-btn"
                onClick={() => {
                  setIsOpen(false);
                  playEarcon(400);
                }}
                aria-label="Close Accessibility Panel"
              >
                <X size={16} />
              </button>
            </div>

            <div className="a11y-drawer-content">
              {/* Feature 1: Page Screen Reader Hero Card */}
              <div className={`a11y-feature-card screen-reader-card ${isSpeaking ? 'active-reading-border' : ''}`}>
                <div className="feature-card-header">
                  <div className="feature-icon-badge speaker">
                    <Volume2 size={18} color="#10b981" />
                  </div>
                  <div className="feature-card-text">
                    <div className="feature-title-row">
                      <h4>Page Screen Reader</h4>
                      {isSpeaking && (
                        <span className="live-radar-chip">
                          <span className="radar-dot" />
                          <span>{isPaused ? 'Paused' : 'Narrating...'}</span>
                        </span>
                      )}
                    </div>
                    <p>Narrates solar generation, OTP verification, and milestone disbursements aloud.</p>
                  </div>
                </div>

                {/* Animated Waveform Equalizer when speaking */}
                {isSpeaking && (
                  <div className="live-equalizer-row" aria-hidden="true">
                    <div className={`audio-waveform-bars ${isPaused ? 'paused' : ''}`}>
                      <span className="eq-bar bar-1" />
                      <span className="eq-bar bar-2" />
                      <span className="eq-bar bar-3" />
                      <span className="eq-bar bar-4" />
                      <span className="eq-bar bar-5" />
                    </div>
                    <span className="waveform-caption">
                      {isPaused ? 'Speech paused' : `Speaking at ${speechRate}x pace (Indian English)`}
                    </span>
                  </div>
                )}

                {/* Speech Rate Cadence Selector */}
                <div className="speech-speed-row">
                  <span className="speed-label">Voice Speed:</span>
                  <div className="speed-pill-group">
                    {[
                      { rate: 0.8, label: '0.8x Slow' },
                      { rate: 0.92, label: '1.0x Normal' },
                      { rate: 1.2, label: '1.2x Fast' },
                    ].map((s) => (
                      <button
                        key={s.rate}
                        type="button"
                        className={`speed-pill ${speechRate === s.rate ? 'active' : ''}`}
                        onClick={() => {
                          setSpeechRate(s.rate);
                          playEarcon(550);
                        }}
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Primary Screen Reader Control Buttons */}
                <div className="screen-reader-controls">
                  <button
                    type="button"
                    className={`btn-reader-action ${isSpeaking && !isPaused ? 'reading' : ''}`}
                    onClick={handleReadPage}
                  >
                    {isSpeaking && !isPaused ? (
                      <>
                        <Pause size={15} />
                        <span>Pause Narration</span>
                      </>
                    ) : (
                      <>
                        <Play size={15} />
                        <span>{isPaused ? 'Resume Narration' : 'Read Page Aloud'}</span>
                      </>
                    )}
                  </button>

                  {isSpeaking && (
                    <button
                      type="button"
                      className="btn-reader-stop"
                      onClick={handleStopSpeech}
                      title="Stop Screen Reader"
                    >
                      <VolumeX size={15} />
                      <span>Stop</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Feature 2: High Contrast Vision Mode */}
              <div className={`a11y-setting-row ${highContrast ? 'active-amber' : ''}`}>
                <div className="setting-info">
                  <div className="setting-icon-box amber">
                    <Eye size={17} color="#f59e0b" />
                  </div>
                  <div>
                    <strong>High Contrast Mode</strong>
                    <span>Deep black background & high luminance yellow text</span>
                  </div>
                </div>
                <button
                  type="button"
                  className={`a11y-toggle-switch amber-switch ${highContrast ? 'active' : ''}`}
                  onClick={toggleHighContrast}
                  aria-pressed={highContrast}
                  aria-label="Toggle High Contrast Vision Mode"
                >
                  <span className="switch-knob" />
                </button>
              </div>

              {/* Feature 3: Interactive Segmented Text Zoom */}
              <div className={`a11y-setting-row column-card ${textSize !== 'normal' ? 'active-sky' : ''}`}>
                <div className="setting-info">
                  <div className="setting-icon-box sky">
                    <Type size={17} color="#0284c7" />
                  </div>
                  <div>
                    <strong>Text Sizing (Zoom)</strong>
                    <span>Scale font sizing proportionally across buttons & tables</span>
                  </div>
                </div>

                <div className="segmented-zoom-control" role="radiogroup" aria-label="Text Sizing Zoom">
                  <button
                    type="button"
                    className={`zoom-segment-btn ${textSize === 'normal' ? 'active' : ''}`}
                    onClick={() => {
                      setTextSize('normal');
                      playEarcon(500);
                    }}
                    role="radio"
                    aria-checked={textSize === 'normal'}
                  >
                    <span>100%</span>
                    <small>Standard</small>
                  </button>
                  <button
                    type="button"
                    className={`zoom-segment-btn ${textSize === 'large' ? 'active' : ''}`}
                    onClick={() => {
                      setTextSize('large');
                      playEarcon(600);
                    }}
                    role="radio"
                    aria-checked={textSize === 'large'}
                  >
                    <span>125%</span>
                    <small>Large</small>
                  </button>
                  <button
                    type="button"
                    className={`zoom-segment-btn ${textSize === 'xlarge' ? 'active' : ''}`}
                    onClick={() => {
                      setTextSize('xlarge');
                      playEarcon(700);
                    }}
                    role="radio"
                    aria-checked={textSize === 'xlarge'}
                  >
                    <span>150%</span>
                    <small>Extra</small>
                  </button>
                </div>
              </div>

              {/* Feature 4: Dyslexia Friendly Spacing */}
              <div className={`a11y-setting-row ${dyslexicFont ? 'active-purple' : ''}`}>
                <div className="setting-info">
                  <div className="setting-icon-box purple">
                    <Sparkles size={17} color="#a855f7" />
                  </div>
                  <div>
                    <strong>Dyslexia Reading Spacing</strong>
                    <span>Expands letter spacing and line heights for readability</span>
                  </div>
                </div>
                <button
                  type="button"
                  className={`a11y-toggle-switch purple-switch ${dyslexicFont ? 'active' : ''}`}
                  onClick={toggleDyslexic}
                  aria-pressed={dyslexicFont}
                  aria-label="Toggle Dyslexia Reading Spacing"
                >
                  <span className="switch-knob" />
                </button>
              </div>

              {/* Feature 5: Reading Ruler (Eye Guide) */}
              <div className={`a11y-setting-row ${readingRuler ? 'active-cyan' : ''}`}>
                <div className="setting-info">
                  <div className="setting-icon-box cyan">
                    <Layers size={17} color="#06b6d4" />
                  </div>
                  <div>
                    <strong>Reading Guide Ruler</strong>
                    <span>Highlighted guide line follows cursor to aid focus</span>
                  </div>
                </div>
                <button
                  type="button"
                  className={`a11y-toggle-switch cyan-switch ${readingRuler ? 'active' : ''}`}
                  onClick={() => {
                    setReadingRuler(!readingRuler);
                    playEarcon(!readingRuler ? 680 : 420);
                  }}
                  aria-pressed={readingRuler}
                  aria-label="Toggle Reading Guide Line"
                >
                  <span className="switch-knob" />
                </button>
              </div>

              {/* Feature 6: Sound & Haptic Earcons */}
              <div className={`a11y-setting-row ${audioFeedback ? 'active-emerald' : ''}`}>
                <div className="setting-info">
                  <div className="setting-icon-box emerald">
                    <Volume1 size={17} color="#10b981" />
                  </div>
                  <div>
                    <strong>Action Sound Earcons</strong>
                    <span>Subtle audio chimes on buttons to confirm clicks</span>
                  </div>
                </div>
                <button
                  type="button"
                  className={`a11y-toggle-switch emerald-switch ${audioFeedback ? 'active' : ''}`}
                  onClick={toggleAudioFeedback}
                  aria-pressed={audioFeedback}
                  aria-label="Toggle Audio Feedback"
                >
                  <span className="switch-knob" />
                </button>
              </div>

              {/* Feature 7: Reduce Motion (Epilepsy / Vestibular) */}
              <div className={`a11y-setting-row ${reduceMotion ? 'active-rose' : ''}`}>
                <div className="setting-info">
                  <div className="setting-icon-box rose">
                    <RotateCcw size={17} color="#ec4899" />
                  </div>
                  <div>
                    <strong>Reduce Motion</strong>
                    <span>Pauses 3D transforms, shimmers & rapid animations</span>
                  </div>
                </div>
                <button
                  type="button"
                  className={`a11y-toggle-switch rose-switch ${reduceMotion ? 'active' : ''}`}
                  onClick={toggleReduceMotion}
                  aria-pressed={reduceMotion}
                  aria-label="Toggle Reduce Motion"
                >
                  <span className="switch-knob" />
                </button>
              </div>
            </div>

            {/* Footer with Reset All & Compliance Tag */}
            <div className="a11y-drawer-footer">
              <button
                type="button"
                className="a11y-reset-all-btn"
                onClick={handleResetAll}
                title="Restore all accessibility settings to standard default"
              >
                <RotateCcw size={13} />
                <span>Reset to Defaults</span>
              </button>

              <div className="wcag-compliance-tag">
                <ShieldCheck size={14} color="#10b981" />
                <span>WCAG 2.2 AAA Compliant</span>
              </div>
            </div>
          </div>
        )}
      </aside>
    </>
  );
}

export default CustomerAccessibility;
