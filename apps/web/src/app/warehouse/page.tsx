"use client";

import { PlannedWorkspace } from "@/components/planned";

export default function WarehousePage() {
  return (
    <PlannedWorkspace
      path="/warehouse"
      title="Warehouse"
      description="Stock quantities are not implemented. This page does not invent on-hand numbers. Warehouse staff and managers have different future permissions."
      sections={[
        { title: "Locations and stock", body: "Receipts, transfers, and adjustments will follow the StockSense ledger rule: stock changes only when an operation is validated, in one database transaction." },
        { title: "Replenishment", body: "Reorder suggestions need a warehouse manager approval. That workflow is planned." },
      ]}
    />
  );
}
