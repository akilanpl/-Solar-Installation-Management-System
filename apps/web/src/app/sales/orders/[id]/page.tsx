"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Workspace } from "@/components/workspace";
import { Card, ErrorState, LoadingState, Notice, PageHeader, StatusBadge } from "@/components/ui";
import { api, type OrderResponse } from "@/lib/api";
import { formatInrFromPaise, formatWhen } from "@/lib/format";

export default function SalesOrderPage() {
  const params = useParams<{ id: string }>();
  return (
    <Workspace path={`/sales/orders/${params.id}`}>
      {() => <OrderView id={params.id} />}
    </Workspace>
  );
}

export function OrderView({ id, ordersHref = "/sales/orders", showScheduling = true }: { id: string; ordersHref?: string; showScheduling?: boolean }) {
  const [order, setOrder] = useState<OrderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<OrderResponse>(`/api/v1/orders/${id}`)
      .then(setOrder)
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load the order."));
  }, [id]);

  if (error) return <ErrorState message={error} />;
  if (!order) return <LoadingState label="Loading order" />;

  return (
    <>
      <PageHeader title={order.reference} description={`${order.package_code} · confirmed ${formatWhen(order.confirmed_at)}`} action={<StatusBadge status={order.status} />} />
      {order.test_only_payment ? <Notice tone="warning">TEST ONLY. This order was confirmed from a sandbox payment.</Notice> : null}
      <Card className="mt-4">
        <dl className="space-y-1 text-sm">
          <div className="flex justify-between"><dt>Total</dt><dd>{formatInrFromPaise(order.total_minor)}</dd></div>
          <div className="flex justify-between"><dt>Payment</dt><dd>{order.payment_verification_state.replaceAll("_", " ")}</dd></div>
          <div className="flex justify-between"><dt>Quotation version</dt><dd>{order.quotation_version}</dd></div>
        </dl>
        <ul className="mt-4 space-y-1 text-sm">
          {order.lines.map((line) => (
            <li key={`${line.sort_order}-${line.description}`}>
              {line.quantity} {line.unit} {line.description} · {formatInrFromPaise(line.line_total_minor)}
            </li>
          ))}
        </ul>
      </Card>
      <Card className="mt-4">
        <h2 className="font-semibold">Handoff</h2>
        <p className="mt-2 text-sm">Warehouse preparation is queued. Equipment is not marked dispatched or installed, and stock is not deducted.</p>
        {showScheduling ? (
          <p className="mt-2 text-sm">
            <Link className="font-semibold text-moss-800 underline" href="/sales/scheduling">Installation scheduling</Link> shows this order as unscheduled until a slot exists.
          </p>
        ) : (
          <p className="mt-2 text-sm">Installation is unscheduled until sales books a slot.</p>
        )}
      </Card>
      <p className="mt-4 text-sm">
        <Link className="font-semibold text-moss-800 underline" href={ordersHref}>Back to orders</Link>
      </p>
    </>
  );
}
