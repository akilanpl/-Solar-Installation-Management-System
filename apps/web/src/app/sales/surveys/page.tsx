"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Workspace } from "@/components/workspace";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge } from "@/components/ui";
import { api, type SurveyList } from "@/lib/api";
import { formatWhen } from "@/lib/format";

export default function SalesSurveysPage() {
  return (
    <Workspace path="/sales/surveys">
      {() => <SurveyQueue />}
    </Workspace>
  );
}

function SurveyQueue() {
  const [data, setData] = useState<SurveyList | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api<SurveyList>("/api/v1/surveys?page=1&page_size=50")
      .then(setData)
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load surveys."));
  }

  useEffect(load, []);

  return (
    <>
      <PageHeader title="Surveys" description="Rooftop surveys opened from qualified enquiries. Assignment, review, and resurvey happen on each survey." />
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!data && !error ? <LoadingState label="Loading surveys" /> : null}
      {data && data.total === 0 ? <EmptyState title="No surveys" body="Qualify an enquiry, then open a survey from its detail page." /> : null}
      {data && data.items.length > 0 ? (
        <div className="overflow-x-auto rounded-xl bg-white shadow-card">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-moss-100 text-xs uppercase tracking-wide text-moss-800">
              <tr>
                <th className="px-4 py-3">Reference</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Appointment</th>
                <th className="px-4 py-3">Revision</th>
                <th className="px-4 py-3">Opened</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id} className="border-b border-moss-50">
                  <td className="px-4 py-3">
                    <Link className="font-semibold text-moss-800 underline" href={`/sales/surveys/${item.id}`}>
                      {item.reference}
                    </Link>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
                  <td className="px-4 py-3">{item.appointment_starts_at ? formatWhen(item.appointment_starts_at) : "Pending"}</td>
                  <td className="px-4 py-3">{item.revision_number}</td>
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
