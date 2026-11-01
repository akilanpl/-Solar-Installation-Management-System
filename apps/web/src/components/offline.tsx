"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button, Card, ErrorState, LoadingState, PageHeader, TextField } from "@/components/ui";
import { api, ApiError, type CurrentUser } from "@/lib/api";
import {
  OFFLINE_ENABLED,
  OfflineQueue,
  createIndexedDbStore,
  type QueuedOperation,
  type SyncState,
} from "@/lib/offlineQueue";

interface Assignment {
  survey_id: string;
  reference: string;
  status: string;
  field_version: number;
  enquiry_id: string;
}

interface RepairAssignment {
  repair_job_id: string;
  reference: string;
  status: string;
  field_version: number;
  ticket_id: string;
}

interface Assignments {
  retention_days: number;
  cached_until: string;
  surveys: Assignment[];
  repair_jobs: RepairAssignment[];
}

const STATE_LABEL: Record<SyncState, string> = {
  draft: "Draft",
  queued: "Queued",
  syncing: "Syncing",
  synced: "Synced",
  conflict: "Conflict",
  failed: "Failed",
  auth_required: "Sign-in required",
};

function useQueue(userId: string) {
  const queue = useMemo(
    () =>
      new OfflineQueue(createIndexedDbStore(), {
        postBatch: (operations) =>
          api<{ verdicts: { client_operation_id: string; status: string }[] }>(
            "/api/v1/offline/sync",
            { method: "POST", body: JSON.stringify({ operations }) },
          ),
      }, userId),
    [userId],
  );
  return queue;
}

export function OfflineWorkbench({ user }: { user: CurrentUser }) {
  const queue = useQueue(user.id);
  const [assignments, setAssignments] = useState<Assignments | null>(null);
  const [rows, setRows] = useState<QueuedOperation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [online, setOnline] = useState(
    typeof navigator === "undefined" ? true : navigator.onLine,
  );
  const userRef = useRef(user.id);

  const reload = useCallback(async () => {
    try {
      const [snapshot, queued] = await Promise.all([
        api<Assignments>("/api/v1/offline/assignments"),
        queue.list(),
      ]);
      setAssignments(snapshot);
      setRows(queued);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Offline data is unavailable.");
    } finally {
      setLoading(false);
    }
  }, [queue]);

  useEffect(() => {
    if (userRef.current !== user.id) {
      // Never expose one technician's drafts to the next account on this device.
      const previous = new OfflineQueue(createIndexedDbStore(), {
        postBatch: async () => ({ verdicts: [] }),
      }, userRef.current);
      previous.purgeUser().catch(() => undefined);
      userRef.current = user.id;
    }
    reload();
  }, [reload, user.id]);

  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  async function syncNow() {
    setSyncing(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await queue.syncPending();
      setRows(updated);
      const synced = updated.filter((row) => row.state === "synced").length;
      const conflicts = updated.filter((row) => row.state === "conflict").length;
      setNotice(
        `Sync finished: ${synced} applied${conflicts > 0 ? `, ${conflicts} need review` : ""}.`,
      );
      await reload();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Sync failed.");
    } finally {
      setSyncing(false);
    }
  }

  async function saveSurveyDraft(event: React.FormEvent<HTMLFormElement>, queued: boolean) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const surveyId = String(form.get("survey_id") ?? "");
    const entry = assignments?.surveys.find((item) => item.survey_id === surveyId);
    if (!entry) {
      setError("Choose an authorized survey first.");
      return;
    }
    setError(null);
    await queue.enqueue({
      op_type: "measurement",
      entity_type: "survey",
      entity_id: surveyId,
      base_field_version: entry.field_version,
      payload: {
        notes: String(form.get("notes") ?? "") || undefined,
        azimuth_deg: form.get("azimuth") ? Number(form.get("azimuth")) : undefined,
        tilt_deg: form.get("tilt") ? Number(form.get("tilt")) : undefined,
        grid_connection: String(form.get("grid") ?? "") || undefined,
      },
    });
    if (!queued) {
      const listed = await queue.list();
      const last = listed[listed.length - 1];
      if (last) {
        last.state = "draft";
      }
    }
    setRows(await queue.list());
    setNotice(queued ? "Queued. It syncs when you press Sync." : "Draft saved on this device.");
    event.currentTarget.reset();
  }

  async function saveDiagnostics(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const jobId = String(form.get("job_id") ?? "");
    const job = assignments?.repair_jobs.find((item) => item.repair_job_id === jobId);
    if (!job) {
      setError("Choose an authorized repair job first.");
      return;
    }
    setError(null);
    await queue.enqueue({
      op_type: "repair_diagnostics",
      entity_type: "repair",
      entity_id: jobId,
      base_field_version: job.field_version,
      payload: {
        diagnostics: {
          findings: String(form.get("findings") ?? ""),
          root_cause: String(form.get("cause") ?? ""),
        },
      },
    });
    setRows(await queue.list());
    setNotice("Diagnostics queued. Press Sync when you have connectivity.");
    event.currentTarget.reset();
  }

  async function uploadEvidence(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const target = String(form.get("target") ?? "survey");
    const entityId = String(form.get("entity_id") ?? "");
    const file = form.get("file");
    if (!(file instanceof File) || file.size === 0) {
      setError("Choose a photo or document first.");
      return;
    }
    setError(null);
    setNotice(null);
    const opId = `ev-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
    const upload = new FormData();
    upload.set("client_operation_id", opId);
    upload.set("target", target);
    upload.set("entity_id", entityId);
    upload.set("upload", file, file.name);
    try {
      await api("/api/v1/offline/evidence", { method: "POST", body: upload });
      setNotice("Evidence uploaded and stored on the server.");
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 0) {
        setError("No connectivity. Keep the file; upload it from this page when online.");
        return;
      }
      setError(caught instanceof ApiError ? caught.message : "Evidence upload failed.");
    }
  }

  async function purge() {
    if (!window.confirm("Delete all offline drafts and queued changes on this device?")) return;
    await queue.purgeUser();
    setRows(await queue.list());
    setNotice("Offline data on this device was deleted.");
  }

  if (!OFFLINE_ENABLED) {
    return (
      <div>
        <PageHeader
          title="Offline field work"
          description="Offline capture is behind a feature flag until acceptance testing passes."
        />
        <Card>
          <p className="text-sm text-moss-900/80">
            Ask your administrator to enable offline capture. Nothing here stores customer data
            while the flag is off.
          </p>
        </Card>
      </div>
    );
  }

  if (loading) return <LoadingState label="Loading offline workspace" />;

  return (
    <div>
      <PageHeader
        title="Offline field work"
        description={`Drafts stay on this device while offline and sync exactly once when you reconnect. Cached assignment data expires after ${assignments?.retention_days ?? 7} days.`}
        action={
          <Button disabled={syncing || !online} onClick={syncNow}>
            {!online ? "Offline" : syncing ? "Syncing…" : "Sync now"}
          </Button>
        }
      />
      <p role="status" aria-live="polite" className="text-sm text-moss-900/80">
        {online
          ? "You are online. Queued changes can sync."
          : "You are offline. Keep working; drafts are stored on this device."}
      </p>
      {error ? <div className="mt-3"><ErrorState message={error} onRetry={reload} /></div> : null}
      {notice ? (
        <p role="status" className="mt-3 rounded-md border border-moss-200 bg-moss-50 px-3 py-2 text-sm">
          {notice}
        </p>
      ) : null}

      <Card className="mt-4">
        <h2 className="text-base font-semibold">Authorized assignments</h2>
        <p className="mt-1 text-sm text-moss-900/80">
          Only these records may be edited offline. Cached until{" "}
          {assignments?.cached_until ? new Date(assignments.cached_until).toLocaleString() : "—"}.
        </p>
        <div className="mt-3 grid gap-4 md:grid-cols-2">
          <div>
            <h3 className="text-sm font-semibold">Surveys</h3>
            {assignments && assignments.surveys.length > 0 ? (
              <ul className="mt-1 space-y-1 text-sm">
                {assignments.surveys.map((item) => (
                  <li key={item.survey_id}>
                    {item.reference} · {item.status} · version {item.field_version}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-1 text-sm text-moss-900/80">No open surveys assigned to you.</p>
            )}
          </div>
          <div>
            <h3 className="text-sm font-semibold">Repair jobs</h3>
            {assignments && assignments.repair_jobs.length > 0 ? (
              <ul className="mt-1 space-y-1 text-sm">
                {assignments.repair_jobs.map((item) => (
                  <li key={item.repair_job_id}>
                    {item.reference} · {item.status} · version {item.field_version}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-1 text-sm text-moss-900/80">No open repair jobs assigned to you.</p>
            )}
          </div>
        </div>
      </Card>

      <Card className="mt-4">
        <h2 className="text-base font-semibold">Survey draft</h2>
        <form
          className="mt-3 grid gap-3 md:grid-cols-2"
          onSubmit={(event) => saveSurveyDraft(event, true)}
        >
          <label className="block text-sm md:col-span-2" htmlFor="offline-survey">
            <span className="font-medium">Survey</span>
            <select
              id="offline-survey"
              name="survey_id"
              required
              className="mt-1 w-full rounded-md border border-moss-200 bg-white px-3 py-2"
            >
              {(assignments?.surveys ?? []).map((item) => (
                <option key={item.survey_id} value={item.survey_id}>
                  {item.reference} (version {item.field_version})
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm md:col-span-2" htmlFor="offline-notes">
            <span className="font-medium">Notes</span>
            <textarea
              id="offline-notes"
              name="notes"
              rows={3}
              className="mt-1 w-full rounded-md border border-moss-200 bg-white px-3 py-2"
            />
          </label>
          <TextField label="Azimuth (degrees)" name="azimuth" inputMode="decimal" />
          <TextField label="Tilt (degrees)" name="tilt" inputMode="decimal" />
          <label className="block text-sm" htmlFor="offline-grid">
            <span className="font-medium">Grid connection</span>
            <select
              id="offline-grid"
              name="grid"
              className="mt-1 w-full rounded-md border border-moss-200 bg-white px-3 py-2"
            >
              <option value="">Leave unchanged</option>
              <option value="suitable">Suitable</option>
              <option value="unsuitable">Unsuitable</option>
              <option value="unknown">Unknown</option>
            </select>
          </label>
          <div className="md:col-span-2">
            <Button type="submit">Queue survey draft</Button>
          </div>
        </form>
      </Card>

      <Card className="mt-4">
        <h2 className="text-base font-semibold">Repair diagnostics</h2>
        <form className="mt-3 grid gap-3 md:grid-cols-2" onSubmit={saveDiagnostics}>
          <label className="block text-sm md:col-span-2" htmlFor="offline-job">
            <span className="font-medium">Repair job</span>
            <select
              id="offline-job"
              name="job_id"
              required
              className="mt-1 w-full rounded-md border border-moss-200 bg-white px-3 py-2"
            >
              {(assignments?.repair_jobs ?? []).map((item) => (
                <option key={item.repair_job_id} value={item.repair_job_id}>
                  {item.reference} (version {item.field_version})
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm md:col-span-2" htmlFor="offline-findings">
            <span className="font-medium">Findings</span>
            <textarea
              id="offline-findings"
              name="findings"
              rows={3}
              required
              className="mt-1 w-full rounded-md border border-moss-200 bg-white px-3 py-2"
            />
          </label>
          <TextField label="Root cause" name="cause" />
          <div className="md:col-span-2">
            <Button type="submit">Queue diagnostics</Button>
          </div>
        </form>
      </Card>

      <Card className="mt-4">
        <h2 className="text-base font-semibold">Evidence upload</h2>
        <p className="mt-1 text-sm text-moss-900/80">
          Photos retry safely: re-uploading the same file reuses the stored record instead of
          duplicating it.
        </p>
        <form className="mt-3 grid gap-3 md:grid-cols-2" onSubmit={uploadEvidence}>
          <TextField label="Target (survey or ticket)" name="target" defaultValue="survey" required />
          <TextField label="Record ID" name="entity_id" required hint="Survey or ticket ID from the assignments above." />
          <label className="block text-sm md:col-span-2" htmlFor="offline-file">
            <span className="font-medium">File (JPEG, PNG, WebP or PDF, max 5 MB)</span>
            <input
              id="offline-file"
              name="file"
              type="file"
              accept="image/jpeg,image/png,image/webp,application/pdf"
              required
              className="mt-1 w-full rounded-md border border-moss-200 bg-white px-3 py-2"
            />
          </label>
          <div className="md:col-span-2">
            <Button type="submit">Upload evidence</Button>
          </div>
        </form>
      </Card>

      <Card className="mt-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-semibold">Pending queue</h2>
          <Button variant="ghost" onClick={purge}>
            Delete device data
          </Button>
        </div>
        {rows.length === 0 ? (
          <p className="mt-2 text-sm text-moss-900/80">Nothing queued. Drafts appear here with their sync state.</p>
        ) : (
          <ul className="mt-2 space-y-2" aria-live="polite">
            {rows.map((row) => (
              <li
                key={row.client_operation_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-moss-200 px-3 py-2 text-sm"
              >
                <span>
                  <strong>{STATE_LABEL[row.state]}</strong> · {row.op_type} · attempts{" "}
                  {row.attempts}
                  {row.error ? <span className="block text-clay-700">{row.error}</span> : null}
                </span>
                <span className="text-moss-900/70">{row.client_operation_id.slice(0, 12)}…</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
