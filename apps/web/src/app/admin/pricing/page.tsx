"use client";
import { Workspace } from "@/components/workspace";
import { PricingAdmin } from "@/components/warranty";
export default function Page() { return <Workspace path="/admin/pricing">{() => <PricingAdmin />}</Workspace>; }
