"use client";
import { Workspace } from "@/components/workspace";
import { Jobs } from "@/components/jobs";
export default function Page() { return <Workspace path="/customer/installations">{() => <Jobs customer={true} />}</Workspace>; }
