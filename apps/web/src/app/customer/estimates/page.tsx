"use client";
import { Workspace } from "@/components/workspace";
import { CustomerEstimates } from "@/components/warranty";
export default function Page() { return <Workspace path="/customer/estimates">{() => <CustomerEstimates />}</Workspace>; }
