"use client";
import { Workspace } from "@/components/workspace";
import { SupportEstimates } from "@/components/warranty";
export default function Page() { return <Workspace path="/support/estimates">{() => <SupportEstimates />}</Workspace>; }
