"use client";
import { Workspace } from "@/components/workspace";
import { SurveysBoard } from "@/components/surveys-board";
export default function Page(){return <Workspace path="/sales/surveys">{()=> <SurveysBoard technician={false}/>}</Workspace>;}
