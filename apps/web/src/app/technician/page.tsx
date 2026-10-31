"use client";

import { PlannedWorkspace } from "@/components/planned";

export default function TechnicianPage() {
  return (
    <PlannedWorkspace
      path="/technician"
      title="Technician"
      description="Jobs, arrival confirmation, and installation evidence are planned. No assignments are loaded because none exist yet."
      sections={[
        { title: "Assigned jobs", body: "When sales schedules a survey or installation, it will appear here from the database." },
        { title: "Arrival and OTP", body: "Customer arrival verification is a planned contract, not a working screen." },
      ]}
    />
  );
}
