"use client";
import {Workspace} from "@/components/workspace";
import {SupportRecords} from "@/components/orders-board";
export default function Page(){return <Workspace path="/support">{()=> <SupportRecords/>}</Workspace>;}
