"use client";

import { OrderQueue } from "@/app/sales/orders/page";
import { Workspace } from "@/components/workspace";

export default function CustomerOrdersPage() {
  return (
    <Workspace path="/customer/orders">
      {() => <OrderQueue base="/customer/orders" />}
    </Workspace>
  );
}
