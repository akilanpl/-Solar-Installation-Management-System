"use client";
import { Workspace } from "@/components/workspace";
import { SupportIntelligence } from "@/components/intelligence";
import { SupportRecords } from "@/components/orders-board";
export default function Page() {
  return <Workspace path="/support/lookup">{() => <><SupportIntelligence /><SupportRecords /></>}</Workspace>;
}
