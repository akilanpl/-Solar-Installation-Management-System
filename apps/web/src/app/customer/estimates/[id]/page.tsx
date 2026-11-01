"use client";
import { useParams } from "next/navigation";
import { Workspace } from "@/components/workspace";
import { EstimateDetail } from "@/components/warranty";
export default function Page() {
  const params = useParams<{ id: string }>();
  return <Workspace path="/customer/estimates">{() => <EstimateDetail estimateId={params.id} />}</Workspace>;
}
