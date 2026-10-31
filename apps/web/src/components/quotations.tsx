"use client";

import { useCallback, useEffect, useState } from "react";
import type { components } from "@/generated/schema";
import { api } from "@/lib/api";
import { formatInrFromPaise } from "@/lib/format";
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge, TextField } from "@/components/ui";

type Quote = components["schemas"]["QuotationResponse"];
type Requirement = components["schemas"]["PaymentRequirementResponse"];
export function Quotations({ customer = true }: { customer?: boolean }) {
  const [items, setItems] = useState<Quote[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const load = useCallback(() => {
    setError(null);
    api<components["schemas"]["QuotationList"]>(`/api/v1/quotations?page=${page}`)
      .then(data => { setItems(data.items); setTotal(data.total); })
      .catch(e => setError(e instanceof Error ? e.message : "Could not load quotations."));
  }, [page]);
  useEffect(load, [load]);
  return <><PageHeader title="Quotations and payments" description="Review the exact issued version and recorded payment requirement. Online payment providers are unavailable." />
    {error && <ErrorState message={error} onRetry={load} />}
    {!items && !error && <LoadingState />}
    {items?.length === 0 && <EmptyState title="No quotations" body="An approved survey is required before sales can issue a quotation." />}
    <div className="space-y-5">{items?.map(quote => <QuoteCard key={quote.id} quote={quote} customer={customer} onChange={load} />)}</div>
    {items && total > 20 && <div className="mt-4 flex items-center gap-3"><Button disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button><span>Page {page}</span><Button disabled={page * 20 >= total} onClick={() => setPage(page + 1)}>Next</Button></div>}
  </>;
}
function QuoteCard({ quote, customer, onChange }: { quote: Quote; customer: boolean; onChange: () => void }) {
  const [requirement, setRequirement] = useState<Requirement | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  useEffect(() => {
    api<Requirement>(`/api/v1/quotations/${quote.id}/payment-requirement`).then(setRequirement).catch(e => setError(e.message));
  }, [quote.id, quote.status]);
  async function act(action: "acceptance" | "revision-requests") {
    setPending(true); setError(null);
    try {
      const body: components["schemas"]["RevisionRequestCreate"] = { category: "installation", request_text: reason };
      await api(`/api/v1/quotations/${quote.id}/${action}`, { method: "POST", ...(action === "revision-requests" ? { body: JSON.stringify(body) } : {}) });
      setReason(""); onChange();
    } catch (e) { setError(e instanceof Error ? e.message : "Action failed."); }
    finally { setPending(false); }
  }
  return <Card><div className="flex flex-wrap justify-between gap-3"><h2 className="text-lg font-semibold">{quote.reference} · Version {quote.version_number}</h2><StatusBadge status={quote.status} /></div>
    <p className="mt-2">{quote.package_code} · {formatInrFromPaise(quote.total_minor)}</p>
    <div className="overflow-x-auto"><table className="my-4 w-full text-left text-sm"><caption className="sr-only">Quoted bill of materials and service</caption><thead><tr><th scope="col">Item</th><th scope="col">Quantity</th><th scope="col">Amount</th></tr></thead><tbody>{quote.lines.map(line => <tr key={line.sort_order}><td className="py-2">{line.description}</td><td>{line.quantity} {line.unit}</td><td>{formatInrFromPaise(line.line_total_minor)}</td></tr>)}</tbody></table></div>
    <p className="text-sm">Tax: {formatInrFromPaise(quote.tax_minor)} · Discount: {formatInrFromPaise(quote.discount_minor)}</p>
    {requirement && <p className="my-3 text-sm">Required advance: {formatInrFromPaise(requirement.minimum_advance_minor)} · Verified recorded payments: {formatInrFromPaise(requirement.verified_minor)} · Outstanding total: {formatInrFromPaise(requirement.outstanding_minor)}</p>}
    {error && <ErrorState message={error} />}
    {customer && quote.status === "issued" && <div className="mt-4 space-y-3"><Button disabled={pending} onClick={() => act("acceptance")}>Accept version {quote.version_number} for {formatInrFromPaise(quote.total_minor)}</Button><TextField label="Requested installation change" value={reason} onChange={e => setReason(e.target.value)} maxLength={2000} /><Button variant="secondary" disabled={pending || reason.trim().length < 3} onClick={() => act("revision-requests")}>Request revision</Button></div>}
  </Card>;
}
