"""Serial identities must reconcile with the ledger before serialized stock moves."""

from decimal import Decimal

from sqlalchemy import func, select

from app.core.errors import AppError
from app.models.custody import StockSerialMovement
from app.models.phase3 import EquipmentSerial, StockOperationLine
from app.models.workflow import CatalogueComponent


def tracked(db, code):
    component = db.get(CatalogueComponent, code)
    return bool(component and component.requires_serial_tracking)


def require_registered_balance(db, code, location):
    from app.services.inventory_service import on_hand

    if not tracked(db, code) or location == "QUARANTINE":
        return
    balance = on_hand(db, code, location)
    units = int(
        db.scalar(
            select(func.count())
            .select_from(EquipmentSerial)
            .where(
                EquipmentSerial.component_code == code,
                EquipmentSerial.location_code == location,
                EquipmentSerial.status.in_(("in_stock", "reserved")),
            )
        )
        or 0
    )
    if balance != Decimal(units):
        raise AppError(
            409,
            "serial_registration_required",
            f"Reconcile every received {code} unit at {location} with its actual serial before allocation or movement.",
        )


def validate_movement(db, operation):
    changes = []
    unidentified_outflow = {}
    for line in operation.lines:
        serial_required = tracked(db, line.component_code)
        quantity = Decimal(line.quantity)
        if serial_required and quantity != quantity.to_integral_value():
            raise AppError(422, "serialized_quantity", "Serialized hardware moves in whole units.")
        if operation.operation_type == "receipt":
            continue  # Unit identities are registered against this validated receipt.
        location = (
            line.from_location
            if operation.operation_type in {"transfer", "delivery"}
            else line.to_location or line.from_location
        )
        if location == "QUARANTINE" and operation.operation_type in {"transfer", "delivery"}:
            raise AppError(
                409,
                "quarantine_blocked",
                "Quarantined stock requires inspected disposition; it cannot be dispatched or transferred as usable stock.",
            )
        if serial_required and operation.operation_type == "delivery":
            raise AppError(
                409,
                "use_order_fulfilment",
                "Dispatch serialized hardware through an order delivery with exact unit custody.",
            )
        movements = list(
            db.scalars(
                select(StockSerialMovement)
                .where(StockSerialMovement.line_id == line.id)
                .order_by(StockSerialMovement.serial_id)
            )
        )
        if serial_required and len(movements) != abs(quantity):
            raise AppError(
                409,
                "serials_required",
                "Select the exact serial identities for every serialized unit moved.",
            )
        if operation.operation_type in {"transfer", "delivery"} or quantity < 0:
            from app.services.inventory_service import on_hand

            known = int(
                db.scalar(
                    select(func.count())
                    .select_from(EquipmentSerial)
                    .where(
                        EquipmentSerial.component_code == line.component_code,
                        EquipmentSerial.location_code == location,
                        EquipmentSerial.status.in_(("in_stock", "reserved")),
                    )
                )
                or 0
            )
            anonymous = max(Decimal(0), on_hand(db, line.component_code, location) - known)
            key = (line.component_code, location)
            unidentified_outflow[key] = (
                unidentified_outflow.get(key, Decimal(0)) + abs(quantity) - len(movements)
            )
            if unidentified_outflow[key] > anonymous:
                raise AppError(
                    409,
                    "serials_required",
                    "Movement would lose a known unit identity; select its serial explicitly.",
                )
        if len(movements) > abs(quantity):
            raise AppError(
                409, "serial_quantity_mismatch", "Selected serials exceed the moved unit count."
            )
        if quantity < 0 or operation.operation_type in {"transfer", "delivery"}:
            require_registered_balance(db, line.component_code, location)
        for movement in movements:
            serial = db.scalar(
                select(EquipmentSerial)
                .where(EquipmentSerial.id == movement.serial_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if (
                serial is None
                or serial.component_code != line.component_code
                or serial.serial_number != movement.serial_number
            ):
                raise AppError(
                    409,
                    "serial_component_mismatch",
                    "A selected serial does not match this stock line.",
                )
            if operation.operation_type == "adjustment" and quantity > 0:
                if serial.status != "missing" or serial.order_id is not None:
                    raise AppError(
                        409,
                        "invalid_serial_state",
                        "A positive counted-stock correction can restore only a previously recorded missing unit.",
                    )
                changes.append((serial, "in_stock", location))
            else:
                if (
                    serial.status != "in_stock"
                    or serial.location_code != location
                    or serial.order_id is not None
                ):
                    raise AppError(
                        409,
                        "invalid_serial_state",
                        "A moved unit must be unassigned and in stock at the exact source location.",
                    )
                state = (
                    "missing"
                    if operation.operation_type == "adjustment"
                    else "in_stock"
                    if operation.operation_type == "transfer"
                    else "in_transit"
                )
                changes.append(
                    (
                        serial,
                        state,
                        line.to_location if operation.operation_type == "transfer" else None,
                    )
                )
    return changes


def attach_received_unit(db, operation, serial, component, location):
    lines = list(
        db.scalars(
            select(StockOperationLine)
            .where(
                StockOperationLine.operation_id == operation.id,
                StockOperationLine.component_code == component,
                StockOperationLine.to_location == location,
            )
            .order_by(StockOperationLine.sort_order)
        )
    )
    for line in lines:
        used = int(
            db.scalar(
                select(func.count())
                .select_from(StockSerialMovement)
                .where(StockSerialMovement.line_id == line.id)
            )
            or 0
        )
        if used < line.quantity:
            db.add(
                StockSerialMovement(
                    operation_id=operation.id,
                    line_id=line.id,
                    serial_id=serial.id,
                    serial_number=serial.serial_number,
                )
            )
            return
    raise AppError(
        409, "serial_receipt_mismatch", "All receipt unit identities are already registered."
    )


def require_order_delivered(db, order_id):
    """Installation needs confirmed net quantities and all tracked unit identities."""
    from collections import defaultdict

    from app.models.operations import GoodsReturn
    from app.models.phase3 import Delivery, DeliveryLine
    from app.models.workflow import SalesOrderLine

    required = defaultdict(int)
    for line in db.scalars(select(SalesOrderLine).where(SalesOrderLine.order_id == order_id)):
        if line.line_kind == "material":
            required[line.component_code] += line.quantity
    delivered = defaultdict(int)
    lines = list(
        db.scalars(
            select(DeliveryLine)
            .join(Delivery)
            .where(Delivery.order_id == order_id, Delivery.status == "confirmed")
        )
    )
    for line in lines:
        returned = db.scalar(
            select(func.coalesce(func.sum(GoodsReturn.quantity), 0)).where(
                GoodsReturn.delivery_line_id == line.id
            )
        )
        delivered[line.component_code] += line.quantity - int(returned)
    for code, quantity in required.items():
        if delivered[code] != quantity:
            raise AppError(
                409,
                "delivery_required",
                "Confirm every ordered material quantity before installation completion; pending returns require resolution.",
            )
        if tracked(db, code):
            units = db.scalar(
                select(func.count())
                .select_from(EquipmentSerial)
                .join(DeliveryLine, EquipmentSerial.delivery_line_id == DeliveryLine.id)
                .join(Delivery)
                .where(
                    EquipmentSerial.order_id == order_id,
                    EquipmentSerial.component_code == code,
                    EquipmentSerial.status == "delivered",
                    Delivery.status == "confirmed",
                )
            )
            if units != quantity:
                raise AppError(
                    409,
                    "serial_custody_required",
                    "Every installed hardware unit needs exact confirmed delivery custody.",
                )
