"use client";

import { useCallback, useEffect, useState } from "react";
import type { components } from "@/generated/schema";
import { api } from "@/lib/api";
import { decimalRupeesToPaise, formatInrFromPaise } from "@/lib/format";
import {RazorpayCheckout} from "@/components/razorpay-checkout";
import { PaymentAvailability } from "@/components/payment-availability";
import { WorkflowForm, Input, post, value } from "@/components/workflow-form";
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge, TextField } from "@/components/ui";

type Quote = components["schemas"]["QuotationResponse"];
function money(data:FormData,key:string) { const amount=decimalRupeesToPaise(value(data,key)); if(amount===null) throw new Error("Enter a valid rupee amount with at most two decimal places."); return amount; }
type Requirement = components["schemas"]["PaymentRequirementResponse"];
export function Quotations({ customer = true,showPayments=false }: { customer?: boolean;showPayments?:boolean }) {
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
  return <><PageHeader title="Quotations and payments" description="Review the exact issued version and recorded payment requirement. Provider checkout is test-only and stays blocked until configured." />
    {error && <ErrorState message={error} onRetry={load} />}
    {!items && !error && <LoadingState />}
    {items?.length === 0 && <EmptyState title="No quotations" body="An approved survey is required before sales can issue a quotation." />}
    {showPayments && items?.length===0 && <PaymentAvailability/>}
    <div className="space-y-5">{items?.map(quote => <QuoteCard key={quote.id} quote={quote} customer={customer} showPayments={showPayments} onChange={load} />)}</div>
    {items && total > 20 && <div className="mt-4 flex items-center gap-3"><Button disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button><span>Page {page}</span><Button disabled={page * 20 >= total} onClick={() => setPage(page + 1)}>Next</Button></div>}
  </>;
}
function QuoteCard({ quote, customer, onChange,showPayments }: { quote: Quote; customer: boolean; onChange: () => void;showPayments:boolean }) {
  const [requirement, setRequirement] = useState<Requirement | null>(null);
  const [reason, setReason] = useState("");
  const [category,setCategory] = useState<components["schemas"]["RevisionRequestCreate"]["category"]>("installation");
  const [requests,setRequests] = useState<components["schemas"]["RevisionRequestResponse"][]>([]);
  const [packages,setPackages] = useState<components["schemas"]["PackageResponse"][]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  useEffect(() => {
    api<Requirement>(`/api/v1/quotations/${quote.id}/payment-requirement`).then(setRequirement).catch(e => setError(e.message));
    api<components["schemas"]["RevisionRequestResponse"][]>(`/api/v1/quotations/${quote.id}/revision-requests`).then(setRequests).catch(e=>setError(e.message));
    if(!customer)api<components["schemas"]["PackageResponse"][]>("/api/v1/packages").then(setPackages).catch(e=>setError(e.message));
  }, [quote, customer]);
  async function act(action: "acceptance" | "revision-requests") {
    setPending(true); setError(null);
    try {
      const body: components["schemas"]["RevisionRequestCreate"] = { category, request_text: reason };
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
    {showPayments && requirement && <><PaymentAvailability outstandingMinor={requirement.outstanding_minor} quotationRef={quote.reference}/>{customer&&["issued","accepted"].includes(quote.status)&&<RazorpayCheckout quotationId={quote.id} outstandingMinor={requirement.outstanding_minor} onChange={onChange}/>}</>}
    {error && <ErrorState message={error} />}
    {!customer && ["issued","accepted"].includes(quote.status) && <WorkflowForm title="Record an authorized cash receipt" label="Record verified cash received" onSaved={onChange} submit={(d,key)=>post("/api/v1/payments/cash-receipts",{quotation_id:quote.id,amount_minor:money(d,"amount"),receipt_reference:value(d,"receipt")} satisfies components["schemas"]["CashReceiptCreate"],key)}><Input label="Amount actually received (₹)" name="amount" type="number" min="0.01" max="1000000" step="0.01"/><Input label="Actual receipt reference" name="receipt" minLength={3} maxLength={80}/><p className="auth-input-note">Record only cash actually received and verified by authorized staff.</p></WorkflowForm>}
    {!customer && quote.status === "accepted" && <WorkflowForm title="Confirm accepted quotation as an order" label="Confirm order" onSaved={onChange} submit={(_d,key)=>post("/api/v1/orders",{quotation_id:quote.id} satisfies components["schemas"]["OrderCreate"],key)}><p className="auth-input-note">The server checks verified advance requirements and prevents duplicate orders.</p></WorkflowForm>}
    {requests.length>0&&<div className="actual-revision-requests"><h3 className="font-semibold">Recorded revision requests</h3>{requests.map(request=><p key={request.id}>{request.category}: {request.request_text} · {request.status}</p>)}</div>}
    {!customer && ["issued","accepted"].includes(quote.status) && <WorkflowForm title="Issue a quotation revision" label="Issue revised version" onSaved={onChange} submit={(d,key)=>post(`/api/v1/quotations/${quote.id}/revisions`,{package_code:value(d,"package"),discount_minor:money(d,"discount"),revision_request_id:value(d,"request")||null} satisfies components["schemas"]["QuotationRevisionCreate"],key)}><label className="actual-field"><span>Revised package</span><select name="package" defaultValue="" required><option value="" disabled>Choose a current package</option>{packages.filter(p=>p.is_active).map(p=><option key={p.code} value={p.code}>{p.name}</option>)}</select></label><label className="actual-field"><span>Related revision request (optional)</span><select name="request" defaultValue=""><option value="">General revision</option>{requests.map(request=><option key={request.id} value={request.id}>{request.category}: {request.request_text}</option>)}</select></label><Input label="Revised discount (₹)" name="discount" type="number" min="0" step="0.01" max="1000000"/><p className="auth-input-note">The server preserves prior versions, accepted prices and verified payment history.</p></WorkflowForm>}
    {customer && quote.status === "issued" && <div className="mt-4 space-y-3"><Button disabled={pending} onClick={() => act("acceptance")}>Accept version {quote.version_number} for {formatInrFromPaise(quote.total_minor)}</Button><label className="actual-field"><span>Requested change category</span><select value={category} onChange={e=>setCategory(e.target.value as typeof category)}><option value="installation">Installation</option><option value="capacity">Capacity</option><option value="grid">Grid connection</option><option value="components">Components</option><option value="pricing">Pricing</option></select></label><TextField label="Requested change" value={reason} onChange={e => setReason(e.target.value)} maxLength={2000} /><Button variant="secondary" disabled={pending || reason.trim().length < 3} onClick={() => act("revision-requests")}>Request revision</Button></div>}
  </Card>;
}
