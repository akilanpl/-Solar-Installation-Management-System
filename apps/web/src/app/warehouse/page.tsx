"use client";
import {OperationsDashboard} from "@/components/recovery/operations";
import {Workspace} from "@/components/workspace";
import {WarehouseBoard} from "@/components/warehouse-board";
export default function Page(){return <Workspace path="/warehouse">{user=><><OperationsDashboard role={user.role === "warehouse_manager" ? "warehouse_manager" : "warehouse_staff"}/><WarehouseBoard user={user}/></>}</Workspace>;}
