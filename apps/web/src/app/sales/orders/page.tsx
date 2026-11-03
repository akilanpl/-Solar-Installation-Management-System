"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Workspace } from "@/components/workspace";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge } from "@/components/ui";
import { api, type OrderList } from "@/lib/api";
import { formatInrFromPaise, formatWhen } from "@/lib/format";

export default function SalesOrdersPage() {
  return (
    <Workspace path="/sales/orders">
      {() => <OrderQueue base="/sales/orders" />}
    </Workspace>
  );
}

export function OrderQueue({ base }: { base: string }) {
  const [data, setData] = useState<OrderList | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api<OrderList>("/api/v1/orders?page=1&page_size=50")
      .then(setData)
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load orders."));
  }

  useEffect(load, []);

  return (
    <>
      <PageHeader title="Orders" description="A confirmed order is created only after the customer accepts a quotation and the advance is verified." />
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!data && !error ? <LoadingState label="Loading orders" /> : null}
      {data && data.total === 0 ? <EmptyState title="No confirmed orders" body="Orders appear after sales confirms an accepted, paid quotation." /> : null}
      {data && data.items.length > 0 ? (
        <div className="overflow-x-auto rounded-xl bg-white shadow-card">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-moss-100 text-xs uppercase tracking-wide text-moss-800">
              <tr>
                <th className="px-4 py-3">Reference</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Package</th>
                <th className="px-4 py-3">Total</th>
                <th className="px-4 py-3">Payment</th>
                <th className="px-4 py-3">Confirmed</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id} className="border-b border-moss-50">
                  <td className="px-4 py-3">
                    <Link className="font-semibold text-moss-800 underline" href={`${base}/${item.id}`}>
                      {item.reference}
                    </Link>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
                  <td className="px-4 py-3">{item.package_code}</td>
                  <td className="px-4 py-3">{formatInrFromPaise(item.total_minor)}</td>
                  <td className="px-4 py-3">
                    {item.test_only_payment ? "Test payment" : item.payment_verification_state.replaceAll("_", " ")}
                  </td>
                  <td className="px-4 py-3">{formatWhen(item.confirmed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </>
  );
}
