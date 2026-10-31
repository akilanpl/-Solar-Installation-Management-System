"use client";
import { Workspace } from "@/components/workspace";
import { OfflineWorkbench } from "@/components/offline";
export default function Page() {
  return (
    <Workspace path="/technician/offline">{(user) => <OfflineWorkbench user={user} />}</Workspace>
  );
}
