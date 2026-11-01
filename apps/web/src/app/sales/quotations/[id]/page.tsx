"use client";
import Link from "next/link";
import {useParams} from "next/navigation";
import {Workspace} from "@/components/workspace";
import {Quotations} from "@/components/quotations";
export default function Page(){const params=useParams<{id:string}>();return <Workspace path={`/sales/quotations/${params.id}`}>{()=> <><Link href="/sales/quotations">Back to quotations</Link><Quotations customer={false} quotationId={params.id}/></>}</Workspace>;}
