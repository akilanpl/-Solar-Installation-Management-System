"use client";
import { Workspace } from "@/components/workspace";
import { CustomerBills } from "@/components/warranty";
export default function Page() { return <Workspace path="/customer/bills">{() => <CustomerBills />}</Workspace>; }
