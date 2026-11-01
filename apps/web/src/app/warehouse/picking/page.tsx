"use client";
import {Workspace} from "@/components/workspace";
import {WarehouseBoard} from "@/components/warehouse-board";
export default function Page(){return <Workspace path="/warehouse/picking">{user=><WarehouseBoard user={user}/>}</Workspace>;}
