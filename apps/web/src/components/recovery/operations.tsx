"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowUpRight, BarChart3, Calendar, CheckCircle2, FileText, Layers, Package, RefreshCw, ShieldCheck, Truck, Wrench } from "lucide-react";
import type { components } from "@/generated/schema";
import { api } from "@/lib/api";
import { formatInrFromPaise, formatWhen } from "@/lib/format";
import { ErrorState, LoadingState } from "@/components/ui";
import { jobCompletion, profitBreakdown } from "./operations-data";
import styles from "./operations.module.css";

type Schema = components["schemas"];
type Activity = { id: string; title: string; status: string; detail: string; href: string };
type Board = { title: string; description: string; focus: string; focusText: string; href: string; action: string;
  activities: Activity[]; progress: { label: string; count: number; total: number }[]; empty: string };

/** Latest e73c795 DashboardView bento composition, backed by authorized records. */
export function OperationsDashboard({ role }: { role: "sales" | "technician" | "warehouse_staff" | "warehouse_manager" }) {
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setError(null); setBoard(null);
    async function load(): Promise<Board> {
      if (role === "sales") {
        const [enquiries, surveys] = await Promise.all([
          api<Schema["EnquiryList"]>("/api/v1/enquiries?page=1&page_size=50"),
          api<Schema["SurveyList"]>("/api/v1/surveys?page=1&page_size=50"),
        ]);
        return { title: "Your sales workspace", description: "A clear view of the latest enquiries and engineering reviews.",
          focus: "From first conversation to a considered proposal", focusText: "Review the customer’s roof and requirements, then prepare a quotation from their approved survey.", href: "/sales/surveys", action: "Review site surveys",
          activities: enquiries.items.slice(0, 4).map(row => ({ id: row.id, title: row.contact_name, status: row.status,
            detail: `${row.reference} · ${formatWhen(row.created_at)}`, href: `/sales/enquiries/${row.id}` })),
          progress: [{ label: "Qualified enquiries", count: enquiries.items.filter(row => row.status === "qualified").length, total: enquiries.items.length },
            { label: "Approved surveys", count: surveys.items.filter(row => row.status === "approved").length, total: surveys.items.length }],
          empty: "Customer enquiries will appear here when they are submitted." };
      }
      if (role === "technician") {
        const jobs = await api<Schema["JobResponse"][]>("/api/v1/jobs");
        const completion = jobCompletion(jobs);
        return { title: "Field engineering", description: "Your assigned installation work, with evidence and customer acceptance kept together.",
          focus: "Every site visit leaves a clear record", focusText: "Open an assigned job to check equipment, upload photographs and complete the customer acknowledgment.", href: "/technician/surveys", action: "Open field surveys",
          activities: jobs.slice(0, 4).map(job => ({ id: job.id, title: job.reference, status: job.status,
            detail: job.slot_starts_at ? formatWhen(job.slot_starts_at) : "Visit time not scheduled", href: "#assigned-installation-jobs" })),
          progress: [{ label: "Completed installations", count: completion.complete, total: completion.total },
            { label: "Customer acknowledgments", count: jobs.filter(job => Boolean(job.signature)).length, total: jobs.length }],
          empty: "Your assigned installation jobs will appear here." };
      }
      const [deliveries, stock] = await Promise.all([
        api<Schema["DeliveryResponse"][]>("/api/v1/deliveries"),
        api<Schema["StockLevelResponse"][]>("/api/v1/stock"),
      ]);
      return { title: "Inventory & dispatch", description: `${stock.length} recorded component and location positions. Stock quantities remain in their original units.`,
        focus: "The right equipment, with exact unit custody", focusText: "Pick received equipment against an order, verify its serial identities and track the dispatch through customer confirmation.", href: "/warehouse/picking", action: "Open picking workspace",
        activities: deliveries.slice(0, 4).map(delivery => ({ id: delivery.id, title: delivery.reference,
          status: delivery.status, detail: formatWhen(delivery.created_at), href: "/warehouse/picking" })),
        progress: [{ label: "Confirmed deliveries", count: deliveries.filter(row => row.status === "confirmed").length, total: deliveries.length },
          { label: "In-transit deliveries", count: deliveries.filter(row => row.status === "in_transit").length, total: deliveries.length }],
        empty: "Recorded deliveries will appear here after equipment is picked." };
    }
    load().then(result => { if (active) setBoard(result); }).catch(caught => {
      if (active) setError(caught instanceof Error ? caught.message : "Workspace activity is unavailable.");
    });
    return () => { active = false; };
  }, [role, revision]);
  return <section className={styles.dashboard} aria-label="Operational overview">
    <div className={styles.heading}><div><span className={styles.eyebrow}>SOLAROPS / OPERATIONS</span><h2>{board?.title ?? "Your operational workspace"}</h2><p>{board?.description ?? "Loading recorded activity for your workspace."}</p></div><button className={styles.refresh} onClick={() => setRevision(value => value + 1)} aria-label="Refresh operational overview"><RefreshCw size={16}/>Refresh</button></div>
    {error ? <ErrorState message={error} onRetry={() => setRevision(value => value + 1)}/> : !board ? <LoadingState label="Loading operational overview"/> : <div className={styles.bento}>
      <article className={styles.focus}><div className={styles.focusIcon}>{role === "sales" ? <Layers/> : role === "technician" ? <Wrench/> : <Package/>}</div><span className={styles.kicker}>WORKSPACE FOCUS</span><h3>{board.focus}</h3><p>{board.focusText}</p><Link href={board.href}>{board.action}<ArrowUpRight size={17}/></Link><div className={styles.orbit} aria-hidden="true"/></article>
      <article className={styles.card}><div className={styles.cardHeading}><h3>Recorded progress</h3><ShieldCheck size={18}/></div><p className={styles.caption}>{role === "sales" ? "Within the latest loaded records, up to 50 per list." : "Across the records available to your account."}</p><div className={styles.progressList}>{board.progress.map(item => <div key={item.label}><div className={styles.progressLabel}><span>{item.label}</span><strong>{item.count} / {item.total}</strong></div>{item.total ? <progress max={item.total} value={item.count} aria-label={item.label}/> : <p className={styles.noData}>No records yet</p>}</div>)}</div></article>
      <article className={styles.card}><div className={styles.cardHeading}><h3>{role === "sales" ? "Latest enquiries" : role === "technician" ? "Assigned visits" : "Recent dispatches"}</h3><Calendar size={18}/></div><div className={styles.activityList}>{board.activities.length ? board.activities.map(item => <Link href={item.href} className={styles.activity} key={item.id}><span className={styles.activityIcon}>{role.startsWith("warehouse") ? <Truck size={17}/> : <FileText size={17}/>}</span><span><strong>{item.title}</strong><small>{item.detail}</small></span><span className={styles.status}>{item.status.replaceAll("_", " ")}</span></Link>) : <p className={styles.noData}>{board.empty}</p>}</div></article>
    </div>}
  </section>;
}

/** e73c795 AdminAnalyticsHub hierarchy and card proportions; actual ledger totals. */
export function ExecutiveAnalytics() {
  const [data, setData] = useState<Schema["DashboardResponse"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [view, setView] = useState<"financials" | "jobs">("financials");
  useEffect(() => {
    let active = true; setError(null); setData(null);
    api<Schema["DashboardResponse"]>("/api/v1/finance/dashboard").then(result => { if (active) setData(result); }).catch(caught => { if (active) setError(caught instanceof Error ? caught.message : "Financial overview is unavailable."); });
    return () => { active = false; };
  }, [revision]);
  const totals = data ? [{ label: "Recognized revenue", amount: data.recognized_revenue_minor, detail: "Revenue recognized under approved policy" },
    { label: "Recorded cash", amount: data.cash_minor, detail: "Cash receipts less recorded settlements" },
    { label: "Customer advances", amount: data.advances_minor, detail: "Received advances, separate from revenue" },
    { label: "Receivables", amount: data.receivables_minor, detail: "Outstanding source-linked customer bills" }] : [];
  return <section className={styles.executive} aria-label="Executive analytics">
    <header className={styles.analyticsHeader}><div><span className={styles.recordedBadge}><ShieldCheck size={13}/>Recorded financial state</span><h2>Company-wide executive analytics</h2><p>A clear view of recognized revenue, cash and the costs behind each job.</p></div><div className={styles.headerActions}><button className={styles.refresh} onClick={() => setRevision(value => value + 1)} aria-label="Refresh executive analytics"><RefreshCw size={16}/></button><Link className={styles.export} href="/admin/reports"><BarChart3 size={16}/>Finance & reports<ArrowUpRight size={15}/></Link></div></header>
    <div className={styles.tabs} aria-label="Analytics views">{(["financials", "jobs"] as const).map(tab => <button type="button" key={tab} aria-pressed={view === tab} onClick={() => setView(tab)} className={view === tab ? styles.activeTab : ""}>{tab === "financials" ? "Financial overview" : "Job economics"}</button>)}</div>
    {error ? <ErrorState message={error} onRetry={() => setRevision(value => value + 1)}/> : !data ? <LoadingState label="Loading executive analytics"/> : <>
      <div className={styles.metricGrid}>{totals.map(total => <article className={styles.metric} key={total.label}><span>{total.label}<ArrowUpRight size={15}/></span><strong>{formatInrFromPaise(total.amount)}</strong><p>{total.detail}</p></article>)}</div>
      {view === "financials" ? <div className={styles.analyticsGrid}><article className={styles.card}><div className={styles.cardHeading}><h3>Cash and commitments</h3><Layers size={18}/></div><dl className={styles.balanceRows}><div><dt>Recorded payables</dt><dd>{formatInrFromPaise(data.payables_minor)}</dd></div><div><dt>Deferred revenue</dt><dd>{formatInrFromPaise(data.deferred_revenue_minor)}</dd></div><div><dt>Jobs requiring reconciliation</dt><dd>{data.outstanding_jobs}</dd></div></dl><Link className={styles.textLink} href="/admin/reports">Review source records<ArrowUpRight size={15}/></Link></article><article className={`${styles.card} ${styles.unavailable}`}><BarChart3 size={30}/><h3>Historical revenue trend</h3><p>A historical time series is unavailable. Current recorded totals are shown above.</p><span>Historical chart unavailable</span></article></div> : <article className={styles.card}><div className={styles.cardHeading}><h3>Revenue, cost & job profitability</h3><CheckCircle2 size={18}/></div><p className={styles.caption}>Each row reflects its recorded source events. Incomplete jobs may still be missing costs.</p>{data.jobs.length ? <div className={styles.jobRows}>{data.jobs.map(job => {
        const summary = profitBreakdown(job); const scale = Math.max(Math.abs(summary.revenue), Math.abs(summary.cost), 1);
        return <div className={styles.jobRow} key={job.order_id}><div className={styles.jobLabel}><strong>{job.reference}</strong><span className={summary.complete ? styles.complete : styles.incomplete}>{summary.complete ? "Reconciled" : "Incomplete"}</span></div><div className={styles.barRow}><span>Revenue</span><div><i style={{ width: `${Math.max(0, summary.revenue) / scale * 100}%` }}/></div><strong>{formatInrFromPaise(summary.revenue)}</strong></div><div className={styles.barRow}><span>Cost</span><div><i className={styles.costBar} style={{ width: `${Math.max(0, summary.cost) / scale * 100}%` }}/></div><strong>{formatInrFromPaise(summary.cost)}</strong></div><p className={summary.profit < 0 ? styles.loss : styles.profit}>Recorded profit: {formatInrFromPaise(summary.profit)}</p>{!summary.complete && <p className={styles.caption}>Missing: {job.missing.join(", ") || "Reconciliation pending"}</p>}</div>;
      })}</div> : <p className={styles.noData}>No source-linked job financial records yet.</p>}</article>}
    </>}
  </section>;
}
