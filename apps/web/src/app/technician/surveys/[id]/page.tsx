"use client";
import Link from "next/link";
import {useParams} from "next/navigation";
import {Workspace} from "@/components/workspace";
import {SurveysBoard} from "@/components/surveys-board";
export default function Page(){const params=useParams<{id:string}>();return <Workspace path={`/technician/surveys/${params.id}`}>{()=> <><Link href="/technician/surveys">Back to surveys</Link><SurveysBoard technician surveyId={params.id}/></>}</Workspace>;}
