"use client";
import { Workspace } from "@/components/workspace";
import { SurveysBoard } from "@/components/surveys-board";
export default function Page(){return <Workspace path="/technician/surveys">{()=> <SurveysBoard technician={true}/>}</Workspace>;}
