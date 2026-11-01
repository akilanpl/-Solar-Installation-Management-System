"use client";
import { useParams } from "next/navigation";
import { RepairDetail } from "@/components/tickets";
import { Workspace } from "@/components/workspace";
export default function Page() {
  const params = useParams<{ id: string }>();
  return <Workspace path={`/technician/repairs/${params.id}`}>{() => <RepairDetail jobId={params.id} />}</Workspace>;
}
