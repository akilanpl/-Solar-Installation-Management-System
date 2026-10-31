"use client";
import Link from "next/link";
import type { ReactNode } from "react";
/** Adapted from ashwin-hue Login.jsx at 74f4734. Original hero layout and video retained. */
export function AuthFrame({ children }: { children: ReactNode }) {
  return <main className="auth-page-viewport" data-frontend-source="teammate-386f356-next-integration">
      <section className="auth-hero-panel" aria-label="Hero Introduction">
        {/* Dynamic Background Video with Royal Blue Ambient Overlay */}
        <video
          className="auth-hero-video-bg"
          aria-hidden="true"
          autoPlay
          loop
          muted
          playsInline
        >
          <source src="/login-bg.mp4" type="video/mp4" />
        </video>
        <div className="auth-hero-video-overlay" />

        {/* Brand Logo & Title (Top Left) */}
        <Link href="/" className="auth-hero-brand">
          <div className="auth-hero-brand-icon">
            {/* Modern Connected Node Glyph matching reference image */}
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="5" r="2.5" />
              <circle cx="6" cy="17" r="2.5" />
              <circle cx="18" cy="17" r="2.5" />
              <line x1="12" y1="7.5" x2="6" y2="14.5" />
              <line x1="12" y1="7.5" x2="18" y2="14.5" />
              <line x1="8.5" y1="17" x2="15.5" y2="17" />
            </svg>
          </div>
          <span className="auth-hero-brand-name">SolarOps</span>
        </Link>

        {/* Lower Content: Pill, Title, Subtitle, 3 Step Cards */}
        <div className="auth-hero-content">
          <div className="auth-hero-badge">
            <span>Join Us</span>
          </div>

          <h2 className="auth-hero-title">Start your Journey</h2>
          <p className="auth-hero-subtitle">
            Follow these simple steps to set up your account.
          </p>

          {/* 3 Step Process Cards Row matching reference */}
          <div className="auth-hero-steps-grid">
            {/* Step 1: Active Solid White Card */}
            <div className="auth-step-card active">
              <div className="auth-step-badge">1</div>
              <div className="auth-step-label">Register your account</div>
            </div>

            {/* Step 2: Translucent Glass Card */}
            <div className="auth-step-card inactive">
              <div className="auth-step-badge">2</div>
              <div className="auth-step-label">Set up your profile information</div>
            </div>

            {/* Step 3: Translucent Glass Card */}
            <div className="auth-step-card inactive">
              <div className="auth-step-badge">3</div>
              <div className="auth-step-label">Verify your email and get started</div>
            </div>
          </div>
        </div>
      </section>

<section className="auth-form-panel" aria-label="Account access"><div className="auth-form-inner">{children}</div></section></main>;
}
