"use client";
import { useParams } from "next/navigation";
import { Workspace } from "@/components/workspace";
import { ReplacementDetail } from "@/components/warranty";
export default function Page() {
  const params = useParams<{ id: string }>();
  return <Workspace path="/warehouse/replacements">{() => <ReplacementDetail replacementId={params.id} warehouse />}</Workspace>;
}
