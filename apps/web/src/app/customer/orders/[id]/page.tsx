"use client";

import { useParams } from "next/navigation";

import { OrderView } from "@/app/sales/orders/[id]/page";
import { Workspace } from "@/components/workspace";

export default function CustomerOrderPage() {
  const params = useParams<{ id: string }>();
  return (
    <Workspace path={`/customer/orders/${params.id}`}>
      {() => <OrderView id={params.id} ordersHref="/customer/orders" showScheduling={false} />}
    </Workspace>
  );
}
