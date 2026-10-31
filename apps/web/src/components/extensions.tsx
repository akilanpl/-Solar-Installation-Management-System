"use client";

import { useCallback, useEffect, useId, useState } from "react";

import { Button, Card, ErrorState, LoadingState, PageHeader, TextField } from "@/components/ui";
import { api, ApiError, type CurrentUser } from "@/lib/api";
import { PASSKEYS_ENABLED, authenticateWithPasskey } from "@/lib/webauthn";

interface Eligibility {
  eligible: boolean;
  reason: string | null;
  serial_number: string | null;
  coverage_id: string | null;
  coverage_status: string | null;
  coverage_ends_at: string | null;
  policy_code: string | null;
  policy_version: number | null;
  extension_days: number | null;
  price_minor: number | null;
  currency: string | null;
  payment_required: boolean | null;
}

interface Extension {
  id: string;
  status: string;
  extension_days: number;
  price_minor: number;
  currency: string;
  original_ends_at: string;
  new_ends_at: string | null;
  payment_reference: string | null;
  decision_note: string | null;
  created_at: string;
}

interface Terms {
  id: string;
  policy_id: string;
  version: number;
  extension_days: number;
  price_minor: number;
  currency: string;
  window_days: number;
  eligible_categories: string[];
  max_extensions: number;
  requires_approval: boolean;
  is_active: boolean;
}

function money(minor: number, currency: string | null) {
  return `${((minor ?? 0) / 100).toFixed(2)} ${currency ?? "INR"}`;
}

export function CustomerExtensions() {
  const [serial, setSerial] = useState("");
  const [eligibility, setEligibility] = useState<Eligibility | null>(null);
  const [extensions, setExtensions] = useState<Extension[]>([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      setExtensions(await api<Extension[]>("/api/v1/warranty/extensions/requests"));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load extensions.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  async function check(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setChecking(true);
    setError(null);
    setNotice(null);
    try {
      const result = await api<Eligibility>(
        `/api/v1/warranty/extensions/eligibility?serial_number=${encodeURIComponent(serial.trim())}`,
      );
      setEligibility(result);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Eligibility check failed.");
    } finally {
      setChecking(false);
    }
  }

  async function request() {
    if (!eligibility?.coverage_id) return;
    setError(null);
    setNotice(null);
    try {
      await api("/api/v1/warranty/extensions/requests", {
        method: "POST",
        body: JSON.stringify({
          coverage_id: eligibility.coverage_id,
          idempotency_key: `web-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`,
        }),
      });
      setNotice("Extension requested. Support reviews it before anything is charged or changed.");
      await reload();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The request failed.");
    }
  }

  if (loading) return <LoadingState label="Loading warranty extensions" />;

  return (
    <div>
      <PageHeader
        title="Warranty extensions"
        description="Extend cover on equipment you own. Extensions keep your original manufacturer terms; nothing activates until every approval and payment check passes."
      />
      {error ? <ErrorState message={error} /> : null}
      {notice ? (
        <p role="status" className="mt-3 rounded-md border border-moss-200 bg-moss-50 px-3 py-2 text-sm">
          {notice}
        </p>
      ) : null}

      <Card className="mt-4">
        <h2 className="text-base font-semibold">Check eligible equipment</h2>
        <form className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={check}>
          <div className="flex-1">
            <TextField
              label="Equipment serial number"
              name="serial"
              value={serial}
              onChange={(event) => setSerial(event.target.value)}
              required
              hint="The exact serial from your installation record."
            />
          </div>
          <Button type="submit" disabled={checking}>
            {checking ? "Checking…" : "Check eligibility"}
          </Button>
        </form>
        {eligibility ? (
          <div className="mt-3 rounded-md border border-moss-200 px-3 py-2 text-sm" aria-live="polite">
            {eligibility.eligible ? (
              <>
                <p>
                  <strong>{eligibility.serial_number}</strong> can be extended by{" "}
                  {eligibility.extension_days} days for{" "}
                  {money(eligibility.price_minor ?? 0, eligibility.currency)}.
                </p>
                <p className="mt-1 text-moss-900/80">
                  Policy {eligibility.policy_code} (version {eligibility.policy_version}) · current
                  cover ends {eligibility.coverage_ends_at?.slice(0, 10)} ·{" "}
                  {eligibility.payment_required ? "payment required" : "no payment required"}.
                </p>
                <div className="mt-2">
                  <Button onClick={request}>Request extension</Button>
                </div>
              </>
            ) : (
              <p>{eligibility.reason ?? "This unit cannot be extended."}</p>
            )}
          </div>
        ) : null}
      </Card>

      <Card className="mt-4">
        <h2 className="text-base font-semibold">Your requests</h2>
        {extensions.length === 0 ? (
          <p className="mt-2 text-sm text-moss-900/80">No extension requests yet.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {extensions.map((item) => (
              <li key={item.id} className="rounded-md border border-moss-200 px-3 py-2 text-sm">
                <strong>{item.status.replace(/_/g, " ")}</strong> · {item.extension_days} days ·{" "}
                {money(item.price_minor, item.currency)}
                {item.new_ends_at ? <span> · new end {item.new_ends_at.slice(0, 10)}</span> : null}
                {item.decision_note ? (
                  <span className="block text-moss-900/80">Note: {item.decision_note}</span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

async function stepUpGrant(): Promise<string> {
  const started = await api<{ ticket: string; methods: string[] }>("/api/v1/auth/step-up/start", {
    method: "POST",
    body: JSON.stringify({}),
  });
  if (started.methods.includes("totp")) {
    const code = window.prompt("Enter the code from your authenticator app to reauthenticate.");
    if (!code) throw new Error("Reauthentication was cancelled.");
    const verified = await api<{ grant: string }>("/api/v1/auth/step-up/verify-totp", {
      method: "POST",
      body: JSON.stringify({ ticket: started.ticket, code: code.trim() }),
    });
    return verified.grant;
  }
  if (PASSKEYS_ENABLED && started.methods.includes("passkey")) {
    const created = await api<{ options: Record<string, unknown> }>(
      "/api/v1/auth/passkeys/authentication/options",
      { method: "POST", body: JSON.stringify({}) },
    );
    const credential = await authenticateWithPasskey(created.options);
    const verified = await api<{ grant: string }>("/api/v1/auth/step-up/verify-passkey", {
      method: "POST",
      body: JSON.stringify({ ticket: started.ticket, credential }),
    });
    return verified.grant;
  }
  throw new Error("No usable second factor. Enroll one on the Security page first.");
}

export function SupportExtensions({ user }: { user: CurrentUser }) {
  const [extensions, setExtensions] = useState<Extension[]>([]);
  const [terms, setTerms] = useState<Terms[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const [requests, allTerms] = await Promise.all([
        api<Extension[]>("/api/v1/warranty/extensions/requests"),
        api<Terms[]>("/api/v1/warranty/extensions/terms"),
      ]);
      setExtensions(requests);
      setTerms(allTerms);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load extensions.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  async function act(
    id: string,
    action: "approve" | "reject",
    body: Record<string, unknown>,
  ) {
    setError(null);
    setNotice(null);
    try {
      const grant = await stepUpGrant();
      await api(`/api/v1/warranty/extensions/requests/${id}/${action}`, {
        method: "POST",
        headers: { "X-Strong-Auth": grant },
        body: JSON.stringify(body),
      });
      setNotice(`Extension ${action}d.`);
      await reload();
    } catch (caught) {
      setError(
        caught instanceof ApiError || caught instanceof Error
          ? caught.message
          : "The action failed.",
      );
    }
  }

  async function decide(id: string, approve: boolean) {
    const note = window.prompt(approve ? "Approval note (optional)." : "Rejection reason (required).");
    if (!approve && !note) {
      setError("A rejection needs a short note.");
      return;
    }
    await act(id, approve ? "approve" : "reject", approve ? { note: note ?? null } : { note });
  }

  if (loading) return <LoadingState label="Loading extension reviews" />;

  return (
    <div>
      <PageHeader
        title="Warranty extension reviews"
        description={`Signed in as ${user.email}. Approvals and payment verification need a fresh second-factor check every time.`}
      />
      {error ? <ErrorState message={error} /> : null}
      {notice ? (
        <p role="status" className="mt-3 rounded-md border border-moss-200 bg-moss-50 px-3 py-2 text-sm">
          {notice}
        </p>
      ) : null}
      <Card className="mt-4">
        <h2 className="text-base font-semibold">Requests</h2>
        {extensions.length === 0 ? (
          <p className="mt-2 text-sm text-moss-900/80">No extension requests.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {extensions.map((item) => (
              <li key={item.id} className="rounded-md border border-moss-200 px-3 py-2 text-sm">
                <strong>{item.status.replace(/_/g, " ")}</strong> · {item.extension_days} days ·{" "}
                {money(item.price_minor, item.currency)}
                {item.payment_reference ? <span> · recorded reference {item.payment_reference}</span> : null}
                <span className="mt-2 flex flex-wrap gap-2">
                  {(item.status === "pending_approval" || item.status === "requested") && (
                    <>
                      <Button onClick={() => decide(item.id, true)}>Approve</Button>
                      <Button variant="secondary" onClick={() => decide(item.id, false)}>
                        Reject
                      </Button>
                    </>
                  )}
                  {item.status === "pending_payment" && (
                    <ExtensionSettlementUnavailable />
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card className="mt-4">
        <h2 className="text-base font-semibold">Extension terms</h2>
        {terms.length === 0 ? (
          <p className="mt-2 text-sm text-moss-900/80">
            No extension terms yet. Terms are managed through the API with a step-up check.
          </p>
        ) : (
          <ul className="mt-2 space-y-2">
            {terms.map((term) => (
              <li key={term.id} className="rounded-md border border-moss-200 px-3 py-2 text-sm">
                Version {term.version} · {term.extension_days} days ·{" "}
                {money(term.price_minor, term.currency)} · window {term.window_days} days ·{" "}
                {term.requires_approval ? "needs approval" : "auto-approves"} ·{" "}
                {term.is_active ? "active" : "superseded"}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

export function ExtensionSettlementUnavailable() {
  const explanation = useId();
  return <span>
    <Button disabled aria-describedby={explanation}>Verify payment &amp; activate</Button>
    <span id={explanation} className="mt-1 block text-sm text-moss-900/80">
      Settlement verification is unavailable. This request remains pending; a payment reference alone cannot activate coverage.
    </span>
  </span>;
}
