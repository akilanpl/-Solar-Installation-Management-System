"use client";
import { CustomerGeneration } from "@/components/generation";
import { Workspace } from "@/components/workspace";
export default function Page() { return <Workspace path="/customer/generation">{() => <CustomerGeneration />}</Workspace>; }
