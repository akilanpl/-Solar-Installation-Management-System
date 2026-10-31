"use client";
import Link from "next/link";
import {useParams} from "next/navigation";
import {Workspace} from "@/components/workspace";
import {Quotations} from "@/components/quotations";
export default function Page(){const params=useParams<{id:string}>();return <Workspace path={`/customer/quotations/${params.id}`}>{()=> <><Link href="/customer/quotations">Back to quotations</Link><Quotations customer quotationId={params.id}/></>}</Workspace>;}
