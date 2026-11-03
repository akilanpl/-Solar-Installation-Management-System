"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Workspace } from "@/components/workspace";
import { EmptyState, ErrorState, LoadingState, Notice, PageHeader, StatusBadge } from "@/components/ui";
import { api, type SchedulingRequestResponse } from "@/lib/api";
import { formatWhen } from "@/lib/format";

export default function SchedulingPage() {
  return (
    <Workspace path="/sales/scheduling">
      {() => <Queue />}
    </Workspace>
  );
}

function Queue() {
  const [rows, setRows] = useState<SchedulingRequestResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api<SchedulingRequestResponse[]>("/api/v1/scheduling/installations")
      .then(setRows)
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load scheduling requests."));
  }

  useEffect(load, []);

  return (
    <>
      <PageHeader title="Installation scheduling" description="Confirmed orders create a scheduling request. No visit is booked until a slot exists." />
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!rows && !error ? <LoadingState label="Loading scheduling requests" /> : null}
      {rows && rows.length === 0 ? <EmptyState title="Nothing to schedule" body="Scheduling requests appear when an order is confirmed." /> : null}
      {rows && rows.length > 0 ? (
        <div className="space-y-3">
          {rows.map((row) => (
            <article key={row.id} className="rounded-xl bg-white p-4 shadow-card">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="font-semibold">
                  <Link className="underline" href={`/sales/orders/${row.order_id}`}>{row.order_reference}</Link>
                </h2>
                <StatusBadge status={row.slot_starts_at ? row.status : "unscheduled"} />
              </div>
              <p className="mt-2 text-sm">{row.work_summary}</p>
              {row.slot_starts_at ? (
                <p className="mt-2 text-sm">Slot {formatWhen(row.slot_starts_at)}</p>
              ) : (
                <div className="mt-3">
                  <Notice>Unscheduled. This request has no installation slot.</Notice>
                </div>
              )}
            </article>
          ))}
        </div>
      ) : null}
    </>
  );
}
