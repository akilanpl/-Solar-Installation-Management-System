"use client";
import { OperationsDashboard } from "@/components/recovery/operations";
import { Workspace } from "@/components/workspace";
import { Jobs } from "@/components/jobs";
export default function Page() { return <Workspace path="/technician">{() => <><OperationsDashboard role="technician"/><div id="assigned-installation-jobs"><Jobs customer={false}/></div></>}</Workspace>; }
