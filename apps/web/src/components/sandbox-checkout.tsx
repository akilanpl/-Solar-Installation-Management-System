"use client";

import { useEffect, useRef, useState } from "react";
import type { components } from "@/generated/schema";
import { api } from "@/lib/api";
import { decimalRupeesToPaise } from "@/lib/format";

type Intent = components["schemas"]["PaymentIntentResponse"];
type Outcome = "succeeded" | "failed" | "unknown";

/** The backend remains authoritative even if a public build flag is misconfigured. */
export function SandboxCheckout({ quotationId, outstandingMinor, onChange }: {
  quotationId: string; outstandingMinor: number; onChange: () => void;
}) {
  const [enabled, setEnabled] = useState(false);
  const [intent, setIntent] = useState<Intent | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const key = useRef<string | null>(null);
  useEffect(() => {
    if (process.env.NEXT_PUBLIC_SOLAROPS_ENV !== "development") return;
    api<{ enabled: boolean }>("/api/v1/payments/sandbox/capability")
      .then(result => setEnabled(result.enabled)).catch(() => setEnabled(false));
  }, []);
  if (!enabled) return null;
  return <section className="actual-subcard" aria-label="Internal payment simulation">
    <h3>Development payment simulation</h3>
    <p>No money moves. This creates an explicitly test-only payment and a test-funded order, never a provider transaction or cash receipt. Physical fulfilment actions in this isolated demo represent software fixtures only.</p>
    {!intent && outstandingMinor > 0 && <form onSubmit={async event => {
      event.preventDefault(); setError(null); setBusy(true);
      const amount = decimalRupeesToPaise(String(new FormData(event.currentTarget).get("amount")));
      try {
        if (amount === null || amount < 1 || amount > outstandingMinor) throw new Error("Enter an amount within the outstanding quotation balance.");
        key.current ??= crypto.randomUUID();
        const result = await api<Intent>("/api/v1/payments/intents", { method: "POST", headers: { "Idempotency-Key": key.current }, body: JSON.stringify({ quotation_id: quotationId, amount_minor: amount }) });
        if (!result.is_test_only || result.provider !== "sandbox") throw new Error("The response is not an internal simulation.");
        setIntent(result);
      } catch (caught) { setError(caught instanceof Error ? caught.message : "Simulation could not start."); }
      finally { setBusy(false); }
    }}><fieldset disabled={busy}><label className="actual-field"><span>Simulated payment amount (₹)</span><input name="amount" type="number" min="0.01" max={outstandingMinor / 100} step="0.01" required /></label><button className="primary-board-btn" type="submit">Create test-only payment intent</button></fieldset></form>}
    {intent?.status === "pending" && <form onSubmit={async event => {
      event.preventDefault(); setError(null); setBusy(true);
      const data = new FormData(event.currentTarget);
      try {
        const outcome = String(data.get("outcome"));
        if (!["succeeded", "failed", "unknown"].includes(outcome) || !data.has("acknowledge")) throw new Error("Select an explicit outcome and acknowledge the simulation.");
        const result = await api<Intent>(`/api/v1/payments/intents/${intent.id}/sandbox-outcome`, { method: "POST", body: JSON.stringify({ outcome: outcome as Outcome }) });
        setIntent(result); setNotice(`Internal simulation recorded: ${result.status}. No external payment occurred.`); onChange();
      } catch (caught) { setError(caught instanceof Error ? caught.message : "Outcome could not be recorded. Retry this intent."); }
      finally { setBusy(false); }
    }}><fieldset disabled={busy}><label className="actual-field"><span>Explicit simulation outcome</span><select name="outcome" defaultValue="" required><option value="" disabled>Choose an outcome</option><option value="succeeded">Simulate approval (test-only)</option><option value="failed">Simulate failure</option><option value="unknown">Simulate unknown result</option></select></label><label><input name="acknowledge" type="checkbox" required /> I understand no money moves and no provider settlement is verified.</label><button className="primary-board-btn" type="submit">Record selected simulation outcome</button></fieldset></form>}
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
  </section>;
}
