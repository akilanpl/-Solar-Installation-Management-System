"use client";
import { Workspace } from "@/components/workspace";
import { Equipment } from "@/components/warranty";
export default function Page() { return <Workspace path="/customer/equipment">{() => <Equipment />}</Workspace>; }
