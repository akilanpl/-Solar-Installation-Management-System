"use client";
import { useParams } from "next/navigation";
import { Workspace } from "@/components/workspace";
import { SupportEstimateDetail } from "@/components/warranty";
export default function Page() {
  const params = useParams<{ id: string }>();
  return <Workspace path="/support/estimates">{() => <SupportEstimateDetail estimateId={params.id} />}</Workspace>;
}
