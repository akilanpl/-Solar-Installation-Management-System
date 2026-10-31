"use client";

import { PlannedWorkspace } from "@/components/planned";

const COPY: Record<string, { title: string; body: string }> = {
  quotations: {
    title: "Quotations",
    body: "Package quotations and bills of materials are not generated in Phase 1.",
  },
  payments: {
    title: "Payments",
    body: "No payment provider is connected. This page will not show a balance.",
  },
  support: {
    title: "Support",
    body: "Complaint tickets are a later phase. You can still track the enquiry you submitted.",
  },
  surveys: {
    title: "Surveys",
    body: "Site surveys are planned. Phase 1 stores the enquiry, not rooftop measurements.",
  },
  repairs: {
    title: "Repairs",
    body: "Repair jobs are not assigned yet.",
  },
  picking: {
    title: "Picking",
    body: "Warehouse picking starts after an order exists. Orders are not implemented.",
  },
  approvals: {
    title: "Approvals",
    body: "Replenishment approvals are planned for the warehouse manager role.",
  },
  lookup: {
    title: "Customer lookup",
    body: "SysCache lookup is documented as a contract and is not implemented.",
  },
  reports: {
    title: "Reports",
    body: "Revenue, labour, and profitability reports need cost data that Phase 1 does not collect.",
  },
};

export function PlannedRoute({ path, kind }: { path: string; kind: keyof typeof COPY }) {
  const section = COPY[kind];
  return <PlannedWorkspace path={path} title={section.title} description={section.body} sections={[section]} />;
}
