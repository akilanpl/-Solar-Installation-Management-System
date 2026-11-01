"use client";
import { Workspace } from "@/components/workspace";
import { SupportExtensions } from "@/components/extensions";
export default function Page() {
  return (
    <Workspace path="/support/extensions">{(user) => <SupportExtensions user={user} />}</Workspace>
  );
}
