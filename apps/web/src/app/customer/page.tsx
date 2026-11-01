"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { CustomerRecoveryDashboard } from "@/components/recovery/customer-dashboard";
import { Workspace } from "@/components/workspace";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge } from "@/components/ui";
import { api, type EnquiryList } from "@/lib/api";
import { formatCapacity, formatInrFromPaise, formatWhen, GRID_LABEL } from "@/lib/format";

export default function CustomerHome() {
  return (
    <Workspace path="/customer">
      {() => <CustomerDashboard />}
    </Workspace>
  );
}

function CustomerDashboard() {
  const [data, setData] = useState<EnquiryList | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setError(null);
    api<EnquiryList>("/api/v1/enquiries")
      .then(setData)
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load enquiries."));
  }

  useEffect(load, []);

  return (
    <>
      <CustomerRecoveryDashboard />
      <section className="customer-enquiry-records">
      <PageHeader
        title="Your enquiries"
        description="Track your enquiries here. Issued quotations and recorded payment requirements are available from the workspace menu."
        action={
          <Link href="/customer/enquiries/new" className="rounded-md bg-moss-700 px-4 py-2 text-sm font-semibold text-white">
            New enquiry
          </Link>
        }
      />
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!data && !error ? <LoadingState label="Loading your enquiries" /> : null}
      {data && data.total === 0 ? (
        <EmptyState
          title="No enquiries yet"
          body="Submit a solar connection enquiry when you are ready. Nothing is shown here until you do."
          action={
            <Link href="/customer/enquiries/new" className="text-sm font-semibold text-moss-800 underline">
              Start an enquiry
            </Link>
          }
        />
      ) : null}
      {data && data.items.length > 0 ? (
        <div className="overflow-x-auto rounded-xl bg-white shadow-card">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-moss-100 text-xs uppercase tracking-wide text-moss-800">
              <tr>
                <th className="px-4 py-3">Reference</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">System</th>
                <th className="px-4 py-3">Bill</th>
                <th className="px-4 py-3">Submitted</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id} className="border-b border-moss-50">
                  <td className="px-4 py-3">
                    <Link className="font-semibold text-moss-800 underline" href={`/customer/enquiries/${item.id}`}>
                      {item.reference}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="px-4 py-3">
                    {formatCapacity(item.preferred_capacity_w)} · {GRID_LABEL[item.grid_preference]}
                  </td>
                  <td className="px-4 py-3">{formatInrFromPaise(item.monthly_bill_minor)}</td>
                  <td className="px-4 py-3">{formatWhen(item.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      </section>
    </>
  );
}
