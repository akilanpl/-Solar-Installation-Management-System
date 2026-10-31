"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { components } from "@/generated/schema";
import { api } from "@/lib/api";
import { formatPaise } from "@/lib/money";
import { newIdempotencyKey } from "@/lib/tickets";
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, SelectField, StatusBadge, TextField } from "@/components/ui";

type Coverage = components["schemas"]["CoverageResponse"];
type Estimate = components["schemas"]["EstimateResponse"];
type Invoice = components["schemas"]["InvoiceResponse"];
type CreditNote = components["schemas"]["CreditNoteResponse"];
type TicketSummary = components["schemas"]["TicketSummary"];
type Decision = components["schemas"]["DecisionResponse"];
type Replacement = components["schemas"]["ReplacementResponse"];
type Inspection = components["schemas"]["InspectionResponse"];
type Policy = components["schemas"]["PolicyResponse"];
type PriceBook = components["schemas"]["PriceBookResponse"];
type TaxPolicy = components["schemas"]["TaxPolicyResponse"];

type EstimateLine = {
  kind: string; code: string; quantity: number; unit: string;
  unit_minor: number; line_total_minor: number;
  covered_minor: number; payable_minor: number; source: string;
};

type LookupCoverage = {
  coverage_id: string; status: string; starts_at: string; ends_at: string; policy_version_id: string;
} | null;

type SerialLookup = {
  serial_number: string; component_code: string; status: string;
  order_id: string | null; customer_user_id: string | null;
  coverage: LookupCoverage;
  decisions: { decision_id: string; ticket_id: string; verdict: string; reason: string }[];
};

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

function linesOf(estimate: Estimate): EstimateLine[] {
  return estimate.lines as unknown as EstimateLine[];
}

export function Equipment() {
  const { data, error, load } = useGet<Coverage[]>(`/api/v1/warranty/serials/mine`);
  return (
    <>
      <PageHeader title="My equipment" description="Every installed unit registered to you, with its live warranty coverage period." />
      {error && <ErrorState message={error} onRetry={load} />}
      {!data && !error && <LoadingState label="Loading equipment" />}
      {data?.length === 0 && <EmptyState title="No equipment" body="Installed units with warranty coverage appear here after delivery confirmation." />}
      <div className="space-y-4">
        {data?.map((row) => (
          <Card key={row.coverage_id}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-semibold">{row.serial_number ?? "—"} · {row.component_code ?? "—"}</span>
              <StatusBadge status={row.status} />
            </div>
            <p className="mt-2 text-sm">Policy {row.policy_code ?? "—"} version {row.policy_version ?? "—"}</p>
            <p className="mt-1 text-sm">Covered {new Date(row.starts_at).toLocaleDateString()} to {new Date(row.ends_at).toLocaleDateString()}</p>
          </Card>
        ))}
      </div>
    </>
  );
}

export function CustomerEstimates() {
  const tickets = useGet<{ items: TicketSummary[] }>(`/api/v1/tickets`);
  const [estimates, setEstimates] = useState<Estimate[] | null>(null);
  useEffect(() => {
    if (!tickets.data) return;
    Promise.all(
      tickets.data.items.map((ticket) =>
        api<Estimate[]>(`/api/v1/tickets/${ticket.id}/estimates`).catch(() => [] as Estimate[]),
      ),
    ).then((lists) => setEstimates(lists.flat().sort((a, b) => b.version - a.version)));
  }, [tickets.data]);
  return (
    <>
      <PageHeader title="Repair estimates" description="Versioned, itemized estimates. Accept or reject the exact version shown; a revised estimate supersedes the old one instead of changing it." />
      {tickets.error && <ErrorState message={tickets.error} onRetry={tickets.load} />}
      {!estimates && !tickets.error && <LoadingState label="Loading estimates" />}
      {estimates?.length === 0 && <EmptyState title="No estimates" body="An estimate appears here when support prices your repair." />}
      <div className="space-y-4">
        {estimates?.map((estimate) => (
          <Card key={estimate.id}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Link className="font-semibold underline" href={`/customer/estimates/${estimate.id}`}>{estimate.reference} · version {estimate.version}</Link>
              <StatusBadge status={estimate.status} />
            </div>
            <p className="mt-2 text-sm">You pay {formatPaise(estimate.customer_payable_minor)} · covered {formatPaise(estimate.covered_minor)} · valid until {new Date(estimate.valid_until).toLocaleDateString()}</p>
          </Card>
        ))}
      </div>
    </>
  );
}

function EstimateLines({ estimate }: { estimate: Estimate }) {
  return (
    <div className="mt-3 overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-moss-200">
            <th className="py-1 pr-2">Item</th>
            <th className="py-1 pr-2">Qty</th>
            <th className="py-1 pr-2">Unit</th>
            <th className="py-1 pr-2">Total</th>
            <th className="py-1 pr-2">Covered</th>
            <th className="py-1">You pay</th>
          </tr>
        </thead>
        <tbody>
          {linesOf(estimate).map((line, index) => (
            <tr key={index} className="border-b border-moss-100">
              <td className="py-1 pr-2">{line.code} ({line.kind}, {line.source})</td>
              <td className="py-1 pr-2">{line.quantity} {line.unit}</td>
              <td className="py-1 pr-2">{formatPaise(line.unit_minor)}</td>
              <td className="py-1 pr-2">{formatPaise(line.line_total_minor)}</td>
              <td className="py-1 pr-2">{formatPaise(line.covered_minor)}</td>
              <td className="py-1">{formatPaise(line.payable_minor)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-sm">Parts {formatPaise(estimate.parts_minor)} · labour {formatPaise(estimate.labour_minor)} · tax {formatPaise(estimate.tax_minor)} · <strong>you pay {formatPaise(estimate.customer_payable_minor)}</strong></p>
    </div>
  );
}

export function EstimateDetail({ estimateId }: { estimateId: string }) {
  const { data: estimate, error, load, setData } = useGet<Estimate>(`/api/v1/estimates/${estimateId}`);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [rejectNote, setRejectNote] = useState("");
  async function decide(decision: "accepted" | "rejected") {
    if (!estimate) return;
    setPending(true);
    setActionError(null);
    try {
      const updated = await api<Estimate>(`/api/v1/estimates/${estimate.id}/decision`, {
        method: "POST",
        body: JSON.stringify({ decision, estimate_version: estimate.version, note: rejectNote || undefined }),
      });
      setData(updated);
      setNotice(decision === "accepted" ? "Estimate accepted. Work is authorized for this exact version." : "Estimate rejected. No billable work is authorized.");
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Decision failed.");
    } finally {
      setPending(false);
    }
  }
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!estimate) return <LoadingState label="Loading estimate" />;
  return (
    <>
      <PageHeader title={`Estimate ${estimate.reference}`} description={`Version ${estimate.version} · status: ${estimate.status}`} />
      {actionError && <ErrorState message={actionError} />}
      {notice && <p role="status" className="my-3 text-sm">{notice}</p>}
      <Card>
        <EstimateLines estimate={estimate} />
        {estimate.status === "proposed" && (
          <div className="mt-4 space-y-3">
            <Button disabled={pending} onClick={() => decide("accepted")}>Accept this exact version</Button>
            <form onSubmit={(e) => { e.preventDefault(); decide("rejected"); }} className="space-y-2">
              <TextField label="Rejection reason (required)" value={rejectNote} onChange={(e) => setRejectNote(e.target.value)} required minLength={3} />
              <Button variant="secondary" disabled={pending || rejectNote.trim().length < 3}>Reject this version</Button>
            </form>
            <p className="text-sm">A rejected estimate never authorizes billing. Accepting authorizes work only for version {estimate.version}.</p>
          </div>
        )}
      </Card>
    </>
  );
}

export function CustomerBills() {
  const { data, error, load } = useGet<Invoice[]>(`/api/v1/service-invoices`);
  return (
    <>
      <PageHeader title="Repair bills" description="Immutable invoices derived from accepted estimates. Without a real payment provider, bills stay outstanding — a click never marks them paid." />
      {error && <ErrorState message={error} onRetry={load} />}
      {!data && !error && <LoadingState label="Loading bills" />}
      {data?.length === 0 && <EmptyState title="No bills" body="An invoice appears here after you accept an estimate." />}
      <div className="space-y-4">
        {data?.map((invoice) => (
          <Card key={invoice.id}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Link className="font-semibold underline" href={`/customer/bills/${invoice.id}`}>{invoice.reference}</Link>
              <StatusBadge status={invoice.status.replaceAll("_", " ")} />
            </div>
            <p className="mt-2 text-sm">You pay {formatPaise(invoice.customer_payable_minor)} · credited {formatPaise(invoice.credited_minor)} · covered {formatPaise(invoice.covered_minor)}</p>
          </Card>
        ))}
      </div>
    </>
  );
}

export function BillDetail({ invoiceId }: { invoiceId: string }) {
  const { data: invoice, error, load } = useGet<Invoice>(`/api/v1/service-invoices/${invoiceId}`);
  const credits = useGet<CreditNote[]>(invoice ? `/api/v1/service-invoices/${invoice.id}/credit-notes` : null);
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!invoice) return <LoadingState label="Loading bill" />;
  const pseudo: Estimate = {
    id: invoice.estimate_id, reference: invoice.reference, ticket_id: invoice.ticket_id,
    repair_job_id: invoice.estimate_id, coverage_decision_id: invoice.estimate_id,
    version: invoice.estimate_version, lines: invoice.lines, parts_minor: invoice.parts_minor,
    labour_minor: invoice.labour_minor, tax_minor: invoice.tax_minor, covered_minor: invoice.covered_minor,
    customer_payable_minor: invoice.customer_payable_minor, price_book_version: 0,
    tax_policy_version: 0, status: invoice.status, valid_until: invoice.created_at, created_at: invoice.created_at,
  };
  return (
    <>
      <PageHeader title={`Bill ${invoice.reference}`} description={`Status: ${invoice.status.replaceAll("_", " ")} · from accepted estimate version ${invoice.estimate_version}`} />
      <Card>
        <EstimateLines estimate={pseudo} />
        <p className="mt-2 text-sm">Credited so far: {formatPaise(invoice.credited_minor)}</p>
        {credits.data && credits.data.length > 0 && (
          <ul className="mt-2 list-disc pl-5 text-sm">
            {credits.data.map((note) => <li key={note.id}>{note.reference}: {formatPaise(note.amount_minor)} — {note.reason}</li>)}
          </ul>
        )}
      </Card>
    </>
  );
}

export function WarrantyWorkspace() {
  const [serial, setSerial] = useState("");
  const [lookup, setLookup] = useState<SerialLookup | null>(null);
  const [policies, setPolicies] = useState<Policy[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  useEffect(() => {
    api<Policy[]>(`/api/v1/warranty/policies`).then(setPolicies).catch(() => setPolicies([]));
  }, []);
  async function run(path: string, options?: RequestInit) {
    setPending(true);
    setError(null);
    setNotice(null);
    try {
      await api<unknown>(path, { method: "POST", ...(options ?? {}) });
      setNotice("Saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed.");
    } finally {
      setPending(false);
    }
  }
  async function doLookup(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      setLookup(await api<SerialLookup>(`/api/v1/warranty/serials/lookup?serial_number=${encodeURIComponent(serial)}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lookup failed.");
    }
  }
  return (
    <>
      <PageHeader title="Warranty intelligence" description="Look up the exact installed unit, activate coverages from confirmed deliveries, record versioned decisions, and register approved exceptions." />
      {error && <ErrorState message={error} />}
      {notice && <p role="status" className="my-3 text-sm">{notice}</p>}
      <div className="space-y-4">
        <Card>
          <h2 className="font-semibold">Serial lookup</h2>
          <form onSubmit={doLookup} className="mt-3 flex flex-wrap items-end gap-2">
            <TextField label="Serial number" value={serial} onChange={(e) => setSerial(e.target.value)} required />
            <Button disabled={pending || !serial.trim()}>Look up</Button>
          </form>
          {lookup && (
            <div className="mt-3 text-sm">
              <p>{lookup.serial_number} · {lookup.component_code} · unit status {lookup.status}</p>
              <p>Order {lookup.order_id ?? "none"} · customer {lookup.customer_user_id ?? "none"}</p>
              {lookup.coverage
                ? <p>Coverage {lookup.coverage.status}: {new Date(lookup.coverage.starts_at).toLocaleDateString()} to {new Date(lookup.coverage.ends_at).toLocaleDateString()}</p>
                : <p>No coverage record. Activate it from the confirmed delivery below.</p>}
              {lookup.decisions.length > 0 && (
                <ul className="mt-2 list-disc pl-5">
                  {lookup.decisions.map((d) => <li key={d.decision_id}>{d.verdict}: {d.reason}</li>)}
                </ul>
              )}
            </div>
          )}
        </Card>
        <Card>
          <h2 className="font-semibold">Activate coverages from a confirmed delivery</h2>
          <p className="mt-1 text-sm">Coverages start only at a valid confirmed delivery. Nothing activates without one.</p>
          <form onSubmit={(e) => { const v = new FormData(e.currentTarget); e.preventDefault(); run(`/api/v1/warranty/orders/${String(v.get("order"))}/activate-coverages`); }} className="mt-3 flex flex-wrap items-end gap-2">
            <TextField label="Order ID" name="order" required />
            <Button disabled={pending}>Activate coverages</Button>
          </form>
        </Card>
        <Card>
          <h2 className="font-semibold">Coverage decision</h2>
          <form onSubmit={(e) => {
            const v = new FormData(e.currentTarget);
            e.preventDefault();
            run(`/api/v1/warranty/coverage-decisions`, {
              headers: { "Idempotency-Key": newIdempotencyKey(), "Content-Type": "application/json" },
              body: JSON.stringify({
                ticket_id: String(v.get("ticket")),
                serial_number: String(v.get("unit")),
                fault_category: String(v.get("fault") || "") || undefined,
              }),
            });
          }} className="mt-3 space-y-2">
            <TextField label="Ticket ID" name="ticket" required />
            <TextField label="Serial number" name="unit" required />
            <TextField label="Fault category (blank reuses the triage classification)" name="fault" />
            <Button disabled={pending}>Record decision</Button>
          </form>
        </Card>
        <Card>
          <h2 className="font-semibold">Coverage exception (approved override with a recorded reason)</h2>
          <form onSubmit={(e) => {
            const v = new FormData(e.currentTarget);
            e.preventDefault();
            run(`/api/v1/warranty/exceptions`, {
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                ticket_id: String(v.get("ticket")),
                serial_number: String(v.get("unit")),
                decision: String(v.get("verdict")),
                reason: String(v.get("reason")),
                evidence_ref: String(v.get("evidence") || "") || undefined,
              }),
            });
          }} className="mt-3 space-y-2">
            <TextField label="Ticket ID" name="ticket" required />
            <TextField label="Serial number" name="unit" required />
            <SelectField label="Override decision" name="verdict" defaultValue="covered">
              <option value="covered">Covered</option>
              <option value="not_covered">Not covered</option>
            </SelectField>
            <TextField label="Reason (at least 10 characters)" name="reason" required minLength={10} />
            <TextField label="Evidence reference (optional)" name="evidence" />
            <Button variant="secondary" disabled={pending}>Record exception</Button>
          </form>
        </Card>
        <Card>
          <h2 className="font-semibold">Policies</h2>
          {!policies && <LoadingState label="Loading policies" />}
          <ul className="mt-2 space-y-1 text-sm">
            {policies?.map((policy) => <li key={policy.id}>{policy.code} · {policy.issuer} · {policy.category}</li>)}
          </ul>
        </Card>
      </div>
    </>
  );
}

export function SupportEstimates() {
  const tickets = useGet<{ items: TicketSummary[] }>(`/api/v1/tickets`);
  const [estimates, setEstimates] = useState<Estimate[] | null>(null);
  useEffect(() => {
    if (!tickets.data) return;
    Promise.all(
      tickets.data.items.map((ticket) =>
        api<Estimate[]>(`/api/v1/tickets/${ticket.id}/estimates`).catch(() => [] as Estimate[]),
      ),
    ).then((lists) => setEstimates(lists.flat()));
  }, [tickets.data]);
  return (
    <>
      <PageHeader title="Repair estimates" description="Every versioned estimate with its customer verdict. New versions supersede; accepted versions never change." />
      {tickets.error && <ErrorState message={tickets.error} onRetry={tickets.load} />}
      {!estimates && !tickets.error && <LoadingState label="Loading estimates" />}
      {estimates?.length === 0 && <EmptyState title="No estimates" body="Build one from the ticket after the coverage decision and recorded work." />}
      <div className="space-y-4">
        {estimates?.map((estimate) => (
          <Card key={estimate.id}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Link className="font-semibold underline" href={`/support/estimates/${estimate.id}`}>{estimate.reference} · v{estimate.version}</Link>
              <StatusBadge status={estimate.status} />
            </div>
            <p className="mt-2 text-sm">Ticket {estimate.ticket_id} · you pay {formatPaise(estimate.customer_payable_minor)} · covered {formatPaise(estimate.covered_minor)}</p>
          </Card>
        ))}
      </div>
      <Card className="mt-8">
        <h2 className="font-semibold">Build an estimate for a ticket</h2>
        <p className="mt-1 text-sm">Needs a final coverage decision, recorded parts and billable work time. Retrying with the same key replays the same version.</p>
        <BuildEstimateForm />
      </Card>
    </>
  );
}

export function BuildEstimateForm({ ticketId }: { ticketId?: string }) {
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  return (
    <form onSubmit={async (e) => {
      const v = new FormData(e.currentTarget);
      e.preventDefault();
      setPending(true);
      setError(null);
      try {
        const created = await api<Estimate>(`/api/v1/tickets/${String(v.get("ticket"))}/estimates`, {
          method: "POST",
          headers: { "Idempotency-Key": newIdempotencyKey() },
        });
        setNotice(`Estimate ${created.reference} version ${created.version} proposed.`);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Estimate failed.");
      } finally {
        setPending(false);
      }
    }} className="mt-3 space-y-2">
      {error && <ErrorState message={error} />}
      {notice && <p role="status" className="text-sm">{notice}</p>}
      <TextField label="Ticket ID" name="ticket" required defaultValue={ticketId ?? ""} />
      <Button disabled={pending}>Build estimate</Button>
    </form>
  );
}

export function SupportEstimateDetail({ estimateId }: { estimateId: string }) {
  const { data: estimate, error, load } = useGet<Estimate>(`/api/v1/estimates/${estimateId}`);
  const [decisions, setDecisions] = useState<Decision[] | null>(null);
  useEffect(() => {
    if (!estimate) return;
    api<Decision[]>(`/api/v1/warranty/coverage-decisions?ticket_id=${estimate.ticket_id}`).catch(() => []).then(setDecisions);
  }, [estimate]);
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!estimate) return <LoadingState label="Loading estimate" />;
  return (
    <>
      <PageHeader title={`Estimate ${estimate.reference}`} description={`Version ${estimate.version} · ${estimate.status} · book v${estimate.price_book_version} · tax v${estimate.tax_policy_version}`} />
      <Card>
        <EstimateLines estimate={estimate} />
        <p className="mt-2 text-sm">Valid until {new Date(estimate.valid_until).toLocaleString()}</p>
        {decisions && decisions.length > 0 && (
          <p className="mt-2 text-sm">Latest coverage verdict: {decisions[decisions.length - 1].verdict} — {decisions[decisions.length - 1].reason}</p>
        )}
      </Card>
      <Card>
        <h2 className="font-semibold">New version</h2>
        <p className="mt-1 text-sm">Rebuilding supersedes this version when it is still proposed or rejected. Accepted versions stay frozen.</p>
        <BuildEstimateForm ticketId={estimate.ticket_id} />
      </Card>
    </>
  );
}

export function ReplacementList({ mine, base }: { mine?: boolean; base?: string }) {
  const detailBase = base ?? "/support/replacements";
  const { data, error, load } = useGet<Replacement[]>(`/api/v1/replacements`);
  return (
    <>
      <PageHeader title={mine ? "Your replacements" : "Replacements"} description="One replacement serial per customer. Defective units return to quarantine, never silently back into stock." />
      {error && <ErrorState message={error} onRetry={load} />}
      {!data && !error && <LoadingState label="Loading replacements" />}
      {data?.length === 0 && <EmptyState title="No replacements" body="An approved replacement appears here once support authorizes it." />}
      <div className="space-y-4">
        {data?.map((row) => (
          <Card key={row.id}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              {mine ? (
                <span className="font-semibold">{row.reference} · {row.old_serial_number} → {row.new_serial_number}</span>
              ) : (
                <Link className="font-semibold underline" href={`${detailBase}/${row.id}`}>
                  {row.reference} · {row.old_serial_number} → {row.new_serial_number}
                </Link>
              )}
              <StatusBadge status={row.status.replaceAll("_", " ")} />
            </div>
            <p className="mt-2 text-sm">Manufacturer authorization: {row.manufacturer_status.replaceAll("_", " ")}</p>
          </Card>
        ))}
      </div>
      {!mine && detailBase === "/support/replacements" && (
        <Card className="mt-8">
          <h2 className="font-semibold">Request a replacement</h2>
          <p className="mt-1 text-sm">Names the defective unit and the exact replacement unit up front, so one serial can never serve two customers.</p>
          <NewReplacementForm />
        </Card>
      )}
    </>
  );
}

export function InstallReplacementForm() {
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  return (
    <form onSubmit={async (e) => {
      const v = new FormData(e.currentTarget);
      e.preventDefault();
      setError(null);
      setNotice(null);
      setPending(true);
      try {
        await api<Replacement>(`/api/v1/replacements/${String(v.get("id"))}/install`, { method: "POST" });
        setNotice("Installation confirmed. The replacement is now the linked unit and the old unit is marked returned.");
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Install failed.");
      } finally {
        setPending(false);
      }
    }} className="space-y-2">
      {error && <ErrorState message={error} />}
      {notice && <p role="status" className="text-sm">{notice}</p>}
      <TextField label="Replacement ID" name="id" required placeholder="From your repair assignment" />
      <Button disabled={pending}>Confirm installation</Button>
    </form>
  );
}

export function ReplacementDetail({ replacementId, warehouse }: { replacementId: string; warehouse?: boolean }) {
  const { data: row, error, load } = useGet<Replacement>(`/api/v1/replacements/${replacementId}`);
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  async function run(path: string, options?: RequestInit) {
    setPending(true);
    setActionError(null);
    try {
      const updated = await api<Replacement | Inspection>(path, { method: "POST", ...(options ?? {}) });
      if (updated && typeof updated === "object" && "verdict" in updated) {
        setInspection(updated as Inspection);
      }
      load();
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : "Action failed.");
    } finally {
      setPending(false);
    }
  }
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!row) return <LoadingState label="Loading replacement" />;
  return (
    <>
      <PageHeader title={`Replacement ${row.reference}`} description={`${row.old_serial_number} → ${row.new_serial_number}`} />
      {actionError && <ErrorState message={actionError} />}
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <StatusBadge status={row.status.replaceAll("_", " ")} />
          <span className="text-sm">manufacturer: {row.manufacturer_status.replaceAll("_", " ")}</span>
        </div>
        <div className="mt-4 space-y-4">
          {!warehouse && (row.status === "proposed" || row.status === "pending_manufacturer") && (
            <div className="flex flex-wrap items-end gap-2">
              <Button disabled={pending} onClick={() => run(`/api/v1/replacements/${row.id}/approve`)}>Approve replacement</Button>
            </div>
          )}
          {!warehouse && (row.status === "proposed" || row.status === "pending_manufacturer") && (
            <form onSubmit={(e) => {
              const v = new FormData(e.currentTarget);
              e.preventDefault();
              run(`/api/v1/replacements/${row.id}/manufacturer-auth`, {
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ evidence_ref: String(v.get("evidence")) }),
              });
            }} className="space-y-2">
              <TextField label="Manufacturer evidence reference" name="evidence" required minLength={3} placeholder="RMA or confirmation number" />
              <Button variant="secondary" disabled={pending}>Attach manufacturer authorization</Button>
            </form>
          )}
          {row.status === "approved" && (
            <div className="flex flex-wrap items-end gap-2">
              <Button variant="secondary" disabled={pending} onClick={() => run(`/api/v1/replacements/${row.id}/reserve`)}>Reserve unit from stock</Button>
            </div>
          )}
          {row.status === "reserved" && (
            <div className="flex flex-wrap items-end gap-2">
              <Button disabled={pending} onClick={() => run(`/api/v1/replacements/${row.id}/issue`, { headers: { "Idempotency-Key": newIdempotencyKey() } })}>Issue replacement</Button>
            </div>
          )}
          {row.status === "issued" && (
            <div className="flex flex-wrap items-end gap-2">
              <Button disabled={pending} onClick={() => run(`/api/v1/replacements/${row.id}/install`)}>Confirm installation</Button>
            </div>
          )}
          {row.status === "installed" && (
            <form onSubmit={(e) => {
              const v = new FormData(e.currentTarget);
              e.preventDefault();
              run(`/api/v1/replacements/${row.id}/inspect`, {
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ verdict: String(v.get("verdict")), note: String(v.get("note")) }),
              });
            }} className="space-y-2">
              <SelectField label="Returned-unit verdict" name="verdict" defaultValue="quarantined">
                <option value="quarantined">Quarantine for review</option>
                <option value="restocked">Fit to restock</option>
                <option value="scrapped">Scrap</option>
              </SelectField>
              <TextField label="Inspection note (at least 10 characters)" name="note" required minLength={10} />
              <Button variant="secondary" disabled={pending}>Record inspection</Button>
            </form>
          )}
          {!warehouse && !["installed", "inspected", "cancelled"].includes(row.status) && (
            <form onSubmit={(e) => {
              const v = new FormData(e.currentTarget);
              e.preventDefault();
              run(`/api/v1/replacements/${row.id}/cancel`, {
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ reason: String(v.get("reason")) }),
              });
            }} className="flex flex-wrap items-end gap-2">
              <TextField label="Cancellation reason" name="reason" required minLength={3} />
              <Button variant="secondary" disabled={pending}>Cancel replacement</Button>
            </form>
          )}
          {inspection && (
            <p className="text-sm">Recorded inspection: {inspection.verdict} — {inspection.note}</p>
          )}
        </div>
      </Card>
    </>
  );
}

export function NewReplacementForm({ ticketId }: { ticketId?: string }) {
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  return (
    <form onSubmit={async (e) => {
      const v = new FormData(e.currentTarget);
      e.preventDefault();
      setError(null);
      setPending(true);
      try {
        const created = await api<Replacement>(`/api/v1/replacements`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Idempotency-Key": newIdempotencyKey() },
          body: JSON.stringify({
            ticket_id: String(v.get("ticket")),
            old_serial_number: String(v.get("old")),
            new_serial_number: String(v.get("unit")),
          }),
        });
        setNotice(`Replacement ${created.reference} proposed.`);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Request failed.");
      } finally {
        setPending(false);
      }
    }} className="mt-3 space-y-2">
      {error && <ErrorState message={error} />}
      {notice && <p role="status" className="text-sm">{notice}</p>}
      <TextField label="Ticket ID" name="ticket" required defaultValue={ticketId ?? ""} />
      <TextField label="Defective serial number" name="old" required placeholder="SN-…" />
      <TextField label="Replacement serial number" name="unit" required placeholder="SN-…" />
      <Button disabled={pending}>Request replacement</Button>
    </form>
  );
}

export function SupportBilling() {
  const [ticketId, setTicketId] = useState("");
  const [estimates, setEstimates] = useState<Estimate[] | null>(null);
  const [invoices, setInvoices] = useState<Invoice[] | null>(null);
  const [credits, setCredits] = useState<CreditNote[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  async function loadTicket(event?: React.FormEvent) {
    event?.preventDefault();
    if (!ticketId.trim()) return;
    setError(null);
    try {
      const [e, i] = await Promise.all([
        api<Estimate[]>(`/api/v1/tickets/${ticketId}/estimates`),
        api<Invoice[]>(`/api/v1/service-invoices?ticket_id=${ticketId}`),
      ]);
      setEstimates(e);
      setInvoices(i);
      setCredits([]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Load failed.");
    }
  }
  async function issueInvoice(estimate: Estimate) {
    setError(null);
    try {
      const created = await api<Invoice>(`/api/v1/service-invoices`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": newIdempotencyKey() },
        body: JSON.stringify({ estimate_id: estimate.id }),
      });
      setNotice(`Invoice ${created.reference} raised (${created.status.replaceAll("_", " ")}). It stays outstanding until real payment arrives.`);
      loadTicket();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Invoice failed.");
    }
  }
  async function consume(invoice: Invoice) {
    setError(null);
    try {
      const updated = await api<Invoice>(`/api/v1/service-invoices/${invoice.id}/consume`, { method: "POST" });
      setNotice(`Stock consumption recorded (operation ${updated.consumption_operation_id ?? "recorded"}).`);
      loadTicket();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Consume failed.");
    }
  }
  async function issueCredit(invoice: Invoice, amount: string, reason: string) {
    setError(null);
    try {
      const created = await api<CreditNote>(`/api/v1/service-invoices/${invoice.id}/credit-notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": newIdempotencyKey() },
        body: JSON.stringify({ amount_minor: Math.round(Number(amount) * 100), reason }),
      });
      const notes = await api<CreditNote[]>(`/api/v1/service-invoices/${invoice.id}/credit-notes`);
      setCredits(notes);
      setNotice(`Credit ${created.reference} recorded. The original invoice stays immutable.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Credit failed.");
    }
  }
  return (
    <>
      <PageHeader title="Service billing" description="Issue invoices from accepted estimates, record warehouse consumption, and post credit notes against immutable originals." />
      {error && <ErrorState message={error} />}
      {notice && <p role="status" className="my-3 text-sm">{notice}</p>}
      <Card>
        <form onSubmit={loadTicket} className="flex flex-wrap items-end gap-2">
          <TextField label="Ticket ID" value={ticketId} onChange={(e) => setTicketId(e.target.value)} required />
          <Button>Load billing</Button>
        </form>
      </Card>
      {estimates && (
        <Card className="mt-4">
          <h2 className="font-semibold">Estimates ({estimates.length})</h2>
          {estimates.map((estimate) => (
            <div key={estimate.id} className="mt-2 border-t border-moss-100 pt-2 text-sm">
              <p>{estimate.reference} · v{estimate.version} · {estimate.status} · customer pays {formatPaise(estimate.customer_payable_minor)}</p>
              {estimate.status === "accepted" && (
                <Button className="mt-2" onClick={() => issueInvoice(estimate)}>Issue invoice</Button>
              )}
            </div>
          ))}
        </Card>
      )}
      {invoices && (
        <Card className="mt-4">
          <h2 className="font-semibold">Invoices ({invoices.length})</h2>
          {invoices.map((invoice) => (
            <div key={invoice.id} className="mt-2 border-t border-moss-100 pt-2 text-sm">
              <p>{invoice.reference} · {invoice.status.replaceAll("_", " ")} · customer pays {formatPaise(invoice.customer_payable_minor)} · credited {formatPaise(invoice.credited_minor)}</p>
              <p className="mt-1">Stock consumption: {invoice.consumption_operation_id ?? "not recorded"}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {!invoice.consumption_operation_id && (
                  <Button variant="secondary" onClick={() => consume(invoice)}>Record warehouse consumption</Button>
                )}
              </div>
              <p className="mt-1 text-xs">Consumption needs warehouse stock and the warehouse role; the server enforces both.</p>
              <form onSubmit={(e) => {
                const v = new FormData(e.currentTarget);
                e.preventDefault();
                issueCredit(invoice, String(v.get("amount")), String(v.get("reason")));
              }} className="mt-2 flex flex-wrap items-end gap-2">
                <TextField label="Credit amount (₹)" name="amount" required inputMode="decimal" placeholder="120.00" />
                <TextField label="Credit reason (at least 10 characters)" name="reason" required minLength={10} />
                <Button variant="secondary">Record credit</Button>
              </form>
            </div>
          ))}
          {credits && credits.length > 0 && (
            <ul className="mt-2 list-disc pl-5 text-sm">
              {credits.map((note) => <li key={note.id}>{note.reference}: {formatPaise(note.amount_minor)} — {note.reason}</li>)}
            </ul>
          )}
        </Card>
      )}
    </>
  );
}

export function PricingAdmin() {
  const books = useGet<PriceBook[]>(`/api/v1/service-price-books`);
  const taxes = useGet<TaxPolicy[]>(`/api/v1/service-tax-policies`);
  const policies = useGet<Policy[]>(`/api/v1/warranty/policies`);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  async function post(path: string, body: unknown) {
    setError(null);
    try {
      await api<unknown>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      setNotice("Saved. New versions take effect for new work; history is untouched.");
      books.load();
      taxes.load();
      policies.load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Save failed.");
    }
  }
  return (
    <>
      <PageHeader title="Warranty & pricing administration" description="Versioned policies, price books and tax rules. New versions never rewrite history." />
      {error && <ErrorState message={error} />}
      {notice && <p role="status" className="my-3 text-sm">{notice}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <h2 className="font-semibold">Warranty policies ({policies.data?.length ?? "…"})</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {policies.data?.map((policy) => <li key={policy.id}>{policy.code} · {policy.issuer} · {policy.category}</li>)}
          </ul>
          <form onSubmit={(e) => {
            const v = new FormData(e.currentTarget);
            e.preventDefault();
            post(`/api/v1/warranty/policies`, {
              code: String(v.get("code")), issuer: String(v.get("issuer")),
              category: String(v.get("category")), description: String(v.get("description")),
            });
          }} className="mt-3 space-y-2">
            <TextField label="Code" name="code" required placeholder="INV-2Y" />
            <TextField label="Issuer" name="issuer" required placeholder="Manufacturer name" />
            <TextField label="Category" name="category" required placeholder="inverter" />
            <TextField label="Description (at least 10 characters)" name="description" required minLength={10} />
            <Button>Publish policy</Button>
          </form>
        </Card>
        <Card>
          <h2 className="font-semibold">Price books ({books.data?.length ?? "…"})</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {books.data?.map((book) => <li key={book.version}>v{book.version} · {book.label} · effective {book.effective_from.slice(0, 10)}</li>)}
          </ul>
          <form onSubmit={(e) => {
            const v = new FormData(e.currentTarget);
            e.preventDefault();
            let labour: unknown = {};
            let parts: unknown = {};
            try {
              labour = JSON.parse(String(v.get("labour") || "{}"));
              parts = JSON.parse(String(v.get("parts") || "{}"));
            } catch {
              setError("Labour rates and part prices must be valid JSON objects mapping codes to paise.");
              return;
            }
            post(`/api/v1/service-price-books`, {
              label: String(v.get("label")), labour_rates: labour, part_prices: parts,
              effective_from: new Date(String(v.get("effective"))).toISOString(),
            });
          }} className="mt-3 space-y-2">
            <TextField label="Label" name="label" required placeholder="Standard 2026" />
            <label className="grid gap-1 text-sm">Labour rates (JSON: code → paise per minute)
              <textarea name="labour" rows={2} required className="rounded-none border border-moss-300 bg-sand-50 p-2 font-mono text-xs" defaultValue='{"REPAIR_LABOUR": 2000}' />
            </label>
            <label className="grid gap-1 text-sm">Part prices (JSON: SKU → paise each)
              <textarea name="parts" rows={3} required className="rounded-none border border-moss-300 bg-sand-50 p-2 font-mono text-xs" defaultValue='{"PANEL-540": 1200000}' />
            </label>
            <TextField label="Effective from" name="effective" type="datetime-local" required />
            <Button>Publish price book</Button>
          </form>
        </Card>
        <Card>
          <h2 className="font-semibold">Tax policies ({taxes.data?.length ?? "…"})</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {taxes.data?.map((tax) => <li key={tax.version}>v{tax.version} · {tax.label} · {tax.rate_bps / 100}%</li>)}
          </ul>
          <form onSubmit={(e) => {
            const v = new FormData(e.currentTarget);
            e.preventDefault();
            post(`/api/v1/service-tax-policies`, {
              label: String(v.get("label")), rate_bps: Math.round(Number(v.get("rate")) * 100),
              effective_from: new Date(String(v.get("effective"))).toISOString(),
            });
          }} className="mt-3 space-y-2">
            <TextField label="Label" name="label" required placeholder="GST 18%" />
            <TextField label="Rate (percent)" name="rate" required inputMode="decimal" placeholder="18" />
            <TextField label="Effective from" name="effective" type="datetime-local" required />
            <Button>Publish tax policy</Button>
          </form>
        </Card>
      </div>
    </>
  );
}
