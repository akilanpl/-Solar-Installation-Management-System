"use client";

import { AssignedSurveys } from "@/app/technician/page";
import { Workspace } from "@/components/workspace";

export default function TechnicianSurveysPage() {
  return (
    <Workspace path="/technician/surveys">
      {() => <AssignedSurveys />}
    </Workspace>
  );
}
