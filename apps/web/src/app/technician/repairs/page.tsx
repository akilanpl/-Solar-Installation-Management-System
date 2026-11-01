"use client";
import { Repairs } from "@/components/tickets";
import { Workspace } from "@/components/workspace";
export default function Page() { return <Workspace path="/technician/repairs">{() => <Repairs />}</Workspace>; }
