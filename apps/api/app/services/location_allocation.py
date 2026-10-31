"""Physical reservations, distinct from unallocated sales-order demand."""

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.operations import StockAllocation
from app.models.phase3 import StockReservation, WarehouseLocation
from app.models.workflow import SalesOrder
from app.repositories.queries import add_audit
from app.services.inventory_service import lock_components, on_hand


def outstanding(db: Session, code: str, location: str, exclude_order=None) -> Decimal:
    query = (
        select(
            func.coalesce(func.sum(StockAllocation.quantity - StockAllocation.picked_quantity), 0)
        )
        .join(StockReservation, StockAllocation.reservation_id == StockReservation.id)
        .where(
            StockReservation.component_code == code,
            StockReservation.status == "reserved",
            StockAllocation.location_code == location,
        )
    )
    if exclude_order is not None:
        query = query.where(StockReservation.order_id != exclude_order)
    return Decimal(db.scalar(query) or 0)


def allocate(db, user, order_id, lines):
    if user.role_code not in {"warehouse_staff", "warehouse_manager", "admin"}:
        raise AppError(403, "forbidden", "Only warehouse staff can allocate stock.")
    order = db.scalar(select(SalesOrder).where(SalesOrder.id == order_id).with_for_update())
    if order is None:
        raise AppError(404, "not_found", "Order not found.")
    reservations = {
        r.component_code: r
        for r in db.scalars(
            select(StockReservation).where(StockReservation.order_id == order_id).with_for_update()
        )
    }
    if not lines:
        raise AppError(422, "empty_allocation", "Choose actual location quantities.")
    lock_components(db, list(reservations))
    wanted = defaultdict(int)
    for item in lines:
        code, loc, qty = item["component_code"], item["location_code"], item["quantity"]
        if (
            qty < 0
            or code not in reservations
            or loc == "QUARANTINE"
            or db.get(WarehouseLocation, loc) is None
        ):
            raise AppError(
                422,
                "invalid_allocation",
                "Select an ordered component, nonnegative allocation quantity and usable location.",
            )
        wanted[(code, loc)] += qty
    for (code, loc), qty in sorted(wanted.items()):
        r = reservations[code]
        if r.status != "reserved":
            raise AppError(409, "reservation_closed", "Reservation is closed.")
        from app.services.serial_custody import require_registered_balance

        if qty:
            require_registered_balance(db, code, loc)
        total = int(
            db.scalar(
                select(func.coalesce(func.sum(StockAllocation.quantity), 0)).where(
                    StockAllocation.reservation_id == r.id
                )
            )
            or 0
        )
        row = db.scalar(
            select(StockAllocation)
            .where(StockAllocation.reservation_id == r.id, StockAllocation.location_code == loc)
            .with_for_update()
        )
        previous = row.quantity if row else 0
        picked = row.picked_quantity if row else 0
        if qty < picked or total - previous + qty > r.quantity:
            raise AppError(
                409,
                "over_allocation",
                "Allocation must cover picked units and cannot exceed order demand.",
            )
        if on_hand(db, code, loc) - outstanding(db, code, loc) + previous - picked < qty - picked:
            raise AppError(
                409, "insufficient_stock", "Location stock is already allocated or insufficient."
            )
        if row and qty == 0:
            db.delete(row)
        elif row:
            row.quantity = qty
        elif qty > 0:
            db.add(
                StockAllocation(
                    reservation_id=r.id, location_code=loc, quantity=qty, picked_quantity=0
                )
            )
        db.flush()
    add_audit(
        db,
        actor_user_id=user.id,
        action="stock.allocated",
        entity_type="sales_order",
        entity_id=order_id,
        metadata={
            "locations": [
                {"component": c, "location": location, "quantity": q}
                for (c, location), q in wanted.items()
            ]
        },
    )
    return list(
        db.scalars(
            select(StockAllocation)
            .join(StockReservation, StockAllocation.reservation_id == StockReservation.id)
            .where(StockReservation.order_id == order_id)
        )
    )
