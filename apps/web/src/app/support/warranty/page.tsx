"use client";
import { Workspace } from "@/components/workspace";
import { WarrantyWorkspace } from "@/components/warranty";
export default function Page() { return <Workspace path="/support/warranty">{() => <WarrantyWorkspace />}</Workspace>; }
