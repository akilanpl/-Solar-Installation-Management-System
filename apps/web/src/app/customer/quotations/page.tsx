"use client";
import { Workspace } from "@/components/workspace";
import { Quotations } from "@/components/quotations";
export default function Page() { return <Workspace path="/customer/quotations">{() => <Quotations customer={true} />}</Workspace>; }
