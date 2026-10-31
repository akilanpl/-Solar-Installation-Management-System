"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Plus, Layers, Sun, FileText, Calendar, Package, Wrench, Users, ArrowRight } from "lucide-react";
import type { CurrentUser } from "@/lib/api";
import { api } from "@/lib/api";
import type { components } from "@/generated/schema";
import { ErrorState, LoadingState } from "@/components/ui";
import { formatInrFromPaise } from "@/lib/format";

const TEXT: Record<string, { title: [string,string]; sub: string; action: string; href: string }> = {
 customer: { title:["What are your", "plans for today?"], sub:"Track your rooftop solar enquiry, quotations, installation work and recorded payment milestones.", action:"New Solar Enquiry", href:"/customer/enquiries/new" },
 sales: { title:["Ready to review", "feasibility today?"], sub:"Screen incoming solar enquiries, review approved surveys and manage customer quotations.", action:"Review enquiries", href:"/sales" },
 technician: { title:["Ready for your", "site surveys today?"], sub:"Review assigned work, record real site measurements and upload installation evidence.", action:"View field surveys", href:"/technician/surveys" },
 warehouse_staff: { title:["What solar inventory", "needs dispatch today?"], sub:"Review actual inventory, receive equipment and validate physical stock movements.", action:"View picking queue", href:"/warehouse/picking" },
 warehouse_manager: { title:["What solar inventory", "needs dispatch today?"], sub:"Review actual inventory, approved stock operations and replenishment requests.", action:"View picking queue", href:"/warehouse/picking" },
 support: { title:["How can we help", "customers today?"], sub:"Triage customer complaints, review repair progress and consult authorized customer snapshots.", action:"Customer intelligence", href:"/support/intelligence" },
 admin: { title:["Solar Operations &", "your team today?"], sub:"Manage the authorized personnel roster and navigate company operations.", action:"Manage employees", href:"#employee-roster" },
};
type Metric = { label:string; value:string; detail:string };
export function DashboardOverview({ user }: { user: CurrentUser }) {
 const [metrics,setMetrics] = useState<Metric[] | null>(null);
 const [error,setError] = useState<string | null>(null);
 const cfg=TEXT[user.role] ?? TEXT.customer;
 useEffect(() => {
  let cancelled=false;
  async function load() {
   setError(null);
   try {
    let result:Metric[];
    if(user.role === "customer" || user.role === "sales") {
     const [enquiries,quotes,orders] = await Promise.all([api<components["schemas"]["EnquiryList"]>("/api/v1/enquiries?page_size=1"),api<components["schemas"]["QuotationList"]>("/api/v1/quotations?page_size=1"),api<components["schemas"]["OrderList"]>("/api/v1/orders?page_size=1")]);
     result=[{label:user.role==="customer"?"My Enquiries":"Enquiry Funnel",value:String(enquiries.total),detail:"Recorded submissions"},{label:"Quotations",value:String(quotes.total),detail:"Issued records, including revisions"},{label:"Confirmed orders",value:String(orders.total),detail:"Persisted order records"}];
    } else if(user.role === "admin") {
     const [rows,finance]=await Promise.all([api<components["schemas"]["EmployeeResponse"][]>("/api/v1/admin/employees"),api<components["schemas"]["DashboardResponse"]>("/api/v1/finance/dashboard")]);
     result=[{label:"Operations Staff",value:String(rows.length),detail:"Company personnel"},{label:"Active accounts",value:String(rows.filter(r=>r.is_active).length),detail:"Currently enabled staff"},{label:"Recognized revenue",value:formatInrFromPaise(finance.recognized_revenue_minor),detail:"Source-linked recognition, separate from cash and advances"}];
    } else if(user.role.startsWith("warehouse")) {
     const [stock,delivery]=await Promise.all([api<components["schemas"]["StockLevelResponse"][]>("/api/v1/stock"),api<components["schemas"]["DeliveryResponse"][]>("/api/v1/deliveries")]);
     result=[{label:"Inventory positions",value:String(stock.length),detail:"Component and location balances"},{label:"Deliveries",value:String(delivery.length),detail:"Recorded delivery records"},{label:"In transit",value:String(delivery.filter(r=>r.status==="in_transit").length),detail:"Dispatched, not confirmed"}];
    } else if(user.role === "support") {
     const [jobs,tickets]=await Promise.all([api<components["schemas"]["JobResponse"][]>("/api/v1/jobs"),api<{total:number}>("/api/v1/tickets?page_size=1")]);
     result=[{label:"Installation records",value:String(jobs.length),detail:"Authorized installation records"},{label:"Completed jobs",value:String(jobs.filter(r=>r.status==="completed").length),detail:"Recorded completion"},{label:"Support tickets",value:String(tickets.total),detail:"Authorized complaint records"}];
    } else {
     const jobs=await api<components["schemas"]["JobResponse"][]>("/api/v1/jobs");
     result=[{label:user.role==="technician"?"Assigned jobs":"Installation records",value:String(jobs.length),detail:"Authorized installation records"},{label:"Completed jobs",value:String(jobs.filter(r=>r.status==="completed").length),detail:"Recorded completion"},{label:"Customer acknowledgments",value:String(jobs.filter(r=>r.signature).length),detail:"Authenticated acceptance records"}];
    }
    if(!cancelled)setMetrics(result);
   }catch(e){if(!cancelled)setError(e instanceof Error?e.message:"Dashboard data unavailable.");}
  }
  load();return()=>{cancelled=true;};
 },[user.role]);
 const icons=[Layers,FileText,user.role==="technician"?Wrench:user.role.startsWith("warehouse")?Package:Users];
 return <div className="dash-container actual-dashboard-overview"><section className="dash-hero-row" aria-label="Dashboard overview"><div className="dash-greeting-box"><h1 className="dash-greeting-title"><span className="dash-greeting-header-line"><span>Hi, {user.full_name.split(" ")[0]}!</span><span className="dash-avatar-cluster"><span className="dash-avatar-ring"><Sun size={22}/></span></span></span><span>{cfg.title[0]}</span><span>{cfg.title[1]}</span></h1><p className="dash-greeting-sub">{cfg.sub}</p></div><div className="dash-feature-cards-grid"><Link className="dash-feature-card create-new" href={cfg.href} aria-label={cfg.action}><div className="dash-create-icon-box"><Plus size={22}/></div><span className="actual-create-label">{cfg.action}</span></Link>{metrics?.map((metric,i)=>{const Icon=icons[i];return <div className="dash-feature-card" key={metric.label}><Icon size={28} color="#4f46e5"/><h2 className="dash-feature-title">{metric.label}</h2><strong className="actual-metric-value">{metric.value}</strong><p className="dash-feature-sub">{metric.detail}</p></div>;})}{!metrics&&!error&&<LoadingState label="Loading dashboard"/>}{error&&<ErrorState message={error}/>}</div></section><div className="actual-overview-note"><Calendar size={16}/><span>Appointments and statuses reflect recorded workflows. Provider availability is shown in each workspace.</span><ArrowRight size={16}/></div></div>;
}
