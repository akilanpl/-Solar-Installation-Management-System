"use client";
import {Workspace} from "@/components/workspace";
import {SupportRecords} from "@/components/orders-board";
import {SupportInbox} from "@/components/tickets";
export default function Page(){return <Workspace path="/support">{()=> <><SupportInbox/><SupportRecords/></>}</Workspace>;}
