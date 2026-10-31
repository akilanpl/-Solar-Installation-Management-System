"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { components } from "@/generated/schema";
import { api } from "@/lib/api";
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, SelectField, StatusBadge, TextField } from "@/components/ui";

type TicketDetail = components["schemas"]["TicketDetail"];
type TicketSummary = components["schemas"]["TicketSummary"];
type TicketEvent = components["schemas"]["TicketEventResponse"];
type Attachment = components["schemas"]["AttachmentResponse"];
type OrderList = components["schemas"]["OrderList"];
type RepairJob = components["schemas"]["RepairJobResponse"];

import { newIdempotencyKey, ticketStatusLabel } from "@/lib/tickets";

export function Timeline({ events }: { events: TicketEvent[] }) {
  if (events.length === 0) return <p className="text-sm">No history yet.</p>;
  return (
    <ol className="space-y-3">
      {events.map((event) => (
        <li key={event.id} className="rounded-lg border border-moss-200 bg-white p-3 text-sm">
          <p className="font-semibold">{event.action.replaceAll("_", " ")}</p>
          <p className="mt-1 text-moss-900/80">
            {[event.from_status, event.to_status].filter(Boolean).join(" → ") || "No status change"}
          </p>
          {event.reason ? <p className="mt-1">{event.reason}</p> : null}
          <p className="mt-1 text-xs text-moss-800/70">{new Date(event.created_at).toLocaleString()}</p>
        </li>
      ))}
    </ol>
  );
}

export function AttachmentSection({ ticketId, canUpload }: { ticketId: string; canUpload: boolean }) {
  const [items, setItems] = useState<Attachment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const load = useCallback(() => {
    api<Attachment[]>(`/api/v1/tickets/${ticketId}/attachments`).then(setItems).catch((e: Error) => setError(e.message));
  }, [ticketId]);
  useEffect(load, [load]);
  async function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setPending(true);
    setError(null);
    try {
      const form = new FormData();
      form.set("upload", file);
      await api(`/api/v1/tickets/${ticketId}/attachments`, { method: "POST", body: form });
      setFile(null);
      event.currentTarget.reset();
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setPending(false);
    }
  }
  return (
    <div className="space-y-3">
      <h3 className="font-semibold">Evidence</h3>
      {error && <ErrorState message={error} onRetry={load} />}
      {!items && !error && <LoadingState label="Loading evidence" />}
      {items?.length === 0 && <p className="text-sm">No files attached yet.</p>}
      <ul className="space-y-2">
        {items?.map((item) => (
          <li key={item.id} className="text-sm">
            <a className="underline" href={`/api/v1/tickets/${ticketId}/attachments/${item.id}`} target="_blank" rel="noreferrer">
              {item.original_filename}
            </a>{" "}
            <span className="text-xs text-moss-800/70">({Math.round(item.size_bytes / 1024)} KB)</span>
          </li>
        ))}
      </ul>
      {canUpload && (
        <form onSubmit={upload} className="space-y-2 rounded-lg border border-moss-200 p-4">
          <TextField label="Attach a photo or document (JPEG, PNG, WebP or PDF, max 5 MB)" type="file" accept="image/jpeg,image/png,image/webp,application/pdf" required onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <Button disabled={pending || !file}>{pending ? "Uploading…" : "Upload evidence"}</Button>
        </form>
      )}
    </div>
  );
}

export function Complaints() {
  const [tickets, setTickets] = useState<TicketSummary[] | null>(null);
  const [orders, setOrders] = useState<OrderList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const load = useCallback(() => {
    setError(null);
    api<{ items: TicketSummary[]; total: number }>(`/api/v1/tickets`)
      .then((body) => setTickets(body.items))
      .catch((e: Error) => setError(e.message));
    api<OrderList>(`/api/v1/orders`).then(setOrders).catch(() => setOrders({ items: [], total: 0, page: 1, page_size: 20 }));
  }, []);
  useEffect(load, [load]);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    setPending(true);
    setFormError(null);
    setNotice(null);
    try {
      const created = await api<TicketDetail>(`/api/v1/tickets`, {
        method: "POST",
        headers: { "Idempotency-Key": newIdempotencyKey() },
        body: JSON.stringify({
          order_id: String(values.get("order")),
          serial_number: String(values.get("serial") || "") || undefined,
          fault_code: String(values.get("fault") || "") || undefined,
          symptoms: String(values.get("symptoms")),
          customer_urgency: String(values.get("urgency")),
          contact_preference: String(values.get("contact")),
        }),
      });
      setNotice(`Complaint ${created.reference} recorded.`);
      event.currentTarget.reset();
      load();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Could not raise the complaint.");
    } finally {
      setPending(false);
    }
  }
  return (
    <>
      <PageHeader title="My complaints" description="Raise a complaint against one of your confirmed orders. Only installed equipment on that order can be named." />
      {error && <ErrorState message={error} onRetry={load} />}
      {!tickets && !error && <LoadingState label="Loading complaints" />}
      {tickets?.length === 0 && <EmptyState title="No complaints" body="Your confirmed orders appear below when you raise a complaint." />}
      <div className="space-y-4">
        {tickets?.map((ticket) => (
          <Card key={ticket.id}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Link className="font-semibold underline" href={`/customer/complaints/${ticket.id}`}>{ticket.reference}</Link>
              <StatusBadge status={ticketStatusLabel(ticket.status)} />
            </div>
            <p className="mt-2 text-sm">Your urgency: {ticket.customer_urgency}{ticket.verified_priority ? ` · Support priority: ${ticket.verified_priority}` : ""}</p>
          </Card>
        ))}
      </div>
      <Card className="mt-8">
        <h2 className="text-lg font-semibold">Raise a complaint</h2>
        {formError && <div className="mt-3"><ErrorState message={formError} /></div>}
        {notice && <p role="status" className="mt-3 text-sm">{notice}</p>}
        <form onSubmit={submit} className="mt-4 space-y-3">
          <SelectField label="Confirmed order" name="order" required defaultValue="">
            <option value="" disabled>Select the order this complaint is about</option>
            {orders?.items.map((order) => (
              <option key={order.id} value={order.id}>{order.reference}</option>
            ))}
          </SelectField>
          <TextField label="Equipment serial (optional, must be installed on that order)" name="serial" maxLength={64} />
          <TextField label="Fault code shown on the unit (optional)" name="fault" maxLength={32} />
          <TextField label="What are the symptoms? (at least 10 characters)" name="symptoms" required minLength={10} maxLength={2000} />
          <SelectField label="How urgent does this feel to you?" name="urgency" defaultValue="normal">
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </SelectField>
          <SelectField label="How should support reach you?" name="contact" defaultValue="either">
            <option value="email">Email</option>
            <option value="phone">Phone</option>
            <option value="either">Either</option>
          </SelectField>
          <Button disabled={pending}>{pending ? "Raising…" : "Raise complaint"}</Button>
        </form>
      </Card>
    </>
  );
}

export function ComplaintDetail({ ticketId }: { ticketId: string }) {
  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [events, setEvents] = useState<TicketEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const [disputeNote, setDisputeNote] = useState("");
  const load = useCallback(() => {
    setError(null);
    api<TicketDetail>(`/api/v1/tickets/${ticketId}`)
      .then(setTicket)
      .catch((e: Error) => setError(e.message));
    api<TicketEvent[]>(`/api/v1/tickets/${ticketId}/history`).then(setEvents).catch(() => setEvents([]));
  }, [ticketId]);
  useEffect(load, [load]);
  async function act(path: string, body?: unknown) {
    setPending(true);
    setActionError(null);
    setNotice(null);
    try {
      const updated = await api<TicketDetail>(`/api/v1/tickets/${ticketId}/${path}`, {
        method: "POST",
        ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      });
      setTicket(updated);
      setNotice("Saved.");
      load();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Action failed.");
    } finally {
      setPending(false);
    }
  }
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!ticket) return <LoadingState label="Loading complaint" />;
  const summary = ticket.resolution_summary as null | {
    version: number; summary: string; work_performed: string; parts_used: { component_code: string; quantity: number }[];
    technician_summary: string; diagnostics: { findings: string; root_cause?: string } | null;
  };
  return (
    <>
      <PageHeader title={`Complaint ${ticket.reference}`} description={`Status: ${ticketStatusLabel(ticket.status)}`} />
      {actionError && <ErrorState message={actionError} />}
      {notice && <p role="status" className="my-3 text-sm">{notice}</p>}
      <div className="space-y-4">
        <Card>
          <h2 className="font-semibold">What you reported</h2>
          <p className="mt-2 text-sm">{ticket.symptoms}</p>
          <p className="mt-2 text-sm">Fault code: {ticket.fault_code ?? "None"} · Serial: {ticket.serial_number ?? "None"} · Your urgency: {ticket.customer_urgency}</p>
          {ticket.warranty && <p className="mt-2 text-sm">Warranty on this order: {ticket.warranty.status}{ticket.warranty.ends_at ? ` until ${new Date(ticket.warranty.ends_at).toLocaleDateString()}` : ""}</p>}
        </Card>
        {summary && (ticket.status === "resolved" || ticket.status === "customer_confirmed" || ticket.status === "closed") && (
          <Card>
            <h2 className="font-semibold">Repair summary (version {summary.version})</h2>
            <p className="mt-2 text-sm">{summary.summary}</p>
            <p className="mt-2 text-sm">Work performed: {summary.work_performed}</p>
            {summary.diagnostics && <p className="mt-2 text-sm">Diagnostics: {summary.diagnostics.findings}{summary.diagnostics.root_cause ? ` Root cause: ${summary.diagnostics.root_cause}` : ""}</p>}
            {summary.parts_used.length > 0 && (
              <ul className="mt-2 list-disc pl-5 text-sm">
                {summary.parts_used.map((part) => <li key={part.component_code}>{part.component_code} × {part.quantity}</li>)}
              </ul>
            )}
            <p className="mt-2 text-sm">Technician note: {summary.technician_summary}</p>
            {ticket.status === "resolved" && (
              <div className="mt-4 space-y-3">
                <Button disabled={pending} onClick={() => act("confirmation", { decision: "confirmed", summary_version: summary.version })}>
                  I reviewed this repair and accept it
                </Button>
                <form onSubmit={(e) => { e.preventDefault(); act("confirmation", { decision: "disputed", summary_version: summary.version, note: disputeNote }); }} className="space-y-2">
                  <TextField label="Dispute reason (required to dispute)" value={disputeNote} onChange={(e) => setDisputeNote(e.target.value)} required minLength={3} />
                  <Button variant="secondary" disabled={pending || disputeNote.trim().length < 3}>Dispute this resolution</Button>
                </form>
                <p className="text-sm">Accepting records an immutable acknowledgment. A dispute reopens the ticket and never closes it silently.</p>
              </div>
            )}
          </Card>
        )}
        <AttachmentSection ticketId={ticketId} canUpload={!["closed", "cancelled"].includes(ticket.status)} />
        <Card>
          <h2 className="font-semibold">Status and timeline</h2>
          <div className="mt-3">{events ? <Timeline events={events} /> : <LoadingState label="Loading timeline" />}</div>
        </Card>
        {ticket.status === "waiting_customer" && (
          <Card>
            <h2 className="font-semibold">Support asked for more information</h2>
            <form onSubmit={(e) => { e.preventDefault(); act("customer-reply", { message: reply }); setReply(""); }} className="mt-3 space-y-2">
              <TextField label="Your reply" value={reply} onChange={(e) => setReply(e.target.value)} required minLength={3} />
              <Button disabled={pending || reply.trim().length < 3}>Send reply</Button>
            </form>
          </Card>
        )}
        {ticket.status === "open" && (
          <Card>
            <h2 className="font-semibold">Cancel ticket</h2>
            <p className="mt-1 text-sm">Cancellation is only possible before the repair is resolved. A reason is recorded.</p>
            <form onSubmit={(e) => { const v = new FormData(e.currentTarget); e.preventDefault(); act("cancel", { reason: String(v.get("reason")) }); }} className="mt-3 space-y-2">
              <TextField label="Cancellation reason" name="reason" required minLength={3} />
              <Button variant="danger" disabled={pending}>Cancel complaint</Button>
            </form>
          </Card>
        )}
        {(ticket.status === "resolved" || ticket.status === "customer_confirmed" || ticket.status === "closed") && (
          <Card>
            <h2 className="font-semibold">Reopen</h2>
            <p className="mt-1 text-sm">If the fault returns, reopen with a reason. The full history is preserved.</p>
            <form onSubmit={(e) => { const v = new FormData(e.currentTarget); e.preventDefault(); act("reopen", { reason: String(v.get("reason")) }); }} className="mt-3 space-y-2">
              <TextField label="Why are you reopening?" name="reason" required minLength={3} />
              <Button variant="secondary" disabled={pending}>Reopen complaint</Button>
            </form>
          </Card>
        )}
      </div>
    </>
  );
}

type StaffEntry = components["schemas"]["StaffEntry"];

const TICKET_STATUSES = ["open", "triaged", "assigned", "in_progress", "waiting_customer", "resolved", "customer_confirmed", "closed", "cancelled"];

export function SupportInbox() {
  const [tickets, setTickets] = useState<TicketSummary[] | null>(null);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    setError(null);
    const query = status ? `?status=${status}` : "";
    api<{ items: TicketSummary[]; total: number }>(`/api/v1/tickets${query}`)
      .then((body) => { setTickets(body.items); setTotal(body.total); })
      .catch((e: Error) => setError(e.message));
  }, [status]);
  useEffect(load, [load]);
  return (
    <>
      <PageHeader title="Support inbox" description="New complaints land here with the customer, order, equipment, warranty, and priority context attached. The customer-selected urgency is a feeling, not a severity classification." />
      <form className="mb-4 max-w-xs" onSubmit={(e) => e.preventDefault()}>
        <SelectField label="Filter by status" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All open work</option>
          {TICKET_STATUSES.map((value) => <option key={value} value={value}>{ticketStatusLabel(value)}</option>)}
        </SelectField>
      </form>
      {error && <ErrorState message={error} onRetry={load} />}
      {!tickets && !error && <LoadingState label="Loading inbox" />}
      {tickets?.length === 0 && <EmptyState title="Inbox clear" body="No complaints match this filter." />}
      <p className="mb-3 text-sm">{total} ticket{total === 1 ? "" : "s"}</p>
      <div className="space-y-4">
        {tickets?.map((ticket) => (
          <Card key={ticket.id}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Link className="font-semibold underline" href={`/support/tickets/${ticket.id}`}>{ticket.reference}</Link>
              <StatusBadge status={ticketStatusLabel(ticket.status)} />
            </div>
            <p className="mt-2 text-sm">
              Customer urgency: {ticket.customer_urgency}
              {ticket.verified_priority ? ` · Verified priority: ${ticket.verified_priority}` : " · Not triaged yet"}
              {ticket.category ? ` · ${ticket.category}` : ""}
              {ticket.assigned_support_user_id ? " · Owner assigned" : " · Unassigned"}
            </p>
          </Card>
        ))}
      </div>
    </>
  );
}

export function SupportTicketDetail({ ticketId }: { ticketId: string }) {
  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [events, setEvents] = useState<TicketEvent[] | null>(null);
  const [technicians, setTechnicians] = useState<StaffEntry[] | null>(null);
  const [owners, setOwners] = useState<StaffEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const load = useCallback(() => {
    setError(null);
    api<TicketDetail>(`/api/v1/tickets/${ticketId}`).then(setTicket).catch((e: Error) => setError(e.message));
    api<TicketEvent[]>(`/api/v1/tickets/${ticketId}/history`).then(setEvents).catch(() => setEvents([]));
    api<StaffEntry[]>(`/api/v1/support/staff?role=technician`).then(setTechnicians).catch(() => setTechnicians([]));
    api<StaffEntry[]>(`/api/v1/support/staff?role=support`).then(setOwners).catch(() => setOwners([]));
  }, [ticketId]);
  useEffect(load, [load]);
  async function act(path: string, body?: unknown, key?: boolean) {
    setPending(true);
    setActionError(null);
    setNotice(null);
    try {
      const updated = await api<TicketDetail>(`/api/v1/tickets/${ticketId}/${path}`, {
        method: "POST",
        ...(key ? { headers: { "Idempotency-Key": newIdempotencyKey() } } : {}),
        ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      });
      setTicket(updated);
      setNotice("Saved.");
      load();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Action failed.");
    } finally {
      setPending(false);
    }
  }
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!ticket) return <LoadingState label="Loading ticket" />;
  return (
    <>
      <PageHeader title={`Ticket ${ticket.reference}`} description={`Status: ${ticketStatusLabel(ticket.status)}`} />
      {actionError && <ErrorState message={actionError} />}
      {notice && <p role="status" className="my-3 text-sm">{notice}</p>}
      <div className="space-y-4">
        <Card>
          <h2 className="font-semibold">Complaint</h2>
          <p className="mt-2 text-sm">{ticket.symptoms}</p>
          <p className="mt-2 text-sm">Fault code: {ticket.fault_code ?? "None"} · Serial: {ticket.serial_number ?? "None"} · Order: {ticket.order_id}</p>
          <p className="mt-2 text-sm">Customer urgency: {ticket.customer_urgency} · Contact: {ticket.contact_preference}</p>
          <p className="mt-2 text-sm">Category: {ticket.category ?? "Unclassified"} · Verified priority: {ticket.verified_priority ?? "Not set"}{ticket.escalated ? " · Escalated" : ""}</p>
          {ticket.warranty && <p className="mt-2 text-sm">Warranty: {ticket.warranty.status} — {ticket.warranty.coverage_note ?? "no coverage note"}</p>}
          {!ticket.warranty && <p className="mt-2 text-sm">No warranty record on this order. Warranty billing rules belong to Phase 4B.</p>}
        </Card>
        {ticket.status === "open" && (
          <Card>
            <h2 className="font-semibold">Triage</h2>
            <p className="mt-1 text-sm">Classify the fault yourself. Never promise a repair date here: assignment depends on real technician availability below.</p>
            <form onSubmit={(e) => { const v = new FormData(e.currentTarget); e.preventDefault(); act("triage", { category: String(v.get("category")), verified_priority: String(v.get("priority")), note: String(v.get("note")) }); }} className="mt-3 space-y-2">
              <SelectField label="Category" name="category" defaultValue="inverter">
                {["inverter", "panel", "battery", "mounting", "wiring", "monitoring", "other"].map((c) => <option key={c} value={c}>{c}</option>)}
              </SelectField>
              <SelectField label="Verified priority" name="priority" defaultValue="normal">
                {["low", "normal", "high", "critical"].map((p) => <option key={p} value={p}>{p}</option>)}
              </SelectField>
              <TextField label="Triage note" name="note" required minLength={3} />
              <Button disabled={pending}>Triage ticket</Button>
            </form>
          </Card>
        )}
        {(ticket.status === "triaged" || ticket.status === "assigned") && (
          <Card>
            <h2 className="font-semibold">Assignment</h2>
            <form onSubmit={(e) => { const v = new FormData(e.currentTarget); e.preventDefault(); act("support-assignment", { support_user_id: String(v.get("owner")), note: String(v.get("note") || "") || undefined }); }} className="space-y-2">
              <SelectField label="Support owner" name="owner" required defaultValue={ticket.assigned_support_user_id ?? ""}>
                <option value="" disabled>Select the owning support agent</option>
                {owners?.map((o) => <option key={o.user_id} value={o.user_id}>{o.full_name} ({o.employee_code})</option>)}
              </SelectField>
              <TextField label="Handover note (optional)" name="note" />
              <Button variant="secondary" disabled={pending}>Assign owner</Button>
            </form>
            <form onSubmit={(e) => { const v = new FormData(e.currentTarget); e.preventDefault(); act("repair-jobs", { technician_user_id: String(v.get("technician")), scheduled_starts_at: String(v.get("slot") || "") || undefined, note: String(v.get("note") || "") || undefined }, true); }} className="mt-4 space-y-2">
              <SelectField label="Repair technician (only active technicians with fewer than 5 open jobs stay eligible)" name="technician" required defaultValue="">
                <option value="" disabled>Select a technician</option>
                {technicians?.map((t) => <option key={t.user_id} value={t.user_id}>{t.full_name} ({t.employee_code}) — {t.open_repair_jobs} open</option>)}
              </SelectField>
              <TextField label="Planned visit (optional)" name="slot" type="datetime-local" />
              <TextField label="Job note (optional)" name="note" />
              <Button disabled={pending}>Create repair job</Button>
            </form>
          </Card>
        )}
        {!["closed", "cancelled", "resolved", "customer_confirmed"].includes(ticket.status) && (
          <Card>
            <h2 className="font-semibold">Ask the customer</h2>
            <form onSubmit={(e) => { const v = new FormData(e.currentTarget); e.preventDefault(); act("request-info", { message: String(v.get("message")) }); }} className="mt-3 space-y-2">
              <TextField label="What do you need from the customer?" name="message" required minLength={3} />
              <Button variant="secondary" disabled={pending}>Request information</Button>
            </form>
          </Card>
        )}
        <Card>
          <h2 className="font-semibold">Repair jobs</h2>
          {ticket.repair_jobs.length === 0 && <p className="mt-2 text-sm">No repair job yet.</p>}
          {ticket.repair_jobs.map((job) => (
            <div key={job.id} className="mt-3 rounded-lg border border-moss-200 p-3 text-sm">
              <p className="font-semibold">{job.reference} · {job.status.replaceAll("_", " ")}</p>
              <p className="mt-1">Technician: {job.technician_user_id}</p>
              {job.arrival_at && <p>Arrived: {new Date(job.arrival_at).toLocaleString()}</p>}
              {job.diagnostics && <p>Diagnostics: {(job.diagnostics as { findings?: string }).findings}</p>}
              {job.work_performed && <p>Work: {job.work_performed}</p>}
              {job.summary && <p>Summary: {job.summary}</p>}
            </div>
          ))}
          {ticket.status === "in_progress" && (
            <form onSubmit={(e) => { const v = new FormData(e.currentTarget); e.preventDefault(); act("resolution-ready", { summary: String(v.get("summary")) }); }} className="mt-4 space-y-2">
              <TextField label="Resolution summary for the customer (only after the technician submits real work)" name="summary" required minLength={20} />
              <Button disabled={pending}>Mark resolution ready</Button>
            </form>
          )}
        </Card>
        <AttachmentSection ticketId={ticketId} canUpload={!["closed", "cancelled"].includes(ticket.status)} />
        <Card>
          <h2 className="font-semibold">Notes and escalation</h2>
          <form onSubmit={(e) => { const v = new FormData(e.currentTarget); e.preventDefault(); act("notes", { note: String(v.get("note")) }); }} className="mt-3 space-y-2">
            <TextField label="Internal note" name="note" required minLength={3} />
            <Button variant="secondary" disabled={pending}>Add note</Button>
          </form>
          {!["open", "closed", "cancelled", "resolved", "customer_confirmed"].includes(ticket.status) && (
            <form onSubmit={(e) => { const v = new FormData(e.currentTarget); e.preventDefault(); act("escalation", { reason: String(v.get("reason")), verified_priority: String(v.get("priority") || "") || undefined }); }} className="mt-4 space-y-2">
              <TextField label="Escalation reason" name="reason" required minLength={3} />
              <SelectField label="New verified priority (optional)" name="priority" defaultValue="">
                <option value="">Keep current priority</option>
                {["low", "normal", "high", "critical"].map((p) => <option key={p} value={p}>{p}</option>)}
              </SelectField>
              <Button variant="secondary" disabled={pending}>Escalate</Button>
            </form>
          )}
        </Card>
        <Card>
          <h2 className="font-semibold">History</h2>
          <div className="mt-3">{events ? <Timeline events={events} /> : <LoadingState label="Loading history" />}</div>
        </Card>
        <Card>
          <h2 className="font-semibold">Closure</h2>
          {ticket.status === "customer_confirmed" && (
            <form onSubmit={(e) => { const v = new FormData(e.currentTarget); e.preventDefault(); act("close", { reason: String(v.get("reason")) }); }} className="mt-3 space-y-2">
              <TextField label="Closure reason" name="reason" required minLength={3} />
              <Button disabled={pending}>Close ticket</Button>
            </form>
          )}
          {(ticket.status === "resolved" || ticket.status === "customer_confirmed" || ticket.status === "closed") && (
            <form onSubmit={(e) => { const v = new FormData(e.currentTarget); e.preventDefault(); act("reopen", { reason: String(v.get("reason")) }); }} className="mt-3 space-y-2">
              <TextField label="Reopen reason" name="reason" required minLength={3} />
              <Button variant="secondary" disabled={pending}>Reopen ticket</Button>
            </form>
          )}
          {(ticket.status === "open" || ticket.status === "triaged" || ticket.status === "assigned") && (
            <form onSubmit={(e) => { const v = new FormData(e.currentTarget); e.preventDefault(); act("cancel", { reason: String(v.get("reason")) }); }} className="mt-3 space-y-2">
              <TextField label="Cancellation reason" name="reason" required minLength={3} />
              <Button variant="danger" disabled={pending}>Cancel ticket</Button>
            </form>
          )}
          {ticket.status !== "customer_confirmed" && ticket.status !== "closed" && (
            <p className="mt-2 text-sm">Closure unlocks only after the owning customer confirms the exact resolution version. A disputed resolution cannot be closed.</p>
          )}
        </Card>
      </div>
    </>
  );
}

export function Repairs() {
  const [jobs, setJobs] = useState<RepairJob[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    setError(null);
    api<RepairJob[]>(`/api/v1/repair-jobs`).then(setJobs).catch((e: Error) => setError(e.message));
  }, []);
  useEffect(load, [load]);
  return (
    <>
      <PageHeader title="Repair assignments" description="Only jobs assigned to you appear here. Record arrival, diagnostics, work, and evidence on site; nothing completes without them." />
      {error && <ErrorState message={error} onRetry={load} />}
      {!jobs && !error && <LoadingState label="Loading assignments" />}
      {jobs?.length === 0 && <EmptyState title="No repair assignments" body="An assigned repair job will appear here when support records it." />}
      <div className="space-y-4">
        {jobs?.map((job) => (
          <Card key={job.id}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Link className="font-semibold underline" href={`/technician/repairs/${job.id}`}>{job.reference}</Link>
              <StatusBadge status={job.status.replaceAll("_", " ")} />
            </div>
            <p className="mt-2 text-sm">Ticket: {job.ticket_id}{job.scheduled_starts_at ? ` · Planned: ${new Date(job.scheduled_starts_at).toLocaleString()}` : " · No planned time"}</p>
          </Card>
        ))}
      </div>
    </>
  );
}

export function RepairDetail({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<RepairJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [photo, setPhoto] = useState<File | null>(null);
  const load = useCallback(() => {
    setError(null);
    api<RepairJob>(`/api/v1/repair-jobs/${jobId}`).then(setJob).catch((e: Error) => setError(e.message));
  }, [jobId]);
  useEffect(load, [load]);
  async function act(path: string, body?: unknown) {
    setPending(true);
    setActionError(null);
    setNotice(null);
    try {
      const updated = await api<RepairJob>(`/api/v1/repair-jobs/${jobId}/${path}`, {
        method: "POST",
        ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      });
      setJob(updated);
      setNotice("Saved.");
      load();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Action failed.");
    } finally {
      setPending(false);
    }
  }
  async function uploadEvidence(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!photo || !job) return;
    setPending(true);
    setActionError(null);
    try {
      const form = new FormData();
      form.set("upload", photo);
      form.append("repair_job_id", job.id);
      await api(`/api/v1/tickets/${job.ticket_id}/attachments?repair_job_id=${job.id}`, { method: "POST", body: form });
      setPhoto(null);
      event.currentTarget.reset();
      setNotice("Evidence uploaded and linked to this job.");
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setPending(false);
    }
  }
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!job) return <LoadingState label="Loading repair job" />;
  const submitted = job.status === "work_submitted";
  return (
    <>
      <PageHeader title={`Repair ${job.reference}`} description={`Status: ${job.status.replaceAll("_", " ")}`} />
      {actionError && <ErrorState message={actionError} />}
      {notice && <p role="status" className="my-3 text-sm">{notice}</p>}
      <div className="space-y-4">
        <Card>
          <h2 className="font-semibold">Site visit</h2>
          <p className="mt-2 text-sm">Arrival: {job.arrival_at ? new Date(job.arrival_at).toLocaleString() : "Not recorded"}</p>
          {job.status === "assigned" && <div className="mt-3"><Button disabled={pending} onClick={() => act("arrival")}>Record arrival now</Button></div>}
        </Card>
        {!submitted && (
          <Card>
            <h2 className="font-semibold">Diagnostics</h2>
            <form onSubmit={(e) => { const v = new FormData(e.currentTarget); e.preventDefault(); act("diagnostics", { findings: String(v.get("findings")), root_cause: String(v.get("cause") || "") || undefined }); }} className="mt-3 space-y-2">
              <TextField label="Diagnostic findings (at least 10 characters)" name="findings" required minLength={10} defaultValue={(job.diagnostics as { findings?: string } | null)?.findings ?? ""} />
              <TextField label="Root cause (optional)" name="cause" defaultValue={(job.diagnostics as { root_cause?: string } | null)?.root_cause ?? ""} />
              <Button variant="secondary" disabled={pending}>Save diagnostics</Button>
            </form>
          </Card>
        )}
        {!submitted && (
          <Card>
            <h2 className="font-semibold">Actual work</h2>
            <form onSubmit={(e) => {
              const v = new FormData(e.currentTarget);
              e.preventDefault();
              const parts = String(v.get("parts") || "").split(",").map((s) => s.trim()).filter(Boolean).map((code) => ({ component_code: code, quantity: 1 }));
              act("work", {
                work_performed: String(v.get("work")),
                work_started_at: new Date(String(v.get("started"))).toISOString(),
                work_finished_at: new Date(String(v.get("finished"))).toISOString(),
                parts_used: parts,
              });
            }} className="mt-3 space-y-2">
              <TextField label="Work performed (at least 10 characters)" name="work" required minLength={10} defaultValue={job.work_performed ?? ""} />
              <TextField label="Work started" name="started" type="datetime-local" required />
              <TextField label="Work finished" name="finished" type="datetime-local" required />
              <TextField label="Parts used: catalogue codes separated by commas (recorded, never billed here)" name="parts" hint="Example: PANEL-550. Warranty billing belongs to Phase 4B." />
              <Button variant="secondary" disabled={pending}>Save work</Button>
            </form>
          </Card>
        )}
        {!submitted && (
          <Card>
            <h2 className="font-semibold">Work evidence</h2>
            <form onSubmit={uploadEvidence} className="mt-3 space-y-2">
              <TextField label="Site photo or document (JPEG, PNG, WebP or PDF, max 5 MB)" type="file" accept="image/jpeg,image/png,image/webp,application/pdf" required onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
              <Button variant="secondary" disabled={pending || !photo}>Upload work evidence</Button>
            </form>
          </Card>
        )}
        {job.status === "in_progress" && (
          <Card>
            <h2 className="font-semibold">Submit repair summary</h2>
            <p className="mt-1 text-sm">Submission needs recorded arrival, diagnostics, and work. Support reviews it before the customer ever sees it.</p>
            <form onSubmit={(e) => { const v = new FormData(e.currentTarget); e.preventDefault(); act("submit", { summary: String(v.get("summary")) }); }} className="mt-3 space-y-2">
              <TextField label="Completion summary (at least 20 characters)" name="summary" required minLength={20} defaultValue={job.summary ?? ""} />
              <Button disabled={pending}>Submit repair summary</Button>
            </form>
          </Card>
        )}
        {submitted && <Card><p className="text-sm">Summary submitted. Support now prepares the customer review. Summary: {job.summary}</p></Card>}
        <Card>
          <h2 className="font-semibold">Ticket</h2>
          <p className="mt-2 text-sm"><Link className="underline" href={`/support/tickets/${job.ticket_id}`}>Open the support ticket</Link> (support workspace only).</p>
        </Card>
      </div>
    </>
  );
}
