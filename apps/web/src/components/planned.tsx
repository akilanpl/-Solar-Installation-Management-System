"use client";

import { Workspace } from "@/components/workspace";
import { EmptyState, PageHeader } from "@/components/ui";

export function PlannedWorkspace({
  path,
  title,
  description,
  sections,
}: {
  path: string;
  title: string;
  description: string;
  sections: { title: string; body: string }[];
}) {
  return (
    <Workspace path={path}>
      {(user) => (
        <>
          <PageHeader title={title} description={`${description} Signed in as ${user.full_name}.`} />
          <div className="grid gap-4">
            {sections.map((section) => (
              <EmptyState key={section.title} title={section.title} body={section.body} />
            ))}
          </div>
        </>
      )}
    </Workspace>
  );
}
