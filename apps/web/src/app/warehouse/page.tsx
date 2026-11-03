"use client";

import { useEffect, useState } from "react";

import { Workspace } from "@/components/workspace";
import { EmptyState, ErrorState, LoadingState, Notice, PageHeader, StatusBadge } from "@/components/ui";
import { api, type WarehouseRequestResponse } from "@/lib/api";
import { formatWhen } from "@/lib/format";

export default function WarehousePage() {
  return (
    <Workspace path="/warehouse">
      {() => <PreparationQueue />}
    </Workspace>
  );
}

function PreparationQueue() {
  const [rows, setRows] = useState<WarehouseRequestResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api<WarehouseRequestResponse[]>("/api/v1/warehouse/preparation")
      .then(setRows)
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load preparation requests."));
  }

  useEffect(load, []);

  return (
    <>
      <PageHeader title="Preparation queue" description="Material lines come from confirmed orders. This screen does not show stock balances and does not dispatch equipment." />
      <Notice>Stock is not deducted. Nothing here is marked dispatched or installed.</Notice>
      {error ? <div className="mt-4"><ErrorState message={error} onRetry={load} /></div> : null}
      {!rows && !error ? <LoadingState label="Loading preparation requests" /> : null}
      {rows && rows.length === 0 ? <EmptyState title="No preparation requests" body="A request appears when sales confirms an order." /> : null}
      {rows && rows.length > 0 ? (
        <div className="mt-4 space-y-4">
          {rows.map((row) => (
            <article key={row.id} className="rounded-xl bg-white p-4 shadow-card">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="font-semibold">{row.order_reference}</h2>
                <StatusBadge status={row.status} />
              </div>
              <p className="mt-1 text-xs text-moss-800/70">Requested {formatWhen(row.created_at)}</p>
              <table className="mt-3 min-w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-moss-800">
                  <tr>
                    <th className="py-1">Material</th>
                    <th className="py-1">Code</th>
                    <th className="py-1">Quantity</th>
                  </tr>
                </thead>
                <tbody>
                  {row.lines.map((line) => (
                    <tr key={`${row.id}-${line.component_code}`}>
                      <td className="py-1">{line.description}</td>
                      <td className="py-1">{line.component_code}</td>
                      <td className="py-1">{line.quantity} {line.unit}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </article>
          ))}
        </div>
      ) : null}
    </>
  );
}
