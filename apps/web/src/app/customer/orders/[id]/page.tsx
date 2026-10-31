"use client";
import Link from "next/link";
import {useParams} from "next/navigation";
import {Workspace} from "@/components/workspace";
import {OrdersBoard} from "@/components/orders-board";
export default function Page(){const params=useParams<{id:string}>();return <Workspace path={`/customer/orders/${params.id}`}>{()=> <><Link href="/customer/orders">Back to orders</Link><OrdersBoard orderId={params.id}/></>}</Workspace>;}
