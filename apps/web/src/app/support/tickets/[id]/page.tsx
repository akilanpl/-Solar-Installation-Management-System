"use client";
import { useParams } from "next/navigation";
import { SupportTicketDetail } from "@/components/tickets";
import { Workspace } from "@/components/workspace";
export default function Page() {
  const params = useParams<{ id: string }>();
  return <Workspace path={`/support/tickets/${params.id}`}>{() => <SupportTicketDetail ticketId={params.id} />}</Workspace>;
}
