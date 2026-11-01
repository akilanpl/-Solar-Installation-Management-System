"""Audited internal records, never supplier or provider confirmation."""

import hashlib
import json

from sqlalchemy import func, select

from app.core.errors import AppError
from app.core.security import utcnow
from app.models.operations import GoodsReturn, SupplierOrder
from app.models.phase3 import (
    Delivery,
    DeliveryLine,
    EquipmentSerial,
    ReplenishmentRequest,
    StockLedger,
    StockOperation,
    StockOperationLine,
)
from app.models.workflow import SalesOrder
from app.repositories.queries import add_audit
from app.services.inventory_service import lock_components
from app.services.references import next_reference

WAREHOUSE = {"warehouse_staff", "warehouse_manager", "admin"}
MANAGER = {"warehouse_manager", "admin"}


def permit(user, roles):
    if user.role_code not in roles:
        raise AppError(403, "forbidden", "Your role cannot perform this operation.")


def authorize_return(db, user, payload, key):
    permit(user, WAREHOUSE)
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    order_id = db.scalar(
        select(Delivery.order_id)
        .join(DeliveryLine, DeliveryLine.delivery_id == Delivery.id)
        .where(DeliveryLine.id == payload["delivery_line_id"])
    )
    if order_id is None:
        raise AppError(404, "not_found", "Delivery line not found.")
    db.scalar(select(SalesOrder.id).where(SalesOrder.id == order_id).with_for_update())
    old = db.scalar(
        select(GoodsReturn).where(
            GoodsReturn.created_by_user_id == user.id, GoodsReturn.idempotency_key == key
        )
    )
    if old:
        if old.request_hash != digest:
            raise AppError(409, "idempotency_conflict", "Return key already used.")
        return old
    line = db.get(DeliveryLine, payload["delivery_line_id"])
    delivery = db.get(Delivery, line.delivery_id)
    if delivery.status not in {"delivered", "confirmed"}:
        raise AppError(409, "invalid_transition", "Only delivered goods can be returned.")
    used = int(
        db.scalar(
            select(func.coalesce(func.sum(GoodsReturn.quantity), 0)).where(
                GoodsReturn.delivery_line_id == line.id
            )
        )
        or 0
    )
    if payload["quantity"] > line.quantity - used:
        raise AppError(
            409, "over_return", "Return exceeds delivered units not already authorized for return."
        )
    serial_id = payload.get("serial_id")
    if serial_id is None and db.scalar(
        select(EquipmentSerial.id).where(EquipmentSerial.delivery_line_id == line.id).limit(1)
    ):
        raise AppError(
            422, "return_serial_required", "Identify the actual serialized unit being returned."
        )
    if serial_id:
        serial = db.scalar(
            select(EquipmentSerial).where(EquipmentSerial.id == serial_id).with_for_update()
        )
        if (
            serial is None
            or serial.order_id != delivery.order_id
            or serial.component_code != line.component_code
            or serial.delivery_line_id != line.id
            or serial.status not in {"installed", "delivered"}
            or payload["quantity"] != 1
        ):
            raise AppError(
                409,
                "invalid_serial",
                "Return an assigned serial of this component/order, quantity one.",
            )
        if db.scalar(
            select(GoodsReturn.id).where(
                GoodsReturn.serial_id == serial_id, GoodsReturn.delivery_line_id == line.id
            )
        ):
            raise AppError(
                409, "duplicate_serial_return", "Serial already has a return authorization."
            )
    row = GoodsReturn(
        **payload,
        status="authorized",
        created_by_user_id=user.id,
        idempotency_key=key,
        request_hash=digest,
    )
    db.add(row)
    db.flush()
    add_audit(
        db,
        actor_user_id=user.id,
        action="return.authorized",
        entity_type="goods_return",
        entity_id=row.id,
        metadata={"delivery_line_id": str(line.id), "quantity": row.quantity},
    )
    return row


def inspect_return(db, user, return_id, disposition, note):
    permit(user, MANAGER)
    row = db.scalar(select(GoodsReturn).where(GoodsReturn.id == return_id).with_for_update())
    if row is None:
        raise AppError(404, "not_found", "Return not found.")
    if row.status != "authorized":
        raise AppError(409, "invalid_transition", "Return was already inspected.")
    line = db.get(DeliveryLine, row.delivery_line_id)
    delivery = db.get(Delivery, line.delivery_id)
    lock_components(db, [line.component_code])
    location = "QUARANTINE" if disposition == "damaged" else line.location_code
    operation = StockOperation(
        reference=next_reference(db, "stock_operation", "STK"),
        operation_type="receipt",
        status="done",
        source_order_id=delivery.order_id,
        note=f"Inspected return {row.id}: {disposition}. {note}",
        created_by_user_id=user.id,
        validated_at=utcnow(),
        idempotency_key=f"return-{row.id}",
        request_hash=row.request_hash,
    )
    db.add(operation)
    db.flush()
    stock_line = StockOperationLine(
        operation_id=operation.id,
        component_code=line.component_code,
        quantity=row.quantity,
        from_location=None,
        to_location=location,
        sort_order=0,
    )
    db.add(stock_line)
    db.flush()
    db.add(
        StockLedger(
            operation_id=operation.id,
            component_code=line.component_code,
            location_code=location,
            quantity_delta=row.quantity,
        )
    )
    if row.serial_id:
        from app.models.custody import StockSerialMovement

        unit = db.get(EquipmentSerial, row.serial_id)
        db.add(
            StockSerialMovement(
                operation_id=operation.id,
                line_id=stock_line.id,
                serial_id=unit.id,
                serial_number=unit.serial_number,
                delivery_line_id=line.id,
            )
        )
        from app.services.coverage_service import void_return

        void_return(db, user, row.serial_id, row.id)
        serial = db.scalar(
            select(EquipmentSerial).where(EquipmentSerial.id == row.serial_id).with_for_update()
        )
        serial.location_code = location
        serial.status = "faulty" if disposition == "damaged" else "in_stock"
        if disposition == "restock":
            serial.order_id = None
            serial.delivery_line_id = None
    row.status = "inspected"
    row.disposition = disposition
    row.inspection_note = note
    row.inspected_by_user_id = user.id
    row.inspected_at = utcnow()
    row.operation_id = operation.id
    add_audit(
        db,
        actor_user_id=user.id,
        action="return.inspected",
        entity_type="goods_return",
        entity_id=row.id,
        metadata={
            "disposition": disposition,
            "location": location,
            "operation_id": str(operation.id),
        },
    )
    db.flush()
    return row


def supplier_order(db, user, request_id, name, reference):
    permit(user, MANAGER)
    request = db.scalar(
        select(ReplenishmentRequest).where(ReplenishmentRequest.id == request_id).with_for_update()
    )
    if request is None:
        raise AppError(404, "not_found", "Replenishment request not found.")
    old = db.scalar(
        select(SupplierOrder).where(SupplierOrder.replenishment_request_id == request_id)
    )
    if old:
        if old.supplier_name != name or old.supplier_reference != reference:
            raise AppError(
                409, "duplicate_supplier_order", "Request has a different supplier order record."
            )
        return old
    if request.status != "approved":
        raise AppError(409, "invalid_transition", "Approve replenishment first.")
    row = SupplierOrder(
        replenishment_request_id=request_id,
        supplier_name=name,
        supplier_reference=reference,
        status="ordered",
        created_by_user_id=user.id,
    )
    db.add(row)
    request.status = "ordered"
    db.flush()
    add_audit(
        db,
        actor_user_id=user.id,
        action="supplier_order.recorded",
        entity_type="supplier_order",
        entity_id=row.id,
        metadata={
            "source": "manual record; no supplier API confirmation",
            "replenishment_request_id": str(request_id),
        },
    )
    return row


def link_supplier_receipt(db, user, order_id, operation_id):
    permit(user, WAREHOUSE)
    row = db.scalar(select(SupplierOrder).where(SupplierOrder.id == order_id).with_for_update())
    if row is None:
        raise AppError(404, "not_found", "Supplier order not found.")
    if row.received_operation_id == operation_id:
        return row
    if row.status != "ordered":
        raise AppError(409, "invalid_transition", "Supplier order is closed.")
    operation = db.scalar(
        select(StockOperation).where(StockOperation.id == operation_id).with_for_update()
    )
    request = db.get(ReplenishmentRequest, row.replenishment_request_id)
    if (
        operation is None
        or operation.operation_type != "receipt"
        or operation.status != "done"
        or operation.source_order_id is not None
    ):
        raise AppError(
            409,
            "invalid_receipt",
            "Link a validated supplier goods receipt separate from sales returns.",
        )
    if db.scalar(
        select(GoodsReturn.id).where(GoodsReturn.operation_id == operation_id)
    ) or db.scalar(
        select(SupplierOrder.id).where(SupplierOrder.received_operation_id == operation_id)
    ):
        raise AppError(409, "receipt_reused", "Receipt already belongs to another business event.")
    lines = list(
        db.scalars(
            select(StockOperationLine).where(StockOperationLine.operation_id == operation_id)
        )
    )
    if (
        any(
            line.component_code != request.component_code
            or line.to_location != request.location_code
            for line in lines
        )
        or sum(line.quantity for line in lines) != request.quantity
    ):
        raise AppError(
            409,
            "receipt_mismatch",
            "Receipt must match approved quantities, component and location.",
        )
    row.received_operation_id = operation_id
    row.status = "received"
    request.status = "received"
    add_audit(
        db,
        actor_user_id=user.id,
        action="supplier_order.receipt_linked",
        entity_type="supplier_order",
        entity_id=row.id,
        metadata={"validated_operation_id": str(operation_id)},
    )
    db.flush()
    return row
