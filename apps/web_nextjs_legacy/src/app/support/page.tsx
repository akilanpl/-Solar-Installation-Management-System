"use client";

import { PlannedWorkspace } from "@/components/planned";

export default function SupportPage() {
  return (
    <PlannedWorkspace
      path="/support"
      title="Support"
      description="Complaint intake and SysCache are planned. There is no ticket list because no tickets have been stored."
      sections={[
        { title: "Complaints", body: "A future summary suggestion must be confirmed by the customer or support agent before it is treated as the issue." },
        { title: "SysCache", body: "Support context will be read from PostgreSQL first. Phase 1 does not cache it and does not claim a speedup." },
      ]}
    />
  );
}
