"use client";
import { Workspace } from "@/components/workspace";
import { ReplacementList } from "@/components/warranty";
export default function Page() { return <Workspace path="/warehouse/replacements">{() => <ReplacementList base="/warehouse/replacements" />}</Workspace>; }
