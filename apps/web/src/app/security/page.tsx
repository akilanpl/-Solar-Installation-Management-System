"use client";
import { Workspace } from "@/components/workspace";
import { SecuritySettings } from "@/components/security";
export default function Page() {
  return (
    <Workspace path="/security">{(user) => <SecuritySettings user={user} />}</Workspace>
  );
}
