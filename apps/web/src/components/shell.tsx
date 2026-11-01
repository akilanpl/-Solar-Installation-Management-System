"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { LayoutDashboard, FileText, Calendar, CreditCard, Package, Headphones, Users, Sun, Bell, LogOut, PlusCircle, Truck, Wrench, BarChart3, Settings, ScanBarcode } from "lucide-react";
import { ShellPanels, type ShellPanel } from "@/components/recovery/shell-panels";
import { api } from "@/lib/api";

import type { CurrentUser } from "@/lib/api";
import { homeForRole, isRole } from "@/lib/access";

const LINKS: Record<string, { href: string; label: string; planned?: boolean }[]> = {
  customer: [
    { href: "/customer", label: "Overview" },
    { href: "/customer/store", label: "Solar store & packages" },
    { href: "/customer/subsidies", label: "Subsidy documents" },
    { href: "/customer/enquiries/new", label: "New enquiry" },
    { href: "/customer/quotations", label: "Quotations" },
    { href: "/customer/payments", label: "Payments" },
    { href: "/customer/orders", label: "Orders & warranty" },
    { href: "/customer/installations", label: "Installation work" },
    { href: "/customer/complaints", label: "Complaints" },
    { href: "/customer/equipment", label: "My equipment" },
    { href: "/customer/generation", label: "Generation" },
    { href: "/customer/estimates", label: "Repair estimates" },
    { href: "/customer/bills", label: "Repair bills" },
    { href: "/customer/replacements", label: "Replacements" },
    { href: "/customer/warranty-extensions", label: "Warranty extensions" },
    { href: "/security", label: "Security" },
  ],
  technician: [
    { href: "/technician/labour", label: "Labour & payables" },
    { href: "/technician", label: "Assigned jobs" },
    { href: "/technician/surveys", label: "Surveys" },
    { href: "/technician/repairs", label: "Repairs" },
    { href: "/technician/install", label: "Replacement install" },
    { href: "/technician/offline", label: "Offline field work" },
    { href: "/security", label: "Security" },
  ],
  sales: [
    { href: "/sales/subsidies", label: "Subsidy review" },
    { href: "/sales", label: "Enquiries" },
    { href: "/sales/surveys", label: "Surveys" },
    { href: "/sales/quotations", label: "Quotations" },
    { href: "/sales/installations", label: "Installation scheduling" },
    { href: "/security", label: "Security" },
  ],
  warehouse_staff: [
    { href: "/warehouse", label: "Stock" },
    { href: "/warehouse/picking", label: "Picking" },
    { href: "/warehouse/replacements", label: "Replacements" },
    { href: "/security", label: "Security" },
  ],
  warehouse_manager: [
    { href: "/warehouse", label: "Stock" },
    { href: "/warehouse/approvals", label: "Approvals" },
    { href: "/warehouse/replacements", label: "Replacements" },
    { href: "/security", label: "Security" },
  ],
  support: [
    { href: "/support", label: "Support records" },
    { href: "/support/lookup", label: "Customer lookup" },
    { href: "/support/intelligence", label: "Intelligence" },
    { href: "/support/weather", label: "Weather ops" },
    { href: "/support/warranty", label: "Warranty" },
    { href: "/support/estimates", label: "Estimates" },
    { href: "/support/replacements", label: "Replacements" },
    { href: "/support/billing", label: "Billing" },
    { href: "/support/extensions", label: "Extension reviews" },
    { href: "/security", label: "Security" },
  ],
  admin: [
    { href: "/admin", label: "Employees" },
    { href: "/sales", label: "Enquiries" },
    { href: "/sales/surveys", label: "Surveys" },
    { href: "/sales/quotations", label: "Quotations" },
    { href: "/sales/installations", label: "Installation scheduling" },
    { href: "/warehouse", label: "Inventory logistics" },
    { href: "/support", label: "Customer support" },
    { href: "/admin/pricing", label: "Warranty & pricing" },
    { href: "/admin/reports", label: "Finance & reports" },
    { href: "/support/extensions", label: "Extension reviews" },
    { href: "/security", label: "Security" },
  ],
};

export function AppShell({ user, children }: { user: CurrentUser; children: React.ReactNode }) {
  const pathname = usePathname();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [panel, setPanel] = useState<ShellPanel>(null);
  useEffect(()=>{try{const p=JSON.parse(localStorage.getItem(`solarops-appearance:${user.id}`)??"{}");document.documentElement.classList.toggle("recovery-compact",p.compact===true);document.documentElement.classList.toggle("recovery-reduced-motion",p.reduced===true);}catch{/* Local appearance preferences are optional. */}},[user.id]);
  const links = LINKS[user.role] ?? [];
  const home = isRole(user.role) ? homeForRole(user.role) : "/login";
  function iconFor(href:string) {
    if(href.endsWith("/enquiries/new"))return PlusCircle;
    if(href.includes("quotations"))return FileText;
    if(href.includes("payments"))return CreditCard;
    if(href.includes("surveys"))return Calendar;
    if(href.includes("support"))return Headphones;
    if(href.includes("orders"))return Truck;
    if(href.includes("installations")||href.includes("repairs"))return Wrench;
    if(href.includes("warehouse"))return Package;
    if(href.includes("reports"))return BarChart3;
    if(href==="/admin")return Users;
    return LayoutDashboard;
  }
  async function logout() {
    setPending(true); setError(null);
    try { await api("/api/v1/auth/logout", { method: "POST" }); window.location.assign("/login"); }
    catch(e) { setError(e instanceof Error ? e.message : "Could not sign out. Please retry."); setPending(false); }
  }
  return <div className="app-shell-layout">
    <aside className="dock-sidebar-container liquid-glass-dock" aria-label="Workspace"><div className="liquid-glass-specular-sheen" aria-hidden="true"/><nav className="dock-nav-column" aria-label="Workspace navigation">
      <Link href={home} className="dock-brand" aria-label="SolarOps home"><Sun size={25} /></Link>
      {links.map((link) => { const Icon = iconFor(link.href); return <Link key={link.href} href={link.href} className={pathname === link.href ? "dock-item-active" : "dock-nav-btn"} title={link.label + (link.planned ? " — planned" : "")} aria-label={link.label} aria-current={pathname === link.href ? "page" : undefined}><Icon size={20} strokeWidth={2.2} />{pathname===link.href&&<span className="dock-active-glow" aria-hidden="true"/>}<span className="dock-tooltip">{link.label}{link.planned ? " · planned" : ""}</span></Link>; })}
      {["technician","warehouse_staff","warehouse_manager","admin"].includes(user.role)&&<button type="button" className="dock-nav-btn dock-scan-btn" aria-label="Equipment scanner and photo evidence" title="Equipment scanner and photo evidence" onClick={()=>setPanel("scanner")}><ScanBarcode size={20}/><span className="dock-scan-badge">SCAN</span></button>}
      <button type="button" className="dock-nav-btn dock-ai-btn" aria-label="Open solar assistant" title="Solar assistant" onClick={()=>setPanel("assistant")}><Image src="/dock-ai-icon.png" alt="" width={24} height={24} className="dock-ai-png-icon"/><span className="dock-ai-badge">AI</span></button>
    </nav><div className="dock-bottom-column"><button type="button" className="dock-bottom-btn" title="Sign out" aria-label="Sign out" onClick={logout} disabled={pending}><LogOut size={18} /></button></div></aside>
    <div className="app-shell-main"><header className="top-nav-bar"><Link href={home} className="top-nav-tab active"><LayoutDashboard size={17} /><span>Dashboard</span></Link><div className="top-nav-right"><span className="recovery-account-name">{user.full_name}</span><button type="button" className="top-icon-btn" title="Notifications" aria-label="Open notifications" aria-haspopup="dialog" onClick={()=>setPanel("notifications")}><Bell size={18}/></button><button type="button" className="top-icon-btn" title="Account settings" aria-label="Open account settings" aria-haspopup="dialog" onClick={()=>setPanel("settings")}><Settings size={18}/></button><button className="top-signout" disabled={pending} onClick={logout}>Sign out</button></div></header>
    {process.env.NEXT_PUBLIC_SOLAROPS_ENV === "development" && <p className="actual-preview-banner">Isolated local preview · acceptance-test records · no real payments or goods movements</p>}<main className="app-shell-content">{pathname===home&&<section className="recovery-welcome"><div><span>SOLAROPS · YOUR CONNECTED WORKSPACE</span><h1>Hello, {user.full_name}</h1><p>Solar projects, people and records — together in one place.</p></div><div className="recovery-role-chip">{user.role.replaceAll("_"," ")}</div></section>}{error && <div role="alert" className="auth-error-note">{error}</div>}{children}</main></div>
    <ShellPanels panel={panel} onClose={()=>setPanel(null)} user={user}/>
  </div>;
}
