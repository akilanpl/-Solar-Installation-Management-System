"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Eye, EyeOff, ArrowRight } from "lucide-react";
import type { components } from "@/generated/schema";
import { AuthFrame } from "@/components/auth-frame";
import { api, ApiError, fieldErrors } from "@/lib/api";
import { destinationAfterLogin, isRole } from "@/lib/access";
import type { CurrentUser } from "@/lib/api";
import { signInWithPassword, verifyLoginFactor } from "@/lib/login-flow";
import { PASSKEYS_ENABLED, isWebAuthnSupported } from "@/lib/webauthn";
import { loginWithPasskey } from "@/components/security";

const PORTALS = ["customer", "technician", "sales", "warehouse", "support", "admin"];
export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const params = useSearchParams();
  const signup = mode === "signup";
  const [ready, setReady] = useState(false);
  useEffect(() => {
    setReady(true);
    if (!signup) document.body.dataset.loginReady = "1";
    return () => { delete document.body.dataset.loginReady; };
  }, [signup]);
  const [portal, setPortal] = useState(PORTALS.includes(params.get("portal") ?? "") ? params.get("portal")! : "customer");
  const requestedPortal = params.get("portal");
  useEffect(() => { if (PORTALS.includes(requestedPortal ?? "")) setPortal(requestedPortal!); }, [requestedPortal]);
  const [visible, setVisible] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [mfaTicket, setMfaTicket] = useState<string | null>(null);
  function land(user: CurrentUser) {
    if (!isRole(user.role)) throw new Error("The account role is not supported.");
    window.location.assign(destinationAfterLogin(user.role, params.get("next")));
  }
  async function verifyFactor(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!mfaTicket) return;
    const code = String(new FormData(event.currentTarget).get("code") ?? "");
    setError(null); setPending(true);
    try { land(await verifyLoginFactor(mfaTicket, code)); }
    catch (e) { setError(e instanceof Error ? e.message : "Verification failed. Please retry."); }
    finally { setPending(false); }
  }
  async function passkeySignIn() {
    setError(null); setPending(true);
    try { land(await loginWithPasskey()); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Passkey sign-in failed. The authenticator may have been dismissed."); }
    finally { setPending(false); }
  }
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(null); setErrors({});
    const fields = new FormData(event.currentTarget);
    const identifier = String(fields.get("identifier") ?? "").trim();
    const password = String(fields.get("password") ?? "");
    setPending(true);
    try {
      if (signup) {
        const payload: components["schemas"]["SignupRequest"] = { full_name: String(fields.get("full_name") ?? "").trim(), email: identifier, phone: String(fields.get("phone") ?? "").trim(), password };
        await api<components["schemas"]["SignupResponse"]>("/api/v1/auth/signup", { method: "POST", body: JSON.stringify(payload) });
        window.location.assign(`/verify-email?email=${encodeURIComponent(identifier)}`);
      } else {
        const payload: components["schemas"]["LoginRequest"] = { identifier, password, account_kind: portal === "customer" ? "customer" : "employee" };
        const result = await signInWithPassword(payload);
        if (result.kind === "second_factor") { setMfaTicket(result.ticket); return; }
        land(result.user);
      }
    } catch (e) {
      if (!signup && e instanceof ApiError && e.code === "email_not_verified") { window.location.assign(`/verify-email?email=${encodeURIComponent(identifier)}`); return; }
      setErrors(fieldErrors(e)); setError(e instanceof Error ? e.message : "Could not connect. Please try again.");
    } finally { setPending(false); }
  }
  function fieldError(name: string) { return errors[name] ? <span id={`${name}-error`} className="auth-field-error">{errors[name]}</span> : null; }
  return <AuthFrame>
    <h1 className="auth-form-heading">{signup ? "Join Us" : "Sign in to SolarOps"}</h1>
    {!signup && params.get("verified") === "1" && <p role="status" className="auth-success-note">Email verified. You can sign in.</p>}
    {error && <div role="alert" className="auth-error-note">{error}</div>}
    {!mfaTicket && <form onSubmit={submit} aria-busy={!ready || pending} data-auth-ready={ready}><fieldset className="auth-fields" disabled={!ready || pending}>
      {signup && <div className="auth-field-group"><label className="auth-field-label" htmlFor="phone">Mobile</label><div className="auth-phone-box"><div className="auth-phone-prefix"><span aria-hidden="true">🇮🇳</span><span>+91</span></div><div className="auth-phone-divider" /><input id="phone" name="phone" type="tel" inputMode="numeric" autoComplete="tel-national" className="auth-phone-input" placeholder="10-digit mobile number" pattern="[6-9][0-9]{9}" maxLength={10} required aria-invalid={!!errors.phone} aria-describedby={errors.phone ? "phone-error" : undefined} /></div>{fieldError("phone")}</div>}
      <div className="auth-field-row">
        <div className="auth-field-group"><label className="auth-field-label" htmlFor={signup ? "full_name" : "portal"}>{signup ? "Full name" : "I am signing in as"}</label><div className="auth-input-box">{signup ? <input className="auth-input-control" id="full_name" name="full_name" autoComplete="name" placeholder="Your full name" minLength={2} maxLength={100} required aria-invalid={!!errors.full_name} aria-describedby={errors.full_name ? "full_name-error" : undefined} /> : <select className="auth-input-control" id="portal" value={portal} onChange={e => setPortal(e.target.value)}>{PORTALS.map(role => <option key={role} value={role}>{role[0].toUpperCase() + role.slice(1)}</option>)}</select>}</div>{fieldError("full_name")}</div>
        <div className="auth-field-group"><label className="auth-field-label" htmlFor="identifier">{signup || portal === "customer" ? "Email" : "Employee ID"}</label><div className="auth-input-box"><input className="auth-input-control" id="identifier" name="identifier" type={signup || portal === "customer" ? "email" : "text"} autoComplete={signup || portal === "customer" ? "email" : "username"} placeholder={signup || portal === "customer" ? "you@example.com" : "Your employee ID"} required aria-invalid={!!errors.email || !!errors.identifier} aria-describedby={errors.email ? "email-error" : errors.identifier ? "identifier-error" : undefined} /></div>{fieldError("email")}{fieldError("identifier")}</div>
      </div>
      <div className="auth-field-group"><label className="auth-field-label" htmlFor="password">Password</label><div className="auth-input-box"><input className="auth-input-control" id="password" name="password" type={visible ? "text" : "password"} autoComplete={signup ? "new-password" : "current-password"} placeholder="Enter your password" required minLength={signup ? 10 : undefined} maxLength={128} aria-invalid={!!errors.password} aria-describedby={signup ? "password-note" : errors.password ? "password-error" : undefined} /><button className="auth-password-toggle" type="button" aria-label={visible ? "Hide password" : "Show password"} aria-pressed={visible} onClick={() => setVisible(!visible)}>{visible ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>{signup && <p className="auth-input-note" id="password-note">At least 10 characters, including a letter and a digit.</p>}{fieldError("password")}</div>
      <button className="auth-continue-btn" type="submit" disabled={pending} aria-label={signup ? "Create account" : "Sign in"}>{pending ? "Processing…" : <><span>Continue</span><ArrowRight size={16} aria-hidden="true" /></>}</button>
    </fieldset></form>}
    {mfaTicket && <form onSubmit={verifyFactor} aria-busy={pending}>
      <p className="auth-input-note">Enter the code from your authenticator app, or a recovery code.</p>
      <fieldset className="auth-fields" disabled={pending}>
        <div className="auth-field-group"><label className="auth-field-label" htmlFor="second-factor-code">Second-factor code</label><div className="auth-input-box"><input className="auth-input-control" id="second-factor-code" name="code" autoComplete="one-time-code" required autoFocus /></div></div>
        <button className="auth-continue-btn" type="submit">{pending ? "Verifying…" : "Verify and sign in"}</button>
        <button className="auth-switch-link" type="button" onClick={() => { setMfaTicket(null); setError(null); }}>Start sign-in again</button>
      </fieldset>
    </form>}
    {!signup && ready && PASSKEYS_ENABLED && isWebAuthnSupported() && !mfaTicket && <button type="button" className="auth-google-btn" disabled={pending} onClick={passkeySignIn}>Sign in with a passkey</button>}
    <div className="auth-switch-prompt">{signup ? <>Already have an account?<Link className="auth-switch-link" href="/login">Log in</Link></> : <>New customer?<Link className="auth-switch-link" href="/signup">Create an account</Link></>}</div>
    <div className="auth-divider-row"><div className="auth-divider-line" /><span className="auth-divider-text">Or</span><div className="auth-divider-line" /></div>
    <button type="button" className="auth-google-btn" disabled aria-describedby="google-unavailable"><svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z" /><path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24z" /><path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.99 0 12s.45 3.82 1.25 5.42l4.03-3.15z" /><path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z" /></svg><span>{signup ? "Sign up with Google" : "Continue with Google"}</span></button>
    <p className="auth-input-note auth-provider-note" id="google-unavailable">Google sign-in is unavailable until an OAuth provider is configured.</p>
    <div className="auth-bypass-container"><div className="auth-bypass-header"><span className="auth-bypass-title">Workspace sign-in</span></div><div className="auth-bypass-pill-grid">{PORTALS.map(role => <Link className="auth-bypass-pill" href={`/login?portal=${role}`} key={role}>{role[0].toUpperCase() + role.slice(1)}</Link>)}</div><p className="auth-input-note">Every workspace requires valid account credentials.</p></div>
    <p className="auth-disclaimer-note">{signup ? "Registration creates a customer account. Staff accounts are provisioned by the company." : "Use your registered email or company employee credentials. Workspace access follows your account permissions."}</p>
  </AuthFrame>;
}
