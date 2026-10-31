"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Workspace } from "@/components/workspace";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge } from "@/components/ui";
import { api, type EnquiryList } from "@/lib/api";
import { formatCapacity, formatWhen, GRID_LABEL } from "@/lib/format";

export default function SalesHome() {
  return (
    <Workspace path="/sales">
      {() => <SalesQueue />}
    </Workspace>
  );
}

function SalesQueue() {
  const [data, setData] = useState<EnquiryList | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api<EnquiryList>("/api/v1/enquiries?page=1&page_size=50")
      .then(setData)
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load enquiries."));
  }

  useEffect(load, []);

  return (
    <>
      <PageHeader
        title="Enquiries"
        description="Sales can read every customer enquiry in the database and update qualification. Open survey assignment, quotations and installation scheduling from the workspace dock."
      />
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!data && !error ? <LoadingState label="Loading enquiries" /> : null}
      {data && data.total === 0 ? (
        <EmptyState title="No enquiries" body="When a customer submits an enquiry, it appears here. There is no sample data." />
      ) : null}
      {data && data.items.length > 0 ? (
        <div className="overflow-x-auto rounded-xl bg-white shadow-card">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-moss-100 text-xs uppercase tracking-wide text-moss-800">
              <tr>
                <th className="px-4 py-3">Reference</th>
                <th className="px-4 py-3">Customer</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">System</th>
                <th className="px-4 py-3">Submitted</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id} className="border-b border-moss-50">
                  <td className="px-4 py-3">
                    <Link className="font-semibold text-moss-800 underline" href={`/sales/enquiries/${item.id}`}>
                      {item.reference}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{item.contact_name}</td>
                  <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
                  <td className="px-4 py-3">{formatCapacity(item.preferred_capacity_w)} {GRID_LABEL[item.grid_preference]}</td>
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
