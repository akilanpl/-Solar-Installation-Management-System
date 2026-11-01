import type { components } from "@/generated/schema";
export type CustomerJob = components["schemas"]["JobResponse"];
export type CustomerReceipt = components["schemas"]["ReceiptResponse"];
export function nextCustomerVisit(jobs: CustomerJob[]): CustomerJob | undefined {
  return jobs.filter(j => j.slot_starts_at && !["completed", "cancelled"].includes(j.status))
    .sort((a,b) => Date.parse(a.slot_starts_at!) - Date.parse(b.slot_starts_at!))[0];
}
export function visibleCustomerCode(job: CustomerJob | undefined): string | null {
  return job && !job.otp_verified && !["completed", "cancelled"].includes(job.status) && /^\d{6}$/.test(job.customer_code ?? "") ? job.customer_code! : null;
}
export function receiptCards(receipts: CustomerReceipt[]) {
  return [...receipts].sort((a,b) => Date.parse(b.recorded_at)-Date.parse(a.recorded_at)).slice(0,3);
}
