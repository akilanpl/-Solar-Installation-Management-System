export function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `key-${Date.now()}-${Math.floor(Math.random() * 1e9)}`;
}

const STATUS_LABELS: Record<string, string> = {
  open: "Open",
  triaged: "Triaged",
  assigned: "Assigned",
  in_progress: "In progress",
  waiting_customer: "Waiting on you",
  resolved: "Resolved",
  customer_confirmed: "Confirmed by you",
  closed: "Closed",
  cancelled: "Cancelled",
};

export function ticketStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}
