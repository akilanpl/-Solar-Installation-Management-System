"use client";
import {Workspace} from "@/components/workspace";
import {OrdersBoard} from "@/components/orders-board";
export default function Page(){return <Workspace path="/customer/orders">{()=> <OrdersBoard/>}</Workspace>;}
