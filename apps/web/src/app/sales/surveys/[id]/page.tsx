"use client";
import Link from "next/link";
import {useParams} from "next/navigation";
import {Workspace} from "@/components/workspace";
import {SurveysBoard} from "@/components/surveys-board";
export default function Page(){const params=useParams<{id:string}>();return <Workspace path={`/sales/surveys/${params.id}`}>{()=> <><Link href="/sales/surveys">Back to surveys</Link><SurveysBoard surveyId={params.id}/></>}</Workspace>;}
