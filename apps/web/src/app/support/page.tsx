"use client";
import { SupportInbox } from "@/components/tickets";
import { Workspace } from "@/components/workspace";
export default function SupportPage() { return <Workspace path="/support">{() => <SupportInbox />}</Workspace>; }
