"use client";
import { useCallback, useEffect, useState } from "react";
import type { components } from "@/generated/schema";
import { api } from "@/lib/api";
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge, TextField } from "@/components/ui";
type Job = components["schemas"]["JobResponse"];
type Evidence = components["schemas"]["JobEvidence-Input"];
type Summary = components["schemas"]["WorkSummaryResponse"];
export function Jobs({ customer = false }: { customer?: boolean }) {
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => { setError(null); api<Job[]>("/api/v1/jobs").then(setJobs).catch(e => setError(e.message)); }, []);
  useEffect(load, [load]);
  return <><PageHeader title={customer ? "Installation work" : "Assigned installation jobs"} description="Appointments and status come from recorded jobs. A code verifies the job; the customer separately reviews and acknowledges the work." />
    {error && <ErrorState message={error} onRetry={load} />}{!jobs && !error && <LoadingState />}
    {jobs?.length === 0 && <EmptyState title="No installation jobs" body="A scheduled assignment will appear when sales records it." />}
    <div className="space-y-5">{jobs?.map(job => <JobCard key={job.id} job={job} customer={customer} reload={load} />)}</div>
  </>;
}
function JobCard({ job, customer, reload }: { job: Job; customer: boolean; reload: () => void }) {
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [code, setCode] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [name, setName] = useState("");
  async function act(action: string, body?: unknown) {
    setPending(true); setError(null); setNotice(null);
    try { const result = await api<{ message?: string }>(`/api/v1/jobs/${job.id}/${action}`, { method: "POST", ...(body !== undefined ? { body: JSON.stringify(body) } : {}) }); setNotice(result.message ?? "Change saved."); reload(); }
    catch (e) { setError(e instanceof Error ? e.message : "Action failed."); } finally { setPending(false); }
  }
  return <Card><h2 className="text-lg font-semibold">{job.reference}</h2><StatusBadge status={job.status} /><p className="my-3 text-sm">Appointment: {job.slot_starts_at ? new Date(job.slot_starts_at).toLocaleString() : "Not scheduled"}</p>
    {error && <ErrorState message={error} />}
    {notice && <p role="status" className="my-3 text-sm">{notice}</p>}
    {!customer && <div className="space-y-3">
      {job.status === "scheduled" && <Button disabled={pending} onClick={() => act("en-route")}>Mark en route</Button>}
      {["scheduled", "en_route"].includes(job.status) && <Button disabled={pending} onClick={() => act("arrival")}>Record arrival now</Button>}
      {!job.otp_verified && <form onSubmit={e => { e.preventDefault(); act("customer-otp", { code }); }} className="space-y-2"><TextField label="Job verification code provided by the customer" value={code} onChange={e => setCode(e.target.value)} pattern="[0-9]{6}" required autoComplete="one-time-code" /><Button disabled={pending}>Verify code</Button></form>}
      {job.status === "on_site" && !job.signature && <EvidenceForm jobId={job.id} onSave={reload} />}
      {job.status === "on_site" && <Button disabled={pending} onClick={() => act("completion")}>Complete acknowledged work</Button>}
    </div>}
    {customer && !job.otp_verified && <Button variant="secondary" disabled={pending} onClick={() => act("verification-code/request")}>Request a new job verification code by email</Button>}
    {customer && job.evidence && !job.signature && <div className="space-y-3"><Button variant="secondary" disabled={pending} onClick={async () => { setError(null); try { setSummary(await api<Summary>(`/api/v1/jobs/${job.id}/work-summary`)); } catch(e) { setError(e instanceof Error ? e.message : "Could not load summary."); } }}>Review work before acknowledging</Button>
      {summary && <div className="space-y-3"><p>Recorded capacity: {summary.summary.evidence.installed_capacity_kw} kW</p><p>Work: {new Date(summary.summary.evidence.started_at).toLocaleString()} – {new Date(summary.summary.evidence.finished_at).toLocaleString()}</p><p>Open-circuit voltage: {summary.summary.evidence.test_readings.voc_v} V</p><ul>{summary.summary.files.map(file => <li key={file.key}><a className="underline" href={`/api/v1/jobs/${job.id}/uploads/${file.key}`} target="_blank" rel="noreferrer">Review uploaded photo</a></li>)}</ul>
      <TextField label="Your full name as acknowledgment" required value={name} onChange={e => setName(e.target.value)} />
      <Button disabled={pending || name.trim().length < 3} onClick={() => act("signature", { signature_ref: name.trim(), customer_confirmed: true, summary_hash: summary.summary_hash } satisfies components["schemas"]["JobSignature"])}>I reviewed this work and accept it</Button><p className="text-sm">If you do not accept the work, leave it unacknowledged and contact the company.</p></div>}
    </div>}
    {job.signature && <p className="mt-3 text-sm">Authenticated customer acknowledgment recorded.</p>}
  </Card>;
}
function EvidenceForm({ jobId, onSave }: { jobId: string; onSave: () => void }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [photo, setPhoto] = useState<File | null>(null);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!photo) return;
    const values = new FormData(event.currentTarget); setPending(true); setError(null);
    try {
      const upload = new FormData(); upload.set("upload", photo);
      const stored = await api<components["schemas"]["InstallationUploadResponse"]>(`/api/v1/jobs/${jobId}/uploads`, { method: "POST", body: upload });
      const payload: Evidence = { photo_refs: [stored.storage_key], test_readings: { voc_v: Number(values.get("voltage")) }, installed_capacity_kw: String(values.get("capacity")), started_at: new Date(String(values.get("started"))).toISOString(), finished_at: new Date(String(values.get("finished"))).toISOString() };
      await api(`/api/v1/jobs/${jobId}/evidence`, { method: "POST", body: JSON.stringify(payload) }); onSave();
    } catch(e) { setError(e instanceof Error ? e.message : "Could not save evidence."); } finally { setPending(false); }
  }
  return <form className="space-y-3 rounded-lg border border-moss-200 p-4" onSubmit={submit}><h3 className="font-semibold">Record completed installation work</h3>{error && <ErrorState message={error} />}
    <TextField label="Actual start" type="datetime-local" name="started" required /><TextField label="Actual finish" type="datetime-local" name="finished" required /><TextField label="Installed capacity (kW)" type="number" name="capacity" min="0.001" max="1000" step="0.001" required /><TextField label="Measured open-circuit voltage (V)" type="number" name="voltage" min="0.01" max="1500" step="0.01" required />
    <TextField label="Installation photo (JPEG, PNG or WebP; maximum 5 MB)" type="file" accept="image/jpeg,image/png,image/webp" required onChange={e => setPhoto(e.target.files?.[0] ?? null)} /><Button disabled={pending}>{pending ? "Uploading and saving…" : "Save work evidence"}</Button></form>;
}
