"use client";
import { useParams } from "next/navigation";
import { Workspace } from "@/components/workspace";
import { BillDetail } from "@/components/warranty";
export default function Page() {
  const params = useParams<{ id: string }>();
  return <Workspace path="/customer/bills">{() => <BillDetail invoiceId={params.id} />}</Workspace>;
}
