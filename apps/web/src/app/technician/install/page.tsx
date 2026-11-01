"use client";
import { Workspace } from "@/components/workspace";
import { Card, PageHeader } from "@/components/ui";
import { InstallReplacementForm } from "@/components/warranty";
export default function Page() {
  return (
    <Workspace path="/technician/install">
      {() => (
        <>
          <PageHeader title="Replacement install" description="Record the exact serial you installed for an issued replacement." />
          <Card><InstallReplacementForm /></Card>
        </>
      )}
    </Workspace>
  );
}
