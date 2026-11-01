"use client";
import Link from "next/link";
import {useParams} from "next/navigation";
import {Workspace} from "@/components/workspace";
import {OrdersBoard} from "@/components/orders-board";
export default function Page(){const params=useParams<{id:string}>();return <Workspace path={`/sales/orders/${params.id}`}>{()=> <><Link href="/sales/orders">Back to orders</Link><OrdersBoard customer={false} orderId={params.id}/></>}</Workspace>;}
