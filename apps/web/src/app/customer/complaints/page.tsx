"use client";
import { Complaints } from "@/components/tickets";
import { Workspace } from "@/components/workspace";
export default function Page() { return <Workspace path="/customer/complaints">{() => <Complaints />}</Workspace>; }
