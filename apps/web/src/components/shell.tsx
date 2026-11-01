"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import type { CurrentUser } from "@/lib/api";
import { homeForRole, isRole } from "@/lib/access";

const LINKS: Record<string, { href: string; label: string; planned?: boolean }[]> = {
  customer: [
    { href: "/customer", label: "Overview" },
    { href: "/customer/enquiries/new", label: "New enquiry" },
    { href: "/customer/quotations", label: "Quotations" },
    { href: "/customer/payments", label: "Payments" },
    { href: "/customer/installations", label: "Installation work" },
    { href: "/customer/complaints", label: "Complaints" },
  ],
  technician: [
    { href: "/technician", label: "Assigned jobs" },
    { href: "/technician/surveys", label: "Surveys", planned: true },
    { href: "/technician/repairs", label: "Repairs" },
  ],
  sales: [
    { href: "/sales", label: "Enquiries" },
    { href: "/sales/surveys", label: "Surveys", planned: true },
    { href: "/sales/quotations", label: "Quotations" },
  ],
  warehouse_staff: [
    { href: "/warehouse", label: "Stock" },
    { href: "/warehouse/picking", label: "Picking", planned: true },
  ],
  warehouse_manager: [
    { href: "/warehouse", label: "Stock" },
    { href: "/warehouse/approvals", label: "Approvals", planned: true },
  ],
  support: [
    { href: "/support", label: "Tickets" },
    { href: "/support/lookup", label: "Customer lookup", planned: true },
  ],
  admin: [
    { href: "/admin", label: "Employees" },
    { href: "/sales", label: "Enquiries" },
    { href: "/admin/reports", label: "Reports", planned: true },
  ],
};

export function AppShell({ user, children }: { user: CurrentUser; children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const links = LINKS[user.role] ?? [];
  const home = isRole(user.role) ? homeForRole(user.role) : "/login";

  const nav = (
    <nav aria-label="Workspace" className="flex flex-col gap-1">
      {links.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            onClick={() => setOpen(false)}
            className={`rounded-md px-3 py-2 text-sm ${active ? "bg-moss-800 text-white" : "text-moss-50 hover:bg-moss-800"}`}
          >
            {link.label}
            {link.planned ? <span className="ml-2 text-[10px] uppercase tracking-wide opacity-70">Planned</span> : null}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <div className="min-h-screen md:grid md:grid-cols-[240px_1fr]">
      <aside className="hidden bg-moss-900 text-white md:flex md:flex-col md:px-4 md:py-6">
        <Link href={home} className="px-3 text-lg font-semibold">
          SolarOps
        </Link>
        <p className="px-3 pb-6 text-xs text-moss-100">SunPower Solutions</p>
        {nav}
      </aside>
      <div>
        <header className="flex items-center justify-between border-b border-moss-200 bg-white px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="rounded-md border border-moss-200 px-3 py-2 text-sm md:hidden"
              aria-expanded={open}
              aria-controls="mobile-nav"
              onClick={() => setOpen((value) => !value)}
            >
              Menu
            </button>
            <div>
              <p className="text-sm font-semibold">{user.full_name}</p>
              <p className="text-xs text-moss-800/80">
                {user.role.replaceAll("_", " ")}
                {user.employee_code ? ` · ${user.employee_code}` : ""}
              </p>
            </div>
          </div>
          <form action="/logout" method="post" onSubmit={(event) => event.preventDefault()}>
            <LogoutButton />
          </form>
        </header>
        {open ? (
          <div id="mobile-nav" className="border-b border-moss-800 bg-moss-900 p-4 md:hidden">
            {nav}
          </div>
        ) : null}
        <main className="mx-auto w-full max-w-5xl px-4 py-6">{children}</main>
      </div>
    </div>
  );
}

function LogoutButton() {
  return (
    <button
      type="button"
      className="text-sm font-semibold text-moss-800"
      onClick={async () => {
        const { api } = await import("@/lib/api");
        await api("/api/v1/auth/logout", { method: "POST" });
        window.location.assign("/login");
      }}
    >
      Sign out
    </button>
  );
}
