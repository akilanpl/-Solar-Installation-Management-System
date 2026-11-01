"""Transactional per-location picking with exact recorded serial custody.

Partial deliveries consume actual location allocations. Confirmed custody is
separate from installation; only a prepared pick can be automatically cancelled.
"""

import hashlib
import json
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.security import utcnow
from app.models.identity import User
from app.models.phase3 import (
    Delivery,
    DeliveryLine,
    EquipmentSerial,
    StockLedger,
    StockOperation,
    StockOperationLine,
    StockReservation,
    Warranty,
)
from app.models.workflow import SalesOrder
from app.repositories.queries import add_audit
from app.services.references import next_reference

WAREHOUSE = {"warehouse_staff", "warehouse_manager", "admin"}
CONFIRM_ROLES = {"warehouse_staff", "warehouse_manager", "admin", "technician"}
READ_ROLES = WAREHOUSE | {"sales", "admin", "technician", "support"}
WARRANTY_YEARS = 5


def _hash(order_id: uuid.UUID) -> str:
    raw = json.dumps({"order_id": str(order_id)}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _main_on_hand(db: Session, component_code: str) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(StockLedger.quantity_delta), 0)).where(
            StockLedger.component_code == component_code,
            StockLedger.location_code == "MAIN",
        )
    )
    return int(total or 0)


def _deduct_pick(
    db: Session, user: User, order: SalesOrder, delivery: Delivery, picks: list[dict]
) -> StockOperation:
    operation = StockOperation(
        reference=next_reference(db, "stock_operation", "STK"),
        operation_type="delivery",
        status="done",
        source_order_id=order.id,
        note=f"Pick for delivery {delivery.reference}.",
        created_by_user_id=user.id,
        validated_at=utcnow(),
        idempotency_key=f"pick-{delivery.id}",
        request_hash=delivery.request_hash,
    )
    db.add(operation)
    db.flush()
    for position, line in enumerate(picks):
        db.add(
            StockOperationLine(
                operation_id=operation.id,
                component_code=line["component_code"],
                quantity=Decimal(line["quantity"]),
                from_location=line["location_code"],
                to_location=None,
                sort_order=position,
            )
        )
        db.add(
            StockLedger(
                operation_id=operation.id,
                component_code=line["component_code"],
                location_code=line["location_code"],
                quantity_delta=Decimal(-line["quantity"]),
            )
        )
    add_audit(
        db,
        actor_user_id=user.id,
        action="stock_operation.validated",
        entity_type="stock_operation",
        entity_id=operation.id,
        metadata={"delivery_id": str(delivery.id)},
    )
    db.flush()
    return operation


def _restock_cancelled_pick(db: Session, user: User, delivery: Delivery) -> None:
    """Return a cancelled pick to its actual source location through a done receipt operation."""
    operation = StockOperation(
        reference=next_reference(db, "stock_operation", "STK"),
        operation_type="receipt",
        status="done",
        source_order_id=delivery.order_id,
        note=f"Restock for cancelled delivery {delivery.reference}.",
        created_by_user_id=user.id,
        validated_at=utcnow(),
        idempotency_key=f"restock-{delivery.id}",
        request_hash=_hash(delivery.order_id),
    )
    db.add(operation)
    db.flush()
    from app.models.operations import StockAllocation
    from app.services.inventory_service import lock_components

    lock_components(db, [line.component_code for line in delivery.lines])
    for position, line in enumerate(delivery.lines):
        allocation = db.scalar(
            select(StockAllocation)
            .join(StockReservation, StockAllocation.reservation_id == StockReservation.id)
            .where(
                StockReservation.order_id == delivery.order_id,
                StockReservation.component_code == line.component_code,
                StockAllocation.location_code == line.location_code,
            )
            .with_for_update(of=StockAllocation)
        )
        if allocation is not None:
            allocation.picked_quantity -= line.quantity
        stock_line = StockOperationLine(
            operation_id=operation.id,
            component_code=line.component_code,
            quantity=Decimal(line.quantity),
            from_location=None,
            to_location=line.location_code,
            sort_order=position,
        )
        db.add(stock_line)
        db.flush()
        from app.models.custody import StockSerialMovement

        for unit in db.scalars(
            select(EquipmentSerial).where(EquipmentSerial.delivery_line_id == line.id)
        ):
            db.add(
                StockSerialMovement(
                    operation_id=operation.id,
                    line_id=stock_line.id,
                    serial_id=unit.id,
                    serial_number=unit.serial_number,
                    delivery_line_id=line.id,
                )
            )
        db.add(
            StockLedger(
                operation_id=operation.id,
                component_code=line.component_code,
                location_code=line.location_code,
                quantity_delta=Decimal(line.quantity),
            )
        )
    add_audit(
        db,
        actor_user_id=user.id,
        action="stock_operation.validated",
        entity_type="stock_operation",
        entity_id=operation.id,
        metadata={"restock_for_delivery": str(delivery.id)},
    )
    db.flush()


def create_delivery(
    db: Session,
    user: User,
    order_id: uuid.UUID,
    idempotency_key: str,
    lines: list[dict] | None = None,
) -> tuple[Delivery, bool]:
    from collections import defaultdict

    from app.models.operations import StockAllocation
    from app.models.phase3 import WarehouseLocation
    from app.services.inventory_service import lock_components, on_hand
    from app.services.location_allocation import outstanding

    if user.role_code not in WAREHOUSE:
        raise AppError(403, "forbidden", "Only warehouse staff can prepare a delivery.")
    # Serialize every pick/cancel for an order, then stock writers by component.
    order = db.scalar(
        select(SalesOrder)
        .where(SalesOrder.id == order_id)
        .options(selectinload(SalesOrder.lines))
        .with_for_update()
    )
    if order is None:
        raise AppError(404, "not_found", "Order not found.")
    digest = hashlib.sha256(
        json.dumps(
            {"order_id": str(order_id), "lines": lines}, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    keyed = db.scalar(
        select(Delivery).where(
            Delivery.created_by_user_id == user.id, Delivery.idempotency_key == idempotency_key
        )
    )
    if keyed is not None:
        if keyed.request_hash != digest:
            raise AppError(
                409, "idempotency_conflict", "This key was used for a different delivery."
            )
        return _load(db, keyed.id), True
    demand = defaultdict(int)
    for line in order.lines:
        if line.line_kind == "material" and line.component_code:
            demand[line.component_code] += line.quantity
    reservations = {
        r.component_code: r
        for r in db.scalars(
            select(StockReservation).where(StockReservation.order_id == order.id).with_for_update()
        )
    }
    if not reservations:
        raise AppError(409, "reservations_missing", "This order has no reservations to pick.")
    lock_components(db, list(demand))
    used = dict(
        db.execute(
            select(DeliveryLine.component_code, func.sum(DeliveryLine.quantity))
            .join(Delivery, DeliveryLine.delivery_id == Delivery.id)
            .where(Delivery.order_id == order.id, Delivery.status != "cancelled")
            .group_by(DeliveryLine.component_code)
        ).all()
    )
    remaining = {c: q - int(used.get(c, 0)) for c, q in demand.items()}
    wanted = defaultdict(int)
    if lines is None:
        for code, quantity in remaining.items():
            own_allocations = list(
                db.scalars(
                    select(StockAllocation).where(
                        StockAllocation.reservation_id == reservations[code].id
                    )
                )
            )
            allowed = {
                row.location_code: row.quantity - row.picked_quantity for row in own_allocations
            }
            # Use this order's reserved locations first, then genuinely
            # unallocated stock. Allocation never invents on-hand goods.
            unallocated = reservations[code].quantity - sum(row.quantity for row in own_allocations)
            locations = list(
                db.scalars(
                    select(WarehouseLocation.code).where(WarehouseLocation.code != "QUARANTINE")
                )
            )
            locations.sort(key=lambda loc: (allowed.get(loc, 0) <= 0, loc))
            for loc in locations:
                qty = min(
                    quantity,
                    max(
                        0,
                        int(
                            on_hand(db, code, loc)
                            - outstanding(db, code, loc, exclude_order=order.id)
                        ),
                    ),
                    allowed.get(loc, 0) + unallocated,
                )
                if qty:
                    wanted[(code, loc)] += qty
                    unallocated -= max(0, qty - allowed.get(loc, 0))
                    quantity -= qty
                if not quantity:
                    break
            if quantity:
                raise AppError(
                    409, "insufficient_stock", f"Insufficient available stock for {code}."
                )
    else:
        for line in lines:
            wanted[(line["component_code"], line["location_code"])] += line["quantity"]
    totals = defaultdict(int)
    for (code, loc), qty in wanted.items():
        if (
            code not in demand
            or qty <= 0
            or loc == "QUARANTINE"
            or db.get(WarehouseLocation, loc) is None
        ):
            raise AppError(
                422,
                "invalid_pick",
                "Choose an ordered component, usable location and positive quantity.",
            )
        totals[code] += qty
        if totals[code] > remaining[code]:
            raise AppError(409, "over_pick", "Pick exceeds remaining order quantity.")
        if on_hand(db, code, loc) - outstanding(db, code, loc, exclude_order=order.id) < qty:
            raise AppError(
                409,
                "insufficient_stock",
                f"Stock at {loc} is insufficient or allocated to another order.",
            )
    if not wanted:
        raise AppError(
            409, "duplicate_delivery", "No remaining order material is available to pick."
        )
    from app.services.serial_custody import require_registered_balance, tracked

    # Allocate recorded received identities under the same component lock.
    # This chooses known stock; it never invents serial numbers or a receipt.
    for (code, loc), qty in sorted(wanted.items()):
        require_registered_balance(db, code, loc)
        own = list(
            db.scalars(
                select(EquipmentSerial).where(
                    EquipmentSerial.order_id == order.id,
                    EquipmentSerial.component_code == code,
                    EquipmentSerial.location_code == loc,
                    EquipmentSerial.status == "reserved",
                    EquipmentSerial.delivery_line_id.is_(None),
                )
            )
        )
        known = int(
            db.scalar(
                select(func.count())
                .select_from(EquipmentSerial)
                .where(
                    EquipmentSerial.component_code == code,
                    EquipmentSerial.location_code == loc,
                    EquipmentSerial.status.in_(("in_stock", "reserved")),
                )
            )
            or 0
        )
        anonymous = max(0, int(on_hand(db, code, loc)) - known)
        needed = max(0, qty - len(own) - (0 if tracked(db, code) else anonymous))
        candidates = (
            list(
                db.scalars(
                    select(EquipmentSerial)
                    .where(
                        EquipmentSerial.component_code == code,
                        EquipmentSerial.location_code == loc,
                        EquipmentSerial.status == "in_stock",
                        EquipmentSerial.order_id.is_(None),
                    )
                    .order_by(EquipmentSerial.created_at, EquipmentSerial.serial_number)
                    .limit(needed)
                    .with_for_update()
                )
            )
            if needed
            else []
        )
        if len(candidates) < needed:
            raise AppError(
                409,
                "serials_required",
                "Record received serials for every hardware unit before picking.",
            )
        for unit in candidates:
            assign_serial(db, user, unit.id, order.id)
    # Existing physical allocations constrain a pick to its reserved locations.
    for code in totals:
        r = reservations[code]
        allocated = list(
            db.scalars(
                select(StockAllocation)
                .where(StockAllocation.reservation_id == r.id)
                .with_for_update()
            )
        )
        unallocated = r.quantity - sum(row.quantity for row in allocated)
        for (c, loc), qty in wanted.items():
            if c != code:
                continue
            row = next((a for a in allocated if a.location_code == loc), None)
            available = row.quantity - row.picked_quantity if row else 0
            needed = max(0, qty - available)
            if needed > unallocated:
                raise AppError(
                    409,
                    "allocation_mismatch",
                    "Other units are reserved at another location; release/reallocate them before picking here.",
                )
            if row is None:
                row = StockAllocation(
                    reservation_id=r.id, location_code=loc, quantity=qty, picked_quantity=0
                )
                db.add(row)
            else:
                row.quantity += needed
            row.picked_quantity += qty
            unallocated -= needed
    delivery = Delivery(
        reference=next_reference(db, "delivery", "DLV"),
        order_id=order.id,
        status="prepared",
        created_by_user_id=user.id,
        idempotency_key=idempotency_key,
        request_hash=digest,
    )
    db.add(delivery)
    db.flush()
    picks = [
        {"component_code": c, "location_code": location, "quantity": q}
        for (c, location), q in sorted(wanted.items())
    ]
    pick_operation = _deduct_pick(db, user, order, delivery, picks)
    for i, item in enumerate(picks):
        line = DeliveryLine(delivery_id=delivery.id, sort_order=i, **item)
        db.add(line)
        db.flush()
        serials = list(
            db.scalars(
                select(EquipmentSerial)
                .where(
                    EquipmentSerial.order_id == order.id,
                    EquipmentSerial.component_code == line.component_code,
                    EquipmentSerial.location_code == line.location_code,
                    EquipmentSerial.status == "reserved",
                    EquipmentSerial.delivery_line_id.is_(None),
                )
                .order_by(EquipmentSerial.serial_number)
                .limit(line.quantity)
                .with_for_update()
            )
        )
        from app.models.custody import StockSerialMovement

        stock_line = db.scalar(
            select(StockOperationLine).where(
                StockOperationLine.operation_id == pick_operation.id,
                StockOperationLine.sort_order == i,
            )
        )
        for serial in serials:
            db.add(
                StockSerialMovement(
                    operation_id=pick_operation.id,
                    line_id=stock_line.id,
                    delivery_line_id=line.id,
                    serial_id=serial.id,
                    serial_number=serial.serial_number,
                )
            )
            serial.delivery_line_id = line.id
            serial.status = "in_transit"
    add_audit(
        db,
        actor_user_id=user.id,
        action="delivery.prepared",
        entity_type="delivery",
        entity_id=delivery.id,
        metadata={
            "order_id": str(order.id),
            "partial": any(totals[c] < remaining[c] for c in remaining),
        },
    )
    db.flush()
    return _load(db, delivery.id), False


def _load(db: Session, delivery_id: uuid.UUID) -> Delivery:
    loaded = db.scalar(
        select(Delivery)
        .where(Delivery.id == delivery_id)
        .options(selectinload(Delivery.lines).selectinload(DeliveryLine.serials))
    )
    if loaded is None:
        raise AppError(500, "delivery_missing", "The delivery could not be reloaded.")
    return loaded


def transition(db: Session, user: User, delivery_id: uuid.UUID, to_status: str) -> Delivery:
    allowed = {
        "prepared": {"in_transit", "cancelled"},
        "in_transit": {"delivered"},
        "delivered": {"confirmed"},
    }
    order_id = db.scalar(select(Delivery.order_id).where(Delivery.id == delivery_id))
    if order_id is not None:
        db.scalar(select(SalesOrder.id).where(SalesOrder.id == order_id).with_for_update())
    delivery = db.scalar(
        select(Delivery)
        .where(Delivery.id == delivery_id)
        .options(selectinload(Delivery.lines).selectinload(DeliveryLine.serials))
        .with_for_update()
    )
    if delivery is None:
        raise AppError(404, "not_found", "Delivery not found.")
    if to_status == "confirmed" and user.role_code not in CONFIRM_ROLES:
        raise AppError(403, "forbidden", "You cannot confirm this delivery.")
    if to_status != "confirmed" and user.role_code not in WAREHOUSE:
        raise AppError(403, "forbidden", "Only warehouse staff can move a delivery.")
    if delivery.status not in allowed or to_status not in allowed[delivery.status]:
        raise AppError(
            409,
            "invalid_transition",
            f"Cannot move delivery from {delivery.status} to {to_status}.",
        )
    delivery.status = to_status
    if to_status == "cancelled":
        _restock_cancelled_pick(db, user, delivery)
        for serial in db.scalars(
            select(EquipmentSerial)
            .join(DeliveryLine, EquipmentSerial.delivery_line_id == DeliveryLine.id)
            .where(DeliveryLine.delivery_id == delivery.id)
            .with_for_update(of=EquipmentSerial)
        ):
            serial.delivery_line_id = None
            serial.status = "reserved"
    if to_status == "confirmed":
        delivery.confirmed_at = utcnow()
        from app.services.inventory_service import consume_reservations as _consume

        db.flush()
        for serial in db.scalars(
            select(EquipmentSerial)
            .join(DeliveryLine, EquipmentSerial.delivery_line_id == DeliveryLine.id)
            .where(DeliveryLine.delivery_id == delivery.id, EquipmentSerial.status == "in_transit")
            .with_for_update(of=EquipmentSerial)
        ):
            serial.status = "delivered"
        db.flush()
        from app.services.coverage_service import activate

        activate(db, user, delivery.order_id, "delivery", delivery.confirmed_at)
        confirmed = dict(
            db.execute(
                select(DeliveryLine.component_code, func.sum(DeliveryLine.quantity))
                .join(Delivery, DeliveryLine.delivery_id == Delivery.id)
                .where(Delivery.order_id == delivery.order_id, Delivery.status == "confirmed")
                .group_by(DeliveryLine.component_code)
            ).all()
        )
        reservations = list(
            db.scalars(
                select(StockReservation).where(StockReservation.order_id == delivery.order_id)
            )
        )
        if all(int(confirmed.get(r.component_code, 0)) >= r.quantity for r in reservations):
            _consume(db, delivery.order_id)
            _activate_warranty(db, user, delivery.order_id)
    add_audit(
        db,
        actor_user_id=user.id,
        action=f"delivery.{to_status}",
        entity_type="delivery",
        entity_id=delivery.id,
        metadata={"order_id": str(delivery.order_id)},
    )
    db.flush()
    return _load(db, delivery.id)


def assign_serial(
    db: Session, user: User, serial_id: uuid.UUID, order_id: uuid.UUID
) -> EquipmentSerial:
    if user.role_code not in WAREHOUSE:
        raise AppError(403, "forbidden", "Only warehouse staff can assign serials.")
    db.scalar(select(SalesOrder.id).where(SalesOrder.id == order_id).with_for_update())
    peek = db.get(EquipmentSerial, serial_id)
    if peek is None:
        raise AppError(404, "not_found", "Serial not found.")
    from app.services.inventory_service import lock_components

    lock_components(db, [peek.component_code])
    serial = db.scalar(
        select(EquipmentSerial)
        .where(EquipmentSerial.id == serial_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if serial is None:
        raise AppError(404, "not_found", "Serial not found.")
    if serial.status != "in_stock":
        raise AppError(409, "invalid_transition", "Only an in-stock serial can be assigned.")
    receipt = db.get(StockOperation, serial.operation_id) if serial.operation_id else None
    if (
        receipt is None
        or receipt.operation_type != "receipt"
        or receipt.status != "done"
        or serial.location_code == "QUARANTINE"
    ):
        raise AppError(
            409,
            "receipt_required",
            "A usable validated receipt is required before serial assignment.",
        )
    order = db.get(SalesOrder, order_id)
    if order is None:
        raise AppError(404, "not_found", "Order not found.")
    if not any(
        line.line_kind == "material" and line.component_code == serial.component_code
        for line in order.lines
    ):
        raise AppError(
            409, "serial_component_mismatch", "This serial's component is not on the order."
        )
    required = sum(
        line.quantity
        for line in order.lines
        if line.line_kind == "material" and line.component_code == serial.component_code
    )
    assigned = int(
        db.scalar(
            select(func.count())
            .select_from(EquipmentSerial)
            .where(
                EquipmentSerial.order_id == order.id,
                EquipmentSerial.component_code == serial.component_code,
                EquipmentSerial.status.in_(("reserved", "in_transit", "delivered", "installed")),
            )
        )
        or 0
    )
    if assigned >= required:
        raise AppError(409, "serial_over_assignment", "All ordered units already have serials.")
    from app.models.operations import StockAllocation
    from app.services.location_allocation import allocate

    reservation = db.scalar(
        select(StockReservation)
        .where(
            StockReservation.order_id == order.id,
            StockReservation.component_code == serial.component_code,
        )
        .with_for_update()
    )
    if reservation is None:
        raise AppError(409, "reservations_missing", "Order material demand is not reserved.")
    allocation = db.scalar(
        select(StockAllocation).where(
            StockAllocation.reservation_id == reservation.id,
            StockAllocation.location_code == serial.location_code,
        )
    )
    units = (
        int(
            db.scalar(
                select(func.count())
                .select_from(EquipmentSerial)
                .where(
                    EquipmentSerial.order_id == order.id,
                    EquipmentSerial.component_code == serial.component_code,
                    EquipmentSerial.location_code == serial.location_code,
                    EquipmentSerial.status == "reserved",
                )
            )
            or 0
        )
        + 1
    )
    desired = max(
        allocation.quantity if allocation else 0,
        (allocation.picked_quantity if allocation else 0) + units,
    )
    allocate(
        db,
        user,
        order.id,
        [
            {
                "component_code": serial.component_code,
                "location_code": serial.location_code,
                "quantity": desired,
            }
        ],
    )
    serial.order_id = order.id
    serial.status = "reserved"
    add_audit(
        db,
        actor_user_id=user.id,
        action="serial.assigned",
        entity_type="equipment_serial",
        entity_id=serial.id,
        metadata={"order_id": str(order.id)},
    )
    db.flush()
    return serial


def _activate_warranty(db: Session, user: User, order_id: uuid.UUID) -> Warranty:
    existing = db.scalar(select(Warranty).where(Warranty.order_id == order_id))
    if existing is not None:
        return existing
    order = db.get(SalesOrder, order_id)
    if order is None:
        raise AppError(404, "not_found", "Order not found.")
    starts_at = utcnow()
    warranty = Warranty(
        order_id=order.id,
        customer_user_id=order.customer_user_id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(days=365 * WARRANTY_YEARS),
        status="active",
        coverage_note="Legacy five-year order-level estimate. Product/serial coverage requires separately recorded policy terms; this record is not manufacturer verification.",
    )
    db.add(warranty)
    db.flush()
    add_audit(
        db,
        actor_user_id=user.id,
        action="warranty.activated",
        entity_type="warranty",
        entity_id=warranty.id,
        metadata={"order_id": str(order.id)},
    )
    db.flush()
    return warranty


def get_delivery(db: Session, user: User, delivery_id: uuid.UUID) -> Delivery:
    delivery = db.scalar(
        select(Delivery)
        .where(Delivery.id == delivery_id)
        .options(selectinload(Delivery.lines).selectinload(DeliveryLine.serials))
    )
    if delivery is None:
        raise AppError(404, "not_found", "Delivery not found.")
    order = db.get(SalesOrder, delivery.order_id)
    if order is None:
        raise AppError(404, "not_found", "Order not found.")
    if user.role_code in READ_ROLES:
        return delivery
    if user.role_code == "customer" and order.customer_user_id == user.id:
        return delivery
    if user.role_code == "customer":
        raise AppError(404, "not_found", "Delivery not found.")
    raise AppError(403, "forbidden", "You cannot view this delivery.")


def list_deliveries(db: Session, user: User) -> list[Delivery]:
    if user.role_code in READ_ROLES:
        query = (
            select(Delivery)
            .options(selectinload(Delivery.lines).selectinload(DeliveryLine.serials))
            .order_by(Delivery.created_at)
        )
        return list(db.scalars(query))
    if user.role_code == "customer":
        orders = set(
            db.scalars(select(SalesOrder.id).where(SalesOrder.customer_user_id == user.id)).all()
        )
        if not orders:
            return []
        return list(
            db.scalars(
                select(Delivery)
                .where(Delivery.order_id.in_(orders))
                .options(selectinload(Delivery.lines).selectinload(DeliveryLine.serials))
                .order_by(Delivery.created_at)
            )
        )
    raise AppError(403, "forbidden", "You cannot list deliveries.")


def get_warranty(db: Session, user: User, order_id: uuid.UUID) -> Warranty:
    warranty = db.scalar(select(Warranty).where(Warranty.order_id == order_id))
    if warranty is None:
        raise AppError(404, "not_found", "Warranty not found.")
    order = db.get(SalesOrder, order_id)
    if order is None:
        raise AppError(404, "not_found", "Order not found.")
    if user.role_code in READ_ROLES:
        return warranty
    if user.role_code == "customer" and order.customer_user_id == user.id:
        return warranty
    if user.role_code == "customer":
        raise AppError(404, "not_found", "Warranty not found.")
    raise AppError(403, "forbidden", "You cannot view this warranty.")


def void_warranty(db: Session, user: User, order_id: uuid.UUID) -> Warranty:
    if user.role_code not in {"support", "admin"}:
        raise AppError(403, "forbidden", "Only support can void a warranty.")
    warranty = db.scalar(select(Warranty).where(Warranty.order_id == order_id).with_for_update())
    if warranty is None:
        raise AppError(404, "not_found", "Warranty not found.")
    if warranty.status != "active":
        raise AppError(409, "invalid_transition", "Only an active warranty can be voided.")
    warranty.status = "void"
    add_audit(
        db,
        actor_user_id=user.id,
        action="warranty.void",
        entity_type="warranty",
        entity_id=warranty.id,
        metadata={"order_id": str(order_id)},
    )
    db.flush()
    return warranty
