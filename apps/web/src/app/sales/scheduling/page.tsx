"use client";
import {Workspace} from "@/components/workspace";
import {SchedulingBoard} from "@/components/scheduling-board";
export default function Page(){return <Workspace path="/sales/scheduling">{()=> <SchedulingBoard/>}</Workspace>;}
