"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Workspace } from "@/components/workspace";
import { EmptyState, ErrorState, LoadingState, Notice, PageHeader, StatusBadge } from "@/components/ui";
import { api, type PaymentRequirementResponse, type QuotationList } from "@/lib/api";
import { formatInrFromPaise } from "@/lib/format";

export default function CustomerPaymentsPage() {
  return (
    <Workspace path="/customer/payments">
      {() => <Payments />}
    </Workspace>
  );
}

function Payments() {
  const [rows, setRows] = useState<{ id: string; reference: string; status: string; requirement: PaymentRequirementResponse }[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api<QuotationList>("/api/v1/quotations?page=1&page_size=50")
      .then(async (quotes) => {
        const open = quotes.items.filter((item) => item.status === "issued" || item.status === "accepted");
        const loaded = await Promise.all(
          open.map(async (item) => ({
            id: item.id,
            reference: item.reference,
            status: item.status,
            requirement: await api<PaymentRequirementResponse>(`/api/v1/quotations/${item.id}/payment-requirement`),
          })),
        );
        setRows(loaded);
      })
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load payment requirements."));
  }

  useEffect(load, []);

  return (
    <>
      <PageHeader title="Payments" description="Amounts come from quotation payment requirements. There is no separate payment ledger." />
      <Notice tone="warning">A payment is verified only when the requirement’s verified amount includes it. Failed and unresolved attempts are not verified.</Notice>
      {error ? <div className="mt-4"><ErrorState message={error} onRetry={load} /></div> : null}
      {!rows && !error ? <LoadingState label="Loading payment requirements" /> : null}
      {rows && rows.length === 0 ? <EmptyState title="No payment requirements" body="An advance appears when a quotation is issued." /> : null}
      {rows && rows.length > 0 ? (
        <div className="mt-4 overflow-x-auto rounded-xl bg-white shadow-card">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-moss-100 text-xs uppercase tracking-wide text-moss-800">
              <tr>
                <th className="px-4 py-3">Quotation</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Advance</th>
                <th className="px-4 py-3">Verified</th>
                <th className="px-4 py-3">Outstanding</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-moss-50">
                  <td className="px-4 py-3">
                    <Link className="font-semibold text-moss-800 underline" href={`/customer/quotations/${row.id}`}>{row.reference}</Link>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={row.status} /></td>
                  <td className="px-4 py-3">{formatInrFromPaise(row.requirement.minimum_advance_minor)}</td>
                  <td className="px-4 py-3">{formatInrFromPaise(row.requirement.verified_minor)}</td>
                  <td className="px-4 py-3">{formatInrFromPaise(row.requirement.outstanding_minor)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </>
  );
}
