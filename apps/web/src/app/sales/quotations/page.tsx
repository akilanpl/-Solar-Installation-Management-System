"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Workspace } from "@/components/workspace";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge } from "@/components/ui";
import { api, type QuotationList } from "@/lib/api";
import { formatInrFromPaise, formatWhen } from "@/lib/format";

export default function SalesQuotationsPage() {
  return (
    <Workspace path="/sales/quotations">
      {() => <QuoteQueue />}
    </Workspace>
  );
}

function QuoteQueue() {
  const [data, setData] = useState<QuotationList | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api<QuotationList>("/api/v1/quotations?page=1&page_size=50")
      .then(setData)
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load quotations."));
  }

  useEffect(load, []);

  return (
    <>
      <PageHeader title="Quotations" description="Issued from an approved survey. A quotation revision replaces the previous one. Amounts are stored in paise." />
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!data && !error ? <LoadingState label="Loading quotations" /> : null}
      {data && data.total === 0 ? <EmptyState title="No quotations" body="Approve a survey, then issue a quotation from the survey page." /> : null}
      {data && data.items.length > 0 ? (
        <div className="overflow-x-auto rounded-xl bg-white shadow-card">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-moss-100 text-xs uppercase tracking-wide text-moss-800">
              <tr>
                <th className="px-4 py-3">Reference</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Package</th>
                <th className="px-4 py-3">Version</th>
                <th className="px-4 py-3">Total</th>
                <th className="px-4 py-3">Issued</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id} className="border-b border-moss-50">
                  <td className="px-4 py-3">
                    <Link className="font-semibold text-moss-800 underline" href={`/sales/quotations/${item.id}`}>
                      {item.reference}
                    </Link>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
                  <td className="px-4 py-3">{item.package_code}</td>
                  <td className="px-4 py-3">{item.version_number}</td>
                  <td className="px-4 py-3">{formatInrFromPaise(item.total_minor)}</td>
                  <td className="px-4 py-3">{formatWhen(item.issued_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </>
  );
}
