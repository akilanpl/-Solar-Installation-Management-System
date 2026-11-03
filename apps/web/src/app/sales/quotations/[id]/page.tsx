"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { QuoteLines } from "@/components/quote-lines";
import { Workspace } from "@/components/workspace";
import { Button, Card, ConfirmDialog, ErrorState, LoadingState, PageHeader, SelectField, StatusBadge, TextField } from "@/components/ui";
import {
  api,
  ApiError,
  idempotencyKey,
  type OrderResponse,
  type PackageResponse,
  type PaymentIntentResponse,
  type PaymentRequirementResponse,
  type QuotationResponse,
  type RevisionRequestResponse,
} from "@/lib/api";
import { formatInrFromPaise, formatWhen, rupeesToPaise, statusLabel } from "@/lib/format";

export default function SalesQuotationPage() {
  const params = useParams<{ id: string }>();
  return (
    <Workspace path={`/sales/quotations/${params.id}`}>
      {() => <QuoteReview id={params.id} />}
    </Workspace>
  );
}

function QuoteReview({ id }: { id: string }) {
  const router = useRouter();
  const [quote, setQuote] = useState<QuotationResponse | null>(null);
  const [requirement, setRequirement] = useState<PaymentRequirementResponse | null>(null);
  const [requests, setRequests] = useState<RevisionRequestResponse[]>([]);
  const [packages, setPackages] = useState<PackageResponse[]>([]);
  const [order, setOrder] = useState<OrderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [packageCode, setPackageCode] = useState("");
  const [discount, setDiscount] = useState("");
  const [requestId, setRequestId] = useState("");
  const [receipt, setReceipt] = useState("");
  const [cashRupees, setCashRupees] = useState("");
  const [confirm, setConfirm] = useState<null | "withdraw" | "revise" | "order" | "cash">(null);

  function load() {
    setError(null);
    Promise.all([
      api<QuotationResponse>(`/api/v1/quotations/${id}`),
      api<PaymentRequirementResponse>(`/api/v1/quotations/${id}/payment-requirement`),
      api<RevisionRequestResponse[]>(`/api/v1/quotations/${id}/revision-requests`),
      api<PackageResponse[]>("/api/v1/packages"),
      api<{ items: OrderResponse[] }>("/api/v1/orders?page=1&page_size=50"),
    ])
      .then(([quoteBody, requirementBody, requestBody, packageBody, orders]) => {
        setQuote(quoteBody);
        setRequirement(requirementBody);
        setRequests(requestBody);
        setPackageCode(quoteBody.package_code);
        const current = packageBody.find((row) => row.code === quoteBody.package_code);
        setPackages(
          packageBody.filter(
            (item) =>
              item.is_active &&
              item.category === "package" &&
              item.capacity_w === current?.capacity_w &&
              item.grid_type === current?.grid_type,
          ),
        );
        setOrder(orders.items.find((item) => item.quotation_id === quoteBody.id) ?? null);
      })
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load the quotation."));
  }

  useEffect(load, [id]);

  async function run(action: () => Promise<void>) {
    setPending(true);
    setError(null);
    try {
      await action();
      setConfirm(null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The action was not saved.");
      setConfirm(null);
    } finally {
      setPending(false);
    }
  }

  if (!quote && !error) return <LoadingState label="Loading quotation" />;
  if (!quote) return <ErrorState message={error ?? "Quotation not found."} />;
  const canOrder = quote.status === "accepted" && requirement !== null && requirement.verified_minor >= requirement.minimum_advance_minor && !order;

  return (
    <>
      <PageHeader
        title={`${quote.reference} · v${quote.version_number}`}
        description={`${quote.package_code} · issued ${formatWhen(quote.issued_at)}`}
        action={<StatusBadge status={quote.status} />}
      />
      {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
      <Card>
        <QuoteLines
          lines={quote.lines}
          material={quote.material_total_minor}
          installation={quote.installation_total_minor}
          discount={quote.discount_minor}
          tax={quote.tax_minor}
          taxRateBps={quote.tax_rate_bps}
          total={quote.total_minor}
        />
      </Card>
      {requirement ? (
        <Card className="mt-4">
          <h2 className="font-semibold">Payment requirement</h2>
          <dl className="mt-3 space-y-1 text-sm">
            <div className="flex justify-between"><dt>Advance ({requirement.advance_percent}%)</dt><dd>{formatInrFromPaise(requirement.minimum_advance_minor)}</dd></div>
            <div className="flex justify-between"><dt>Verified</dt><dd>{formatInrFromPaise(requirement.verified_minor)}</dd></div>
            <div className="flex justify-between"><dt>Outstanding</dt><dd>{formatInrFromPaise(requirement.outstanding_minor)}</dd></div>
          </dl>
          {requirement.verified_minor < requirement.minimum_advance_minor ? (
            <p className="mt-2 text-sm">The advance is not verified yet. An order cannot be confirmed.</p>
          ) : (
            <p className="mt-2 text-sm">Verified payments cover the advance.</p>
          )}
        </Card>
      ) : null}
      {quote.status === "issued" || quote.status === "accepted" ? (
        <Card className="mt-4">
          <h2 className="font-semibold">Cash receipt</h2>
          <p className="mt-2 text-sm">A cash receipt is recorded as verified immediately. It is not a test payment.</p>
          <form
            className="mt-3 grid gap-3 md:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault();
              if (rupeesToPaise(cashRupees) === null || receipt.trim().length < 3) {
                setError("Enter a receipt reference and a whole-rupee amount.");
                return;
              }
              setConfirm("cash");
            }}
          >
            <TextField label="Amount in rupees" name="cash" value={cashRupees} onChange={(event) => setCashRupees(event.target.value)} />
            <TextField label="Receipt reference" name="receipt" value={receipt} onChange={(event) => setReceipt(event.target.value)} />
            <Button type="submit">Record cash receipt</Button>
          </form>
        </Card>
      ) : null}
      {requests.length > 0 ? (
        <Card className="mt-4">
          <h2 className="font-semibold">Revision requests</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {requests.map((item) => (
              <li key={item.id}>{statusLabel(item.category)} · {item.request_text} · {statusLabel(item.status)}</li>
            ))}
          </ul>
        </Card>
      ) : null}
      {quote.status === "issued" ? (
        <Card className="mt-4">
          <h2 className="font-semibold">Revise or withdraw</h2>
          <form
            className="mt-3 space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              if (discount && rupeesToPaise(discount) === null) {
                setError("Enter the discount in whole rupees, or leave it blank.");
                return;
              }
              setConfirm("revise");
            }}
          >
            <SelectField label="Package" name="package" value={packageCode} onChange={(event) => setPackageCode(event.target.value)}>
              {packages.map((item) => (
                <option key={item.code} value={item.code}>{item.name} ({item.code})</option>
              ))}
            </SelectField>
            <TextField label="Discount in rupees" name="discount" value={discount} onChange={(event) => setDiscount(event.target.value)} />
            {requests.length > 0 ? (
              <SelectField label="Revision request" name="request" value={requestId} onChange={(event) => setRequestId(event.target.value)}>
                <option value="">None</option>
                {requests.map((item) => (
                  <option key={item.id} value={item.id}>{item.category}</option>
                ))}
              </SelectField>
            ) : null}
            <div className="flex flex-wrap gap-2">
              <Button type="submit">Revise quotation</Button>
              <Button type="button" variant="danger" onClick={() => setConfirm("withdraw")}>Withdraw</Button>
            </div>
          </form>
        </Card>
      ) : null}
      {order ? (
        <p className="mt-4 text-sm">
          Confirmed as <Link className="font-semibold text-moss-800 underline" href={`/sales/orders/${order.id}`}>{order.reference}</Link>.
        </p>
      ) : null}
      {canOrder ? <Button className="mt-4" type="button" onClick={() => setConfirm("order")}>Confirm order</Button> : null}
      {confirm === "withdraw" ? (
        <ConfirmDialog
          title="Withdraw this quotation?"
          body="A withdrawn quotation cannot be accepted. You can issue a new one afterwards."
          confirmLabel="Withdraw"
          pending={pending}
          onCancel={() => setConfirm(null)}
          onConfirm={() => {
            void run(async () => {
              const updated = await api<QuotationResponse>(`/api/v1/quotations/${id}/withdrawal`, { method: "POST" });
              setQuote(updated);
            });
          }}
        />
      ) : null}
      {confirm === "revise" ? (
        <ConfirmDialog
          title="Issue a revision?"
          body="The current quotation becomes superseded. The customer sees the new revision."
          confirmLabel="Issue revision"
          pending={pending}
          onCancel={() => setConfirm(null)}
          onConfirm={() => {
            void run(async () => {
              const created = await api<QuotationResponse>(`/api/v1/quotations/${id}/revisions`, {
                method: "POST",
                headers: { "Idempotency-Key": idempotencyKey() },
                body: JSON.stringify({
                  package_code: packageCode,
                  discount_minor: discount ? rupeesToPaise(discount) ?? 0 : 0,
                  revision_request_id: requestId || null,
                }),
              });
              router.push(`/sales/quotations/${created.id}`);
            });
          }}
        />
      ) : null}
      {confirm === "cash" ? (
        <ConfirmDialog
          title="Record this cash receipt?"
          body="This marks the amount verified. It is a real receipt, not a sandbox payment."
          confirmLabel="Record receipt"
          pending={pending}
          onCancel={() => setConfirm(null)}
          onConfirm={() => {
            void run(async () => {
              await api<PaymentIntentResponse>("/api/v1/payments/cash-receipts", {
                method: "POST",
                headers: { "Idempotency-Key": idempotencyKey() },
                body: JSON.stringify({
                  quotation_id: id,
                  amount_minor: rupeesToPaise(cashRupees),
                  receipt_reference: receipt.trim(),
                }),
              });
              const next = await api<PaymentRequirementResponse>(`/api/v1/quotations/${id}/payment-requirement`);
              setRequirement(next);
            });
          }}
        />
      ) : null}
      {confirm === "order" ? (
        <ConfirmDialog
          title="Confirm the installation order?"
          body="This creates one order, a warehouse preparation request, and an unscheduled installation request. Stock is not deducted."
          confirmLabel="Confirm order"
          pending={pending}
          onCancel={() => setConfirm(null)}
          onConfirm={() => {
            void run(async () => {
              const created = await api<OrderResponse>("/api/v1/orders", {
                method: "POST",
                headers: { "Idempotency-Key": idempotencyKey() },
                body: JSON.stringify({ quotation_id: id }),
              });
              router.push(`/sales/orders/${created.id}`);
            });
          }}
        />
      ) : null}
    </>
  );
}
