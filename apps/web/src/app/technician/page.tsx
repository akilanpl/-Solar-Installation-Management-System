"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Workspace } from "@/components/workspace";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge } from "@/components/ui";
import { api, type SurveyList } from "@/lib/api";
import { formatWhen } from "@/lib/format";

export function AssignedSurveys() {
  const [data, setData] = useState<SurveyList | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api<SurveyList>("/api/v1/surveys?page=1&page_size=50")
      .then(setData)
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load assigned surveys."));
  }

  useEffect(load, []);

  return (
    <>
      <PageHeader title="Assigned surveys" description="Only surveys assigned to you are listed. Installation completion is not part of this workspace." />
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!data && !error ? <LoadingState label="Loading assigned surveys" /> : null}
      {data && data.total === 0 ? <EmptyState title="No assigned surveys" body="When sales assigns a rooftop survey to you, it appears here." /> : null}
      {data && data.items.length > 0 ? (
        <div className="overflow-x-auto rounded-xl bg-white shadow-card">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-moss-100 text-xs uppercase tracking-wide text-moss-800">
              <tr>
                <th className="px-4 py-3">Reference</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Appointment</th>
                <th className="px-4 py-3">Opened</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id} className="border-b border-moss-50">
                  <td className="px-4 py-3">
                    <Link className="font-semibold text-moss-800 underline" href={`/technician/surveys/${item.id}`}>{item.reference}</Link>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
                  <td className="px-4 py-3">{item.appointment_starts_at ? formatWhen(item.appointment_starts_at) : "Pending"}</td>
                  <td className="px-4 py-3">{formatWhen(item.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </>
  );
}

export default function TechnicianHome() {
  return (
    <Workspace path="/technician">
      {() => <AssignedSurveys />}
    </Workspace>
  );
}
