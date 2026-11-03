"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { QuoteLines } from "@/components/quote-lines";
import { Workspace } from "@/components/workspace";
import { Button, Card, ConfirmDialog, ErrorState, LoadingState, Notice, PageHeader, SelectField, StatusBadge, TextArea, TextField } from "@/components/ui";
import {
  api,
  ApiError,
  idempotencyKey,
  sandboxPaymentsEnabled,
  type OrderList,
  type PaymentIntentResponse,
  type PaymentRequirementResponse,
  type QuotationResponse,
  type RevisionRequestResponse,
} from "@/lib/api";
import { formatInrFromPaise, rupeesToPaise, statusLabel } from "@/lib/format";

export default function CustomerQuotationPage() {
  const params = useParams<{ id: string }>();
  return (
    <Workspace path={`/customer/quotations/${params.id}`}>
      {() => <QuoteView id={params.id} />}
    </Workspace>
  );
}

function QuoteView({ id }: { id: string }) {
  const [quote, setQuote] = useState<QuotationResponse | null>(null);
  const [requirement, setRequirement] = useState<PaymentRequirementResponse | null>(null);
  const [requests, setRequests] = useState<RevisionRequestResponse[]>([]);
  const [orderId, setOrderId] = useState<string | null>(null);
  const [intent, setIntent] = useState<PaymentIntentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [category, setCategory] = useState("pricing");
  const [requestText, setRequestText] = useState("");
  const [amount, setAmount] = useState("");
  const [confirm, setConfirm] = useState<null | "accept" | "pay">(null);

  function load() {
    Promise.all([
      api<QuotationResponse>(`/api/v1/quotations/${id}`),
      api<PaymentRequirementResponse>(`/api/v1/quotations/${id}/payment-requirement`),
      api<RevisionRequestResponse[]>(`/api/v1/quotations/${id}/revision-requests`),
      api<OrderList>("/api/v1/orders?page=1&page_size=50"),
    ])
      .then(([quoteBody, requirementBody, requestBody, orders]) => {
        setQuote(quoteBody);
        setRequirement(requirementBody);
        setRequests(requestBody);
        setOrderId(orders.items.find((item) => item.quotation_id === quoteBody.id)?.id ?? null);
        setAmount((current) => current || String(Math.trunc(requirementBody.minimum_advance_minor / 100)));
      })
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load the quotation."));
  }

  useEffect(() => {
    load();
  }, [id]);

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

  return (
    <>
      <PageHeader title={`${quote.reference} · version ${quote.version_number}`} description={quote.package_code} action={<StatusBadge status={quote.status} />} />
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
          <h2 className="font-semibold">Advance</h2>
          <p className="mt-2 text-sm">
            {requirement.advance_percent}% advance {formatInrFromPaise(requirement.minimum_advance_minor)}. Verified {formatInrFromPaise(requirement.verified_minor)}. Outstanding {formatInrFromPaise(requirement.outstanding_minor)}.
          </p>
          {requirement.verified_minor > 0 ? <p className="mt-2 text-sm">Verified amount is only money the server has marked verified.</p> : null}
        </Card>
      ) : null}
      {quote.status === "issued" ? (
        <Card className="mt-4">
          <h2 className="font-semibold">Ask for a revision</h2>
          <form
            className="mt-3 space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              void run(async () => {
                const created = await api<RevisionRequestResponse>(`/api/v1/quotations/${id}/revision-requests`, {
                  method: "POST",
                  body: JSON.stringify({ category, request_text: requestText }),
                });
                setRequests((current) => [created, ...current]);
                setRequestText("");
              });
            }}
          >
            <SelectField label="Category" name="category" value={category} onChange={(event) => setCategory(event.target.value)}>
              <option value="capacity">Capacity</option>
              <option value="grid">Grid</option>
              <option value="components">Components</option>
              <option value="pricing">Pricing</option>
              <option value="installation">Installation</option>
            </SelectField>
            <TextArea label="What should change?" name="request_text" value={requestText} onChange={(event) => setRequestText(event.target.value)} />
            <Button type="submit" disabled={pending || requestText.trim().length < 3}>Send request</Button>
          </form>
          {requests.length > 0 ? (
            <ul className="mt-3 space-y-1 text-sm">
              {requests.map((item) => <li key={item.id}>{statusLabel(item.category)} · {item.request_text} · {statusLabel(item.status)}</li>)}
            </ul>
          ) : null}
          <Button className="mt-4" type="button" onClick={() => setConfirm("accept")}>Accept version {quote.version_number}</Button>
        </Card>
      ) : null}
      {(quote.status === "issued" || quote.status === "accepted") && requirement && requirement.outstanding_minor > 0 ? (
        <Card className="mt-4">
          <h2 className="font-semibold">Payment</h2>
          {sandboxPaymentsEnabled ? (
            <>
              <Notice tone="warning">TEST ONLY. Sandbox payments are not a bank transfer and are refused in production.</Notice>
              <form
                className="mt-3 space-y-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (rupeesToPaise(amount) === null) {
                    setError("Enter the payment in whole rupees.");
                    return;
                  }
                  setConfirm("pay");
                }}
              >
                <TextField label="Amount in rupees" name="amount" value={amount} onChange={(event) => setAmount(event.target.value)} hint="Whole rupees. The server rejects an amount above the outstanding balance." />
                <Button type="submit">Start test payment</Button>
              </form>
            </>
          ) : (
            <p className="mt-2 text-sm">Sandbox confirmation is disabled outside development. A payment stays unverified until the server records it.</p>
          )}
          {intent ? (
            <div className="mt-4 space-y-2">
              <p className="text-sm font-medium">Latest attempt {formatInrFromPaise(intent.amount_minor)} · {intent.is_test_only ? "TEST ONLY" : intent.provider}</p>
              <StatusBadge status={intent.status} />
              {intent.status === "unresolved" || intent.status === "failed" ? (
                <p className="text-sm">This payment is not verified.</p>
              ) : null}
              {sandboxPaymentsEnabled && intent.status === "pending" ? (
                <div className="flex flex-wrap gap-2">
                  <Button type="button" disabled={pending} onClick={() => void outcome("succeeded")}>Record test success</Button>
                  <Button type="button" variant="danger" disabled={pending} onClick={() => void outcome("failed")}>Record test failure</Button>
                  <Button type="button" variant="secondary" disabled={pending} onClick={() => void outcome("unknown")}>Leave unresolved</Button>
                </div>
              ) : null}
            </div>
          ) : null}
        </Card>
      ) : null}
      {orderId ? (
        <p className="mt-4 text-sm">
          <Link className="font-semibold text-moss-800 underline" href={`/customer/orders/${orderId}`}>View confirmed order</Link>
        </p>
      ) : null}
      {confirm === "accept" ? (
        <ConfirmDialog
          title={`Accept version ${quote.version_number}?`}
          body={`This accepts ${quote.reference} exactly as issued, total ${formatInrFromPaise(quote.total_minor)}. It does not change the line items.`}
          confirmLabel="Accept quotation"
          pending={pending}
          onCancel={() => setConfirm(null)}
          onConfirm={() => {
            void run(async () => {
              setQuote(await api<QuotationResponse>(`/api/v1/quotations/${id}/acceptance`, { method: "POST" }));
            });
          }}
        />
      ) : null}
      {confirm === "pay" ? (
        <ConfirmDialog
          title="Start a test payment?"
          body="TEST ONLY. This creates a sandbox payment. It is not verified until you record a test success."
          confirmLabel="Start test payment"
          pending={pending}
          onCancel={() => setConfirm(null)}
          onConfirm={() => {
            void run(async () => {
              const created = await api<PaymentIntentResponse>("/api/v1/payments/intents", {
                method: "POST",
                headers: { "Idempotency-Key": idempotencyKey() },
                body: JSON.stringify({ quotation_id: id, amount_minor: rupeesToPaise(amount) }),
              });
              setIntent(created);
            });
          }}
        />
      ) : null}
    </>
  );

  async function outcome(value: "succeeded" | "failed" | "unknown") {
    if (!intent) return;
    setPending(true);
    setError(null);
    try {
      const updated = await api<PaymentIntentResponse>(`/api/v1/payments/intents/${intent.id}/sandbox-outcome`, {
        method: "POST",
        body: JSON.stringify({ outcome: value }),
      });
      setIntent(updated);
      setRequirement(await api<PaymentRequirementResponse>(`/api/v1/quotations/${id}/payment-requirement`));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The payment outcome was not recorded.");
    } finally {
      setPending(false);
    }
  }
}
