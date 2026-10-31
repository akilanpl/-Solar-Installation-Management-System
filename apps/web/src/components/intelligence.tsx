"use client";
import { useCallback, useEffect, useState } from "react";
import type { components } from "@/generated/schema";
import { api } from "@/lib/api";
import { snapshotFreshnessLabel } from "@/lib/intelligence";
import { Button, Card, ErrorState, LoadingState, PageHeader, StatusBadge, TextField } from "@/components/ui";

type Snapshot = components["schemas"]["SnapshotResponse"];
type Assist = components["schemas"]["AssistResponse"];
type Metrics = components["schemas"]["CacheMetricsResponse"];

function useGet<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    if (!path) return;
    setError(null);
    api<T>(path).then(setData).catch((e: Error) => setError(e.message));
  }, [path]);
  useEffect(load, [load]);
  return { data, error, load, setData };
}

function Definition({ term, children }: { term: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap gap-x-2 text-sm">
      <dt className="font-medium text-ink">{term}</dt>
      <dd>{children}</dd>
    </div>
  );
}

export function SupportIntelligence() {
  const [customerId, setCustomerId] = useState("");
  const [snapshotPath, setSnapshotPath] = useState<string | null>(null);
  const snapshot = useGet<Snapshot>(snapshotPath);
  const metrics = useGet<Metrics>("/api/v1/cache/metrics");

  const [complaint, setComplaint] = useState("");
  const [ticketId, setTicketId] = useState("");
  const [assist, setAssist] = useState<Assist | null>(null);
  const [assistError, setAssistError] = useState<string | null>(null);
  const [editedSummary, setEditedSummary] = useState("");
  const [busy, setBusy] = useState(false);

  async function createAssist() {
    setBusy(true);
    setAssistError(null);
    try {
      const body = await api<Assist>("/api/v1/ai-assists", {
        method: "POST",
        body: JSON.stringify({
          complaint_text: complaint,
          ticket_id: ticketId.trim() || null,
          mode: "auto",
        }),
      });
      setAssist(body);
      setEditedSummary("");
    } catch (e) {
      setAssistError(e instanceof Error ? e.message : "Assistance failed.");
    } finally {
      setBusy(false);
    }
  }

  async function decideAssist(decision: "confirmed" | "discarded") {
    if (!assist) return;
    setBusy(true);
    setAssistError(null);
    try {
      const body = await api<Assist>(`/api/v1/ai-assists/${assist.id}/confirm`, {
        method: "POST",
        body: JSON.stringify({
          decision,
          edited_summary: editedSummary.trim() || null,
          note: "Reviewed in the support workspace.",
        }),
      });
      setAssist(body);
    } catch (e) {
      setAssistError(e instanceof Error ? e.message : "Confirmation failed.");
    } finally {
      setBusy(false);
    }
  }

  const snap = snapshot.data?.snapshot as Record<string, unknown> | undefined;
  const tickets = (snap?.tickets as { open?: unknown[]; open_count?: number; total_count?: number } | undefined);

  return (
    <>
      <PageHeader
        title="Customer intelligence"
        description="Live SysCache snapshots and supervised AI ticket intake. Machine drafts never change a ticket on their own."
      />

      <Card className="mb-4">
        <h2 className="font-semibold">Customer snapshot</h2>
        <div className="mt-2 flex flex-wrap items-end gap-2">
          <div className="min-w-64 flex-1">
            <TextField label="Customer user ID" value={customerId} onChange={(e) => setCustomerId(e.target.value)} placeholder="Paste the customer user UUID" />
          </div>
          <Button onClick={() => setSnapshotPath(customerId.trim() ? `/api/v1/customer-snapshots/${customerId.trim()}` : null)} disabled={!customerId.trim()}>
            Load snapshot
          </Button>
          {snapshot.data && (
            <Button variant="secondary" onClick={snapshot.load}>
              Refresh
            </Button>
          )}
        </div>
        {snapshot.error && <div className="mt-2"><ErrorState message={snapshot.error} onRetry={snapshot.load} /></div>}
        {snapshot.data && (
          <div className="mt-3 space-y-2">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <StatusBadge status={snapshotFreshnessLabel(snapshot.data.source, snapshot.data.stale)} />
              <span>Source: {snapshot.data.source}</span>
              {snapshot.data.stale_reason && <span>Reason: {snapshot.data.stale_reason}</span>}
              <span>Built in {snapshot.data.build_ms} ms</span>
            </div>
            <dl className="space-y-1">
              <Definition term="Customer">
                {String((snap?.customer as Record<string, string> | undefined)?.full_name ?? "—")} ·{" "}
                {String((snap?.customer as Record<string, string> | undefined)?.phone ?? "—")}
              </Definition>
              <Definition term="Sites">{String(((snap?.sites as unknown[]) ?? []).length)} site(s) on record</Definition>
              <Definition term="Orders">{String(((snap?.orders as unknown[]) ?? []).length)} order(s)</Definition>
              <Definition term="Equipment">{String(((snap?.equipment as unknown[]) ?? []).length)} serialized unit(s)</Definition>
              <Definition term="Warranty">
                {((snap?.warranty as { status?: string }[] | undefined) ?? []).map((w) => w.status).join(", ") || "none"}
              </Definition>
              <Definition term="Tickets">
                {String(tickets?.open_count ?? 0)} open of {String(tickets?.total_count ?? 0)} total
              </Definition>
              <Definition term="Version">
                schema {snapshot.data.schema_version} · business {snapshot.data.business_version.slice(0, 12)}
              </Definition>
            </dl>
          </div>
        )}
      </Card>

      <Card className="mb-4">
        <h2 className="font-semibold">AI-assisted ticket intake</h2>
        <p className="mt-1 text-sm text-moss-800/80">
          Deterministic assistance unless an AI provider is configured. Every draft needs your confirmation.
        </p>
        <label className="mt-2 block text-sm" htmlFor="complaint">
          <span className="font-medium text-ink">Customer complaint (untrusted input)</span>
          <textarea
            id="complaint"
            rows={4}
            value={complaint}
            onChange={(e) => setComplaint(e.target.value)}
            className="mt-1 w-full rounded-md border border-moss-200 bg-white px-3 py-2 text-ink shadow-sm"
            placeholder="Paste the customer's own words. Original complaint is preserved on the ticket."
          />
        </label>
        <div className="mt-2 max-w-md">
          <TextField label="Ticket ID (optional)" value={ticketId} onChange={(e) => setTicketId(e.target.value)} placeholder="Link this draft to an existing ticket" />
        </div>
        <div className="mt-2">
          <Button onClick={createAssist} disabled={busy || complaint.trim().length < 3}>
            Generate supervised draft
          </Button>
        </div>
        {assistError && <div className="mt-2"><ErrorState message={assistError} /></div>}
        {assist && (
          <div className="mt-3 space-y-2 border-t border-moss-200 pt-3">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <StatusBadge status={assist.status} />
              <span>{assist.mode === "deterministic" ? "Deterministic assistance — not a model" : `Provider: ${assist.model_provider} ${assist.model_version}`}</span>
            </div>
            <p className="text-sm"><span className="font-medium">Summary:</span> {String((assist.draft as Record<string, unknown>).summary)}</p>
            <p className="text-sm"><span className="font-medium">Fault codes:</span> {((assist.draft as Record<string, string[]>).fault_codes ?? []).join(", ") || "none found"}</p>
            <p className="text-sm"><span className="font-medium">Suggested categories:</span> {((assist.draft as Record<string, string[]>).suggested_categories ?? []).join(", ")}</p>
            <p className="text-sm"><span className="font-medium">Missing information:</span> {((assist.draft as Record<string, string[]>).missing_information ?? []).join("; ") || "none"}</p>
            <p className="text-sm">
              <span className="font-medium">Recommended priority:</span> {String((assist.draft as Record<string, string>).recommended_priority)} —{" "}
              {((assist.draft as Record<string, string[]>).priority_reasons ?? []).join("; ")}
            </p>
            {assist.status === "draft" && (
              <>
                <TextField label="Operator-edited summary (optional)" value={editedSummary} onChange={(e) => setEditedSummary(e.target.value)} placeholder="Your confirmed wording" />
                <div className="flex gap-2">
                  <Button onClick={() => decideAssist("confirmed")} disabled={busy}>Confirm draft</Button>
                  <Button variant="secondary" onClick={() => decideAssist("discarded")} disabled={busy}>Discard</Button>
                </div>
              </>
            )}
          </div>
        )}
      </Card>

      <Card>
        <h2 className="font-semibold">Cache observability</h2>
        {!metrics.data && !metrics.error && <LoadingState label="Loading cache metrics" />}
        {metrics.error && <ErrorState message={metrics.error} onRetry={metrics.load} />}
        {metrics.data && (
          <p className="mt-1 text-sm">
            Snapshots: {metrics.data.snapshots} · Invalidated: {metrics.data.invalidated} · Hits: {metrics.data.hits} ·{" "}
            Misses: {metrics.data.misses} · Rebuilds: {metrics.data.rebuilds} · Fallbacks: {metrics.data.fallbacks}
          </p>
        )}
      </Card>
    </>
  );
}
