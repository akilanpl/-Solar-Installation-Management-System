"use client";
import { Workspace } from "@/components/workspace";
import { Quotations } from "@/components/quotations";
export default function Page() { return <Workspace path="/sales/quotations">{() => <Quotations customer={false} />}</Workspace>; }
