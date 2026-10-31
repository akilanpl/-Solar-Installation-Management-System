"use client";
import { useParams } from "next/navigation";
import { ComplaintDetail } from "@/components/tickets";
import { Workspace } from "@/components/workspace";
export default function Page() {
  const params = useParams<{ id: string }>();
  return <Workspace path={`/customer/complaints/${params.id}`}>{() => <ComplaintDetail ticketId={params.id} />}</Workspace>;
}
