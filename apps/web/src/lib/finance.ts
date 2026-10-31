import type { components } from "@/generated/schema";
import { api } from "@/lib/api";

export type FinanceRecord = components["schemas"]["RecordResponse"];
export type FinanceDashboard = components["schemas"]["DashboardResponse"];
export type FinanceJournal = components["schemas"]["JournalResponse"];
export type FinanceInvoiceCreate =
  components["schemas"]["FinanceInvoiceCreate"];
export type FinanceTimesheetCreate = components["schemas"]["TimesheetCreate"];
export type FinanceSubsidyCreate = components["schemas"]["SubsidyCreate"];
export const finance = {
  records: (kind?: string, orderId?: string) =>
    api<FinanceRecord[]>(
      `/api/v1/finance/records?${new URLSearchParams({ ...(kind ? { kind } : {}), ...(orderId ? { order_id: orderId } : {}) })}`,
    ),
  dashboard: () => api<FinanceDashboard>("/api/v1/finance/dashboard"),
  journal: (orderId?: string) =>
    api<FinanceJournal[]>(
      `/api/v1/finance/journal${orderId ? `?order_id=${encodeURIComponent(orderId)}` : ""}`,
    ),
  invoice: (body: FinanceInvoiceCreate) =>
    api<FinanceRecord>("/api/v1/finance/invoices", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  timesheet: (body: FinanceTimesheetCreate) =>
    api<FinanceRecord>("/api/v1/finance/timesheets", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  subsidy: (body: FinanceSubsidyCreate) =>
    api<FinanceRecord>("/api/v1/finance/subsidies", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export function inr(paise: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
  }).format(paise / 100);
}
