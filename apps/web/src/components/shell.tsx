"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { LayoutDashboard, FileText, Calendar, CreditCard, Package, Headphones, Users, Sun, Bell, LogOut, PlusCircle, Truck, Wrench, BarChart3 } from "lucide-react";
import { api } from "@/lib/api";

import type { CurrentUser } from "@/lib/api";
import { homeForRole, isRole } from "@/lib/access";

const LINKS: Record<string, { href: string; label: string; planned?: boolean }[]> = {
  customer: [
    { href: "/customer/subsidies", label: "Subsidy documents" },
    { href: "/customer", label: "Overview" },
    { href: "/customer/enquiries/new", label: "New enquiry" },
    { href: "/customer/quotations", label: "Quotations" },
    { href: "/customer/payments", label: "Payments" },
    { href: "/customer/orders", label: "Orders & warranty" },
    { href: "/customer/installations", label: "Installation work" },
    { href: "/customer/complaints", label: "Complaints" },
    { href: "/customer/equipment", label: "My equipment" },
    { href: "/customer/estimates", label: "Repair estimates" },
    { href: "/customer/bills", label: "Repair bills" },
    { href: "/customer/replacements", label: "Replacements" },
  ],
  technician: [
    { href: "/technician/labour", label: "Labour & payables" },
    { href: "/technician", label: "Assigned jobs" },
    { href: "/technician/surveys", label: "Surveys" },
    { href: "/technician/repairs", label: "Repairs", planned: true },
    { href: "/technician/install", label: "Replacement install" },
  ],
  sales: [
    { href: "/sales/subsidies", label: "Subsidy review" },
    { href: "/sales", label: "Enquiries" },
    { href: "/sales/surveys", label: "Surveys" },
    { href: "/sales/quotations", label: "Quotations" },
    { href: "/sales/installations", label: "Installation scheduling" },
  ],
  warehouse_staff: [
    { href: "/warehouse", label: "Stock" },
    { href: "/warehouse/picking", label: "Picking" },
  ],
  warehouse_manager: [
    { href: "/warehouse", label: "Stock" },
    { href: "/warehouse/approvals", label: "Approvals" },
    { href: "/warehouse/picking", label: "Picking", planned: true },
    { href: "/warehouse/replacements", label: "Replacements" },
  ],
  warehouse_manager: [
    { href: "/warehouse", label: "Stock" },
    { href: "/warehouse/approvals", label: "Approvals", planned: true },
    { href: "/warehouse/replacements", label: "Replacements" },
  ],
  support: [
    { href: "/support", label: "Support records" },
    { href: "/support/lookup", label: "Customer lookup", planned: true },
    { href: "/support/warranty", label: "Warranty" },
    { href: "/support/estimates", label: "Estimates" },
    { href: "/support/replacements", label: "Replacements" },
    { href: "/support/billing", label: "Billing" },
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
  ],
};

export function AppShell({ user, children }: { user: CurrentUser; children: React.ReactNode }) {
  const pathname = usePathname();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
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
    <aside className="dock-sidebar-container" aria-label="Workspace"><nav className="dock-nav-column" aria-label="Workspace navigation">
      <Link href={home} className="dock-brand" aria-label="SolarOps home"><Sun size={25} /></Link>
      {links.map((link) => { const Icon = iconFor(link.href); return <Link key={link.href} href={link.href} className={pathname === link.href ? "dock-item-active" : "dock-nav-btn"} title={link.label + (link.planned ? " — planned" : "")} aria-label={link.label} aria-current={pathname === link.href ? "page" : undefined}><Icon size={20} strokeWidth={2.2} /><span className="dock-tooltip">{link.label}{link.planned ? " · planned" : ""}</span></Link>; })}
    </nav><div className="dock-bottom-column"><button type="button" className="dock-bottom-btn" title="Sign out" aria-label="Sign out" onClick={logout} disabled={pending}><LogOut size={18} /></button></div></aside>
    <div className="app-shell-main"><header className="top-nav-bar"><Link href={home} className="top-nav-tab active"><LayoutDashboard size={17} /><span>Dashboard</span></Link><div className="top-nav-right"><div className="top-user-pill"><span className="top-user-avatar">{user.full_name.split(" ").filter(Boolean).map(n => n[0]).join("").slice(0,2).toUpperCase()}</span><div className="top-user-meta"><span className="top-user-name">{user.full_name}</span><span className="top-user-role">{user.role.replaceAll("_", " ")}</span></div></div><button type="button" className="top-icon-btn" title="Notifications are not implemented" aria-label="Notifications unavailable" disabled><Bell size={18} /></button><button className="top-signout" disabled={pending} onClick={logout}>Sign out</button></div></header>
    {process.env.NEXT_PUBLIC_SOLAROPS_ENV === "development" && <p className="actual-preview-banner">Isolated local preview · acceptance-test records · no real payments or goods movements</p>}<main className="app-shell-content">{error && <div role="alert" className="auth-error-note">{error}</div>}{children}</main></div>
  </div>;
}
