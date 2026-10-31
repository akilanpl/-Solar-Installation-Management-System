"""Deliveries, picking and warranty activation.

A delivery is the picking record: it is created from a confirmed order,
moves prepared -> in_transit -> delivered, and confirmation flips it to
``confirmed`` and activates the five-year warranty in the same transaction.
Consuming reservations and checking ledger availability happen when the
delivery stock operation validates, so a failed delivery leaves both
unchanged.
"""

import hashlib
import json
import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.security import utcnow
from app.models.identity import User
from app.models.phase3 import Delivery, DeliveryLine, StockReservation, Warranty
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


def _check_pick_availability(db: Session, order: SalesOrder) -> None:
    """Picking needs real stock minus other orders' reservations."""
    from app.models.phase3 import StockLedger

    for line in order.lines:
        if line.line_kind != "material" or line.component_code is None:
            continue
        on_hand = db.scalar(
            select(func.coalesce(func.sum(StockLedger.quantity_delta), 0)).where(
                StockLedger.component_code == line.component_code
            )
        )
        reserved_others = db.scalar(
            select(func.coalesce(func.sum(StockReservation.quantity), 0)).where(
                StockReservation.component_code == line.component_code,
                StockReservation.status == "reserved",
                StockReservation.order_id != order.id,
            )
        )
        if int(on_hand or 0) - int(reserved_others or 0) < line.quantity:
            raise AppError(
                409,
                "insufficient_stock",
                f"Insufficient stock to pick {line.component_code}.",
            )


def create_delivery(
    db: Session, user: User, order_id: uuid.UUID, idempotency_key: str
) -> tuple[Delivery, bool]:
    if user.role_code not in WAREHOUSE:
        raise AppError(403, "forbidden", "Only warehouse staff can prepare a delivery.")
    order = db.scalar(
        select(SalesOrder).where(SalesOrder.id == order_id).options(selectinload(SalesOrder.lines))
    )
    if order is None:
        raise AppError(404, "not_found", "Order not found.")
    digest = _hash(order.id)
    existing = db.scalar(select(Delivery).where(Delivery.order_id == order.id))
    if existing is not None:
        if (
            existing.created_by_user_id == user.id
            and existing.idempotency_key == idempotency_key
            and existing.request_hash == digest
        ):
            return _load(db, existing.id), True
        raise AppError(409, "duplicate_delivery", "This order already has a delivery.")
    keyed = db.scalar(
        select(Delivery).where(
            Delivery.created_by_user_id == user.id,
            Delivery.idempotency_key == idempotency_key,
        )
    )
    if keyed is not None:
        if keyed.request_hash != digest:
            raise AppError(409, "idempotency_conflict", "This key was used for a different delivery.")
        return _load(db, keyed.id), True
    reservations = list(
        db.scalars(select(StockReservation).where(StockReservation.order_id == order.id))
    )
    if not reservations:
        raise AppError(409, "reservations_missing", "This order has no reservations to pick.")
    _check_pick_availability(db, order)
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
    position = 0
    for line in order.lines:
        if line.line_kind != "material" or line.component_code is None:
            continue
        db.add(
            DeliveryLine(
                delivery_id=delivery.id,
                component_code=line.component_code,
                quantity=line.quantity,
                sort_order=position,
            )
        )
        position += 1
    if position == 0:
        raise AppError(409, "nothing_to_deliver", "This order has no material lines.")
    add_audit(
        db,
        actor_user_id=user.id,
        action="delivery.prepared",
        entity_type="delivery",
        entity_id=delivery.id,
        metadata={"order_id": str(order.id)},
    )
    db.flush()
    return _load(db, delivery.id), False


def _load(db: Session, delivery_id: uuid.UUID) -> Delivery:
    loaded = db.scalar(
        select(Delivery).where(Delivery.id == delivery_id).options(selectinload(Delivery.lines))
    )
    if loaded is None:
        raise AppError(500, "delivery_missing", "The delivery could not be reloaded.")
    return loaded


def transition(db: Session, user: User, delivery_id: uuid.UUID, to_status: str) -> Delivery:
    allowed = {
        "prepared": {"in_transit", "cancelled"},
        "in_transit": {"delivered", "cancelled"},
        "delivered": {"confirmed"},
    }
    delivery = db.scalar(
        select(Delivery).where(Delivery.id == delivery_id).options(selectinload(Delivery.lines)).with_for_update()
    )
    if delivery is None:
        raise AppError(404, "not_found", "Delivery not found.")
    if to_status == "confirmed" and user.role_code not in CONFIRM_ROLES:
        raise AppError(403, "forbidden", "You cannot confirm this delivery.")
    if to_status != "confirmed" and user.role_code not in WAREHOUSE:
        raise AppError(403, "forbidden", "Only warehouse staff can move a delivery.")
    if delivery.status not in allowed or to_status not in allowed[delivery.status]:
        raise AppError(409, "invalid_transition", f"Cannot move delivery from {delivery.status} to {to_status}.")
    delivery.status = to_status
    if to_status == "confirmed":
        delivery.confirmed_at = utcnow()
        from app.services.inventory_service import consume_reservations as _consume

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
        coverage_note="Five-year workmanship and panel warranty from delivery confirmation.",
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
        select(Delivery).where(Delivery.id == delivery_id).options(selectinload(Delivery.lines))
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
        query = select(Delivery).options(selectinload(Delivery.lines)).order_by(Delivery.created_at)
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
                .options(selectinload(Delivery.lines))
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
