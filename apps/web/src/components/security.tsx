"use client";

import { useCallback, useEffect, useState } from "react";

import { Button, Card, ErrorState, LoadingState, PageHeader, TextField } from "@/components/ui";
import { api, ApiError, type CurrentUser } from "@/lib/api";
import {
  PASSKEYS_ENABLED,
  authenticateWithPasskey,
  isWebAuthnSupported,
  registerPasskey,
} from "@/lib/webauthn";

interface Passkey {
  id: string;
  credential_id: string;
  label: string;
  backed_up: boolean;
  sign_count: number;
  created_at: string;
}

interface MfaStatus {
  totp_enrolled: boolean;
  totp_factor_id: string | null;
  passkeys_registered: boolean;
  recovery_codes_remaining: number;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="mt-4">
      <h2 className="text-base font-semibold">{title}</h2>
      <div className="mt-3 space-y-3">{children}</div>
    </Card>
  );
}

export function SecuritySettings({ user }: { user: CurrentUser }) {
  const [status, setStatus] = useState<MfaStatus | null>(null);
  const [passkeys, setPasskeys] = useState<Passkey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [enrollSecret, setEnrollSecret] = useState<string | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [mfa, keys] = await Promise.all([
        api<MfaStatus>("/api/v1/auth/mfa/status"),
        PASSKEYS_ENABLED ? api<Passkey[]>("/api/v1/auth/passkeys") : Promise.resolve([]),
      ]);
      setStatus(mfa);
      setPasskeys(keys);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load security settings.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function withPassword<T>(action: string, run: (password: string) => Promise<T>) {
    const password = window.prompt(`Enter your password to ${action}.`);
    if (!password) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await run(password);
      await refresh();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The change failed.");
    } finally {
      setBusy(false);
    }
  }

  async function onRegisterPasskey() {
    if (!isWebAuthnSupported()) {
      setError("This browser does not support passkeys.");
      return;
    }
    const label = window.prompt("Name this passkey (for example: Laptop).", "Passkey") ?? "Passkey";
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const created = await api<{ options: Record<string, unknown> }>(
        "/api/v1/auth/passkeys/registration/options",
        { method: "POST", body: JSON.stringify({}) },
      );
      const credential = await registerPasskey(created.options);
      await api("/api/v1/auth/passkeys/registration/verify", {
        method: "POST",
        body: JSON.stringify({ credential, label: label.slice(0, 80) || "Passkey" }),
      });
      setNotice("Passkey registered. It now works on the sign-in page.");
      await refresh();
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Passkey registration failed. The authenticator may have been dismissed.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function onRevokePasskey(id: string) {
    await withPassword("revoke this passkey", async (password) => {
      await api(`/api/v1/auth/passkeys/${id}/revoke`, {
        method: "POST",
        body: JSON.stringify({ password }),
      });
      setNotice("Passkey revoked. It can no longer sign in.");
    });
  }

  async function onStartTotp(password: string) {
    const started = await api<{ factor_id: string; otpauth_uri: string }>(
      "/api/v1/auth/mfa/totp/enroll/start",
      { method: "POST", body: JSON.stringify({ label: "Authenticator app", password }) },
    );
    const match = started.otpauth_uri.match(/secret=([A-Z2-7]+)/i);
    setEnrollSecret(match ? match[1].toUpperCase() : started.otpauth_uri);
    setNotice("Scan the key into your authenticator app, then enter the 6-digit code below.");
  }

  async function onConfirmTotp(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const code = String(new FormData(event.currentTarget).get("code") ?? "").trim();
    setBusy(true);
    setError(null);
    try {
      await api("/api/v1/auth/mfa/totp/enroll/confirm", {
        method: "POST",
        body: JSON.stringify({ code }),
      });
      setEnrollSecret(null);
      setNotice("Authenticator app enrolled. Password sign-in now asks for a code.");
      await refresh();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The code was not accepted.");
    } finally {
      setBusy(false);
    }
  }

  async function onRevokeTotp() {
    if (!status?.totp_factor_id) return;
    await withPassword("revoke the authenticator app", async (password) => {
      await api(`/api/v1/auth/mfa/factors/${status.totp_factor_id}/revoke`, {
        method: "POST",
        body: JSON.stringify({ password }),
      });
      setNotice("Authenticator app revoked. Password sign-in works directly again.");
    });
  }

  async function onIssueRecoveryCodes() {
    await withPassword("show new recovery codes", async (password) => {
      const issued = await api<{ codes: string[] }>("/api/v1/auth/mfa/recovery-codes", {
        method: "POST",
        body: JSON.stringify({ label: "regenerate", password }),
      });
      setRecoveryCodes(issued.codes);
      setNotice("Write these codes down. Each works once and they replace the old set.");
    });
  }

  async function onRevokeOthers() {
    setBusy(true);
    setError(null);
    try {
      const result = await api<{ revoked: number }>("/api/v1/auth/sessions/revoke-others", {
        method: "POST",
        body: JSON.stringify({}),
      });
      setNotice(`Signed out ${result.revoked} other session${result.revoked === 1 ? "" : "s"}.`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not revoke sessions.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingState label="Loading security settings" />;

  return (
    <div>
      <PageHeader
        title="Security"
        description={`Signed in as ${user.email}. Passkeys and authenticator codes protect this account without changing its role.`}
      />
      {error ? <ErrorState message={error} /> : null}
      {notice ? (
        <p role="status" className="mt-3 rounded-md border border-moss-200 bg-moss-50 px-3 py-2 text-sm">
          {notice}
        </p>
      ) : null}

      {PASSKEYS_ENABLED ? (
        <Section title="Passkeys">
          {isWebAuthnSupported() ? (
            <p className="text-sm text-moss-900/80">
              Passkeys sign you in with this device instead of a password. Registration and sign-in
              are verified by the server.
            </p>
          ) : (
            <p className="text-sm text-clay-700">
              This browser does not support passkeys. Use an authenticator app below instead.
            </p>
          )}
          {passkeys.length === 0 ? (
            <p className="text-sm text-moss-900/80">No passkeys registered yet.</p>
          ) : (
            <ul className="space-y-2">
              {passkeys.map((key) => (
                <li
                  key={key.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-moss-200 px-3 py-2"
                >
                  <span className="text-sm">
                    <strong>{key.label}</strong>
                    <span className="ml-2 text-moss-900/70">
                      {key.backed_up ? "synced passkey" : "device passkey"} · added{" "}
                      {new Date(key.created_at).toLocaleDateString()}
                    </span>
                  </span>
                  <Button variant="danger" disabled={busy} onClick={() => onRevokePasskey(key.id)}>
                    Revoke
                  </Button>
                </li>
              ))}
            </ul>
          )}
          <Button disabled={busy || !isWebAuthnSupported()} onClick={onRegisterPasskey}>
            Register a passkey
          </Button>
        </Section>
      ) : null}

      <Section title="Authenticator app">
        {status?.totp_enrolled ? (
          <p className="text-sm text-moss-900/80">
            An authenticator app is enrolled. Password sign-in asks for a code.
          </p>
        ) : (
          <p className="text-sm text-moss-900/80">
            Add a time-based code from an authenticator app as a second factor.
          </p>
        )}
        {!status?.totp_enrolled && !enrollSecret ? (
          <Button
            disabled={busy}
            onClick={() =>
              withPassword("start authenticator enrollment", (password) => onStartTotp(password))
            }
          >
            Enroll authenticator app
          </Button>
        ) : null}
        {status?.totp_enrolled ? (
          <Button variant="danger" disabled={busy} onClick={onRevokeTotp}>
            Revoke authenticator app
          </Button>
        ) : null}
        {enrollSecret ? (
          <form className="space-y-3" onSubmit={onConfirmTotp}>
            <p className="break-all rounded-md bg-moss-50 px-3 py-2 text-sm">
              Manual key: <strong>{enrollSecret}</strong>
            </p>
            <TextField
              label="6-digit code"
              name="code"
              inputMode="numeric"
              autoComplete="one-time-code"
              required
              minLength={6}
              maxLength={12}
            />
            <Button type="submit" disabled={busy}>
              Confirm enrollment
            </Button>
          </form>
        ) : null}
      </Section>

      <Section title="Recovery codes">
        <p className="text-sm text-moss-900/80">
          {status?.recovery_codes_remaining ?? 0} unused codes remaining. Keep them somewhere safe;
          each works once.
        </p>
        {recoveryCodes ? (
          <ul className="grid gap-1 rounded-md bg-moss-50 p-3 font-mono text-sm" aria-label="Recovery codes">
            {recoveryCodes.map((code) => (
              <li key={code}>{code}</li>
            ))}
          </ul>
        ) : null}
        <Button variant="secondary" disabled={busy} onClick={onIssueRecoveryCodes}>
          {(status?.recovery_codes_remaining ?? 0) > 0 ? "Replace recovery codes" : "Create recovery codes"}
        </Button>
      </Section>

      <Section title="Sessions">
        <p className="text-sm text-moss-900/80">
          Signed in as {user.email} ({user.role}). Sign out other browsers and devices here.
        </p>
        <Button variant="secondary" disabled={busy} onClick={onRevokeOthers}>
          Sign out other sessions
        </Button>
      </Section>
    </div>
  );
}

export async function loginWithPasskey(): Promise<CurrentUser> {
  const created = await api<{ options: Record<string, unknown> }>(
    "/api/v1/auth/passkeys/authentication/options",
    { method: "POST", body: JSON.stringify({}) },
  );
  const credential = await authenticateWithPasskey(created.options);
  const body = await api<{ user: CurrentUser }>("/api/v1/auth/passkeys/authentication/verify", {
    method: "POST",
    body: JSON.stringify({ credential }),
  });
  return body.user;
}
