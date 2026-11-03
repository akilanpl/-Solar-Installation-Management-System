export function rupeesToPaise(input: string): number | null {
  if (!/^[0-9]+$/.test(input)) return null;
  const rupees = Number(input);
  if (!Number.isSafeInteger(rupees) || rupees > 1_000_000) return null;
  return rupees * 100;
}

export function formatInrFromPaise(minor: number): string {
  const sign = minor < 0 ? "-" : "";
  const absolute = Math.abs(minor);
  const rupees = Math.trunc(absolute / 100);
  const paise = absolute % 100;
  const grouped = new Intl.NumberFormat("en-IN").format(rupees);
  return `${sign}₹${grouped}.${String(paise).padStart(2, "0")}`;
}

export function formatCapacity(watts: number): string {
  return `${watts / 1000} kW`;
}

export function formatWhen(iso: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata",
  }).format(new Date(iso));
}

export const STATUS_LABEL: Record<string, string> = {
  submitted: "Submitted",
  under_review: "Under review",
  qualified: "Qualified",
  not_qualified: "Not qualified",
  draft: "Draft",
  assigned: "Assigned",
  in_progress: "In progress",
  approved: "Approved",
  rejected: "Rejected",
  issued: "Issued",
  superseded: "Superseded",
  withdrawn: "Withdrawn",
  accepted: "Accepted",
  pending: "Pending",
  processing: "Processing",
  verified: "Verified",
  failed: "Failed",
  unresolved: "Unresolved",
  confirmed: "Confirmed",
  pending_preparation: "Pending preparation",
  unscheduled: "Unscheduled",
  suitable: "Suitable",
  unsuitable: "Unsuitable",
  unknown: "Unknown",
};

export function statusLabel(status: string): string {
  return STATUS_LABEL[status] ?? status.replaceAll("_", " ");
}

export const GRID_LABEL: Record<string, string> = {
  on_grid: "On-grid",
  off_grid: "Off-grid",
};
