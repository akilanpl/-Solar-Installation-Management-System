"use client";
import { Workspace } from "@/components/workspace";
import { CustomerExtensions } from "@/components/extensions";
export default function Page() {
  return (
    <Workspace path="/customer/warranty-extensions">{() => <CustomerExtensions />}</Workspace>
  );
}
