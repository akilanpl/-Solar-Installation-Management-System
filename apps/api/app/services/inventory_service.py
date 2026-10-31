"""Warehouse inventory: operations, ledger, reservations, serials, replenishment.

Ledger rows are the stock truth and are written by validated stock commands
in the same transaction that flips the operation to ``done``. A failed
validation raises before any ledger insert, so stock and the ledger stay
unchanged. Concurrent validations serialize on the operation row lock plus
product/location pairs taken in a stable order.
"""

import hashlib
import json
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.security import utcnow
from app.models.custody import StockSerialMovement
from app.models.identity import User
from app.models.phase3 import (
    EquipmentSerial,
    ReplenishmentRequest,
    StockLedger,
    StockOperation,
    StockOperationLine,
    StockReservation,
    WarehouseLocation,
)
from app.models.workflow import CatalogueComponent, SalesOrder
from app.repositories.queries import add_audit
from app.services.references import next_reference

WAREHOUSE = {"warehouse_staff", "warehouse_manager", "admin"}
MANAGER = {"warehouse_manager", "admin"}
ZERO = Decimal("0")


def _hash(operation_type: str, lines: list[dict]) -> str:
    raw = json.dumps(
        {"type": operation_type, "lines": lines}, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _line_payload(
    component: str, quantity: str, from_location: str | None, to_location: str | None, serials=None
) -> dict:
    return {
        "component": component,
        "quantity": quantity,
        "from": from_location,
        "to": to_location,
        "serials": sorted(str(value) for value in (serials or [])),
    }


def on_hand(db: Session, component_code: str, location_code: str) -> Decimal:
    total = db.scalar(
        select(func.coalesce(func.sum(StockLedger.quantity_delta), 0)).where(
            StockLedger.component_code == component_code,
            StockLedger.location_code == location_code,
        )
    )
    return Decimal(str(total or "0"))


def stock_levels(db: Session, user: User) -> list[dict]:
    if user.role_code not in WAREHOUSE | {"sales"}:
        raise AppError(403, "forbidden", "You cannot view stock.")
    rows = db.execute(
        select(
            StockLedger.component_code,
            StockLedger.location_code,
            func.sum(StockLedger.quantity_delta).label("on_hand"),
        ).group_by(StockLedger.component_code, StockLedger.location_code)
    ).all()
    return [
        {
            "component_code": row[0],
            "location_code": row[1],
            "on_hand": Decimal(str(row[2])),
        }
        for row in rows
    ]


def _check_component(db: Session, code: str) -> None:
    if db.get(CatalogueComponent, code) is None:
        raise AppError(400, "unknown_component", f"Unknown component {code}.")


def _check_location(db: Session, code: str) -> None:
    if db.get(WarehouseLocation, code) is None:
        raise AppError(400, "unknown_location", f"Unknown location {code}.")


def create_operation(
    db: Session,
    user: User,
    operation_type: str,
    lines: list[dict],
    note: str | None,
    source_order_id: uuid.UUID | None,
    idempotency_key: str,
) -> tuple[StockOperation, bool]:
    if user.role_code not in WAREHOUSE:
        raise AppError(403, "forbidden", "Only warehouse staff can create stock operations.")
    if operation_type not in ("receipt", "transfer", "delivery", "adjustment"):
        raise AppError(400, "invalid_operation_type", "Unknown operation type.")
    if not lines:
        raise AppError(400, "empty_operation", "An operation needs at least one line.")
    if operation_type == "adjustment" and (
        user.role_code not in MANAGER or not note or len(note.strip()) < 5
    ):
        raise AppError(
            403,
            "adjustment_approval_required",
            "A manager and recorded count/reconciliation reason are required for adjustments.",
        )
    selected = [str(serial) for line in lines for serial in line.get("serial_ids", [])]
    if len(selected) > 500 or len(selected) != len(set(selected)):
        raise AppError(
            422, "duplicate_serial", "Select at most 500 distinct units in one operation."
        )
    if operation_type == "receipt" and selected:
        raise AppError(
            422,
            "receipt_serial_registration",
            "Register new unit identities after validating the goods receipt.",
        )
    payload = [
        _line_payload(
            str(item["component_code"]).upper(),
            str(item["quantity"]),
            item.get("from_location"),
            item.get("to_location"),
            item.get("serial_ids", []),
        )
        for item in lines
    ]
    digest = _hash(operation_type, payload)
    existing = db.scalar(
        select(StockOperation).where(
            StockOperation.created_by_user_id == user.id,
            StockOperation.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.request_hash != digest:
            raise AppError(
                409, "idempotency_conflict", "This key was used for a different operation."
            )
        loaded = db.scalar(
            select(StockOperation)
            .where(StockOperation.id == existing.id)
            .options(selectinload(StockOperation.lines).selectinload(StockOperationLine.serials))
        )
        assert loaded is not None
        return loaded, True
    if source_order_id is not None and db.get(SalesOrder, source_order_id) is None:
        raise AppError(404, "not_found", "Order not found.")
    operation = StockOperation(
        reference=next_reference(db, "stock_operation", "STK"),
        operation_type=operation_type,
        status="draft",
        source_order_id=source_order_id,
        note=note,
        created_by_user_id=user.id,
        idempotency_key=idempotency_key,
        request_hash=digest,
    )
    db.add(operation)
    db.flush()
    for position, item in enumerate(lines):
        code = str(item["component_code"]).upper()
        _check_component(db, code)
        try:
            quantity = Decimal(str(item["quantity"]))
        except Exception as exc:
            raise AppError(400, "invalid_quantity", "Quantities must be numeric.") from exc
        if quantity == ZERO:
            raise AppError(400, "invalid_quantity", "Quantities cannot be zero.")
        if operation_type != "adjustment" and quantity < ZERO:
            raise AppError(400, "invalid_quantity", "Only adjustments accept negative quantities.")
        from_location = item.get("from_location")
        to_location = item.get("to_location")
        if from_location is not None:
            _check_location(db, from_location)
        if to_location is not None:
            _check_location(db, to_location)
        if operation_type == "receipt" and to_location is None:
            raise AppError(400, "location_required", "Receipts need a destination location.")
        if operation_type == "transfer" and (from_location is None or to_location is None):
            raise AppError(400, "location_required", "Transfers need a source and a destination.")
        if operation_type == "delivery" and from_location is None:
            raise AppError(400, "location_required", "Deliveries need a source location.")
        if operation_type == "adjustment" and to_location is None and from_location is None:
            raise AppError(400, "location_required", "Adjustments need a location.")
        line = StockOperationLine(
            operation_id=operation.id,
            component_code=code,
            quantity=quantity,
            from_location=from_location,
            to_location=to_location,
            sort_order=position,
        )
        db.add(line)
        db.flush()
        for serial_id in item.get("serial_ids", []):
            serial = db.get(EquipmentSerial, serial_id)
            if serial is None or serial.component_code != code:
                raise AppError(
                    422,
                    "serial_component_mismatch",
                    "Selected serial must belong to this component.",
                )
            db.add(
                StockSerialMovement(
                    operation_id=operation.id,
                    line_id=line.id,
                    serial_id=serial.id,
                    serial_number=serial.serial_number,
                )
            )
    db.flush()
    add_audit(
        db,
        actor_user_id=user.id,
        action="stock_operation.created",
        entity_type="stock_operation",
        entity_id=operation.id,
        metadata={"operation_type": operation_type},
    )
    db.flush()
    loaded = db.scalar(
        select(StockOperation)
        .where(StockOperation.id == operation.id)
        .options(selectinload(StockOperation.lines).selectinload(StockOperationLine.serials))
    )
    assert loaded is not None
    return loaded, False


def mark_ready(db: Session, user: User, operation_id: uuid.UUID) -> StockOperation:
    if user.role_code not in WAREHOUSE:
        raise AppError(403, "forbidden", "Only warehouse staff can ready an operation.")
    operation = db.scalar(
        select(StockOperation)
        .where(StockOperation.id == operation_id)
        .options(selectinload(StockOperation.lines).selectinload(StockOperationLine.serials))
        .with_for_update()
    )
    if operation is None:
        raise AppError(404, "not_found", "Stock operation not found.")
    if operation.status != "draft":
        raise AppError(409, "invalid_transition", "Only draft operations become ready.")
    operation.status = "ready"
    add_audit(
        db,
        actor_user_id=user.id,
        action="stock_operation.ready",
        entity_type="stock_operation",
        entity_id=operation.id,
        metadata={},
    )
    db.flush()
    return operation


def cancel_operation(db: Session, user: User, operation_id: uuid.UUID) -> StockOperation:
    if user.role_code not in WAREHOUSE:
        raise AppError(403, "forbidden", "Only warehouse staff can cancel an operation.")
    operation = db.scalar(
        select(StockOperation)
        .where(StockOperation.id == operation_id)
        .options(selectinload(StockOperation.lines).selectinload(StockOperationLine.serials))
        .with_for_update()
    )
    if operation is None:
        raise AppError(404, "not_found", "Stock operation not found.")
    if operation.status == "done":
        raise AppError(409, "invalid_transition", "A validated operation cannot be cancelled.")
    if operation.status == "cancelled":
        raise AppError(409, "invalid_transition", "This operation is already cancelled.")
    operation.status = "cancelled"
    add_audit(
        db,
        actor_user_id=user.id,
        action="stock_operation.cancelled",
        entity_type="stock_operation",
        entity_id=operation.id,
        metadata={},
    )
    db.flush()
    return operation


def lock_components(db: Session, codes: list[str]) -> None:
    """Lock catalogue rows in a stable order so concurrent stock writers serialize."""
    for code in sorted(set(codes)):
        row = db.scalar(
            select(CatalogueComponent).where(CatalogueComponent.code == code).with_for_update()
        )
        if row is None:
            raise AppError(400, "unknown_component", f"Unknown component {code}.")


def validate_operation(db: Session, user: User, operation_id: uuid.UUID) -> StockOperation:
    """Validate a ready operation, writing ledger rows in one transaction."""
    if user.role_code not in WAREHOUSE:
        raise AppError(403, "forbidden", "Only warehouse staff can validate stock.")
    operation = db.scalar(
        select(StockOperation)
        .where(StockOperation.id == operation_id)
        .options(selectinload(StockOperation.lines).selectinload(StockOperationLine.serials))
        .with_for_update()
    )
    if operation is None:
        raise AppError(404, "not_found", "Stock operation not found.")
    if operation.status != "ready":
        raise AppError(409, "invalid_transition", "Only ready operations validate.")
    lock_components(db, [line.component_code for line in operation.lines])
    deltas: list[tuple[str, str, Decimal]] = []
    for line in sorted(
        operation.lines,
        key=lambda item: (item.component_code, item.from_location or "", item.to_location or ""),
    ):
        quantity = Decimal(str(line.quantity))
        if operation.operation_type == "receipt":
            assert line.to_location is not None
            deltas.append((line.component_code, line.to_location, quantity))
        elif operation.operation_type == "transfer":
            assert line.from_location is not None and line.to_location is not None
            available = on_hand(db, line.component_code, line.from_location)
            if available < quantity:
                raise AppError(
                    409, "insufficient_stock", f"Insufficient stock for {line.component_code}."
                )
            deltas.append((line.component_code, line.from_location, -quantity))
            deltas.append((line.component_code, line.to_location, quantity))
        elif operation.operation_type == "delivery":
            assert line.from_location is not None
            available = on_hand(db, line.component_code, line.from_location)
            if available < quantity:
                raise AppError(
                    409, "insufficient_stock", f"Insufficient stock for {line.component_code}."
                )
            deltas.append((line.component_code, line.from_location, -quantity))
        else:
            location = line.to_location or line.from_location
            assert location is not None
            if quantity < ZERO:
                available = on_hand(db, line.component_code, location)
                if available + quantity < ZERO:
                    raise AppError(
                        409,
                        "insufficient_stock",
                        f"Adjustment would drive {line.component_code} negative.",
                    )
            deltas.append((line.component_code, location, quantity))
    # Every line was checked against the same starting balance above. Check the
    # combined operation too: duplicate lines must never collectively overdraw.
    gross_debits: dict[tuple[str, str], Decimal] = {}
    net: dict[tuple[str, str], Decimal] = {}
    for code, location, delta in deltas:
        key = (code, location)
        net[key] = net.get(key, ZERO) + delta
        if delta < ZERO:
            gross_debits[key] = gross_debits.get(key, ZERO) - delta
    from app.services.location_allocation import outstanding

    for (code, location), debit in gross_debits.items():
        if on_hand(db, code, location) - debit < outstanding(db, code, location):
            raise AppError(
                409,
                "insufficient_stock",
                "Outgoing stock exceeds the unallocated starting balance.",
            )
    for (code, location), delta in net.items():
        if delta < ZERO and on_hand(db, code, location) + delta < outstanding(db, code, location):
            raise AppError(
                409, "insufficient_stock", f"Operation would drive {code} at {location} negative."
            )
    from app.services.serial_custody import validate_movement

    serial_changes = validate_movement(db, operation)
    for component_code, location_code, delta in deltas:
        db.add(
            StockLedger(
                operation_id=operation.id,
                component_code=component_code,
                location_code=location_code,
                quantity_delta=delta,
            )
        )
    for serial, state, location in serial_changes:
        serial.status = state
        serial.location_code = location
    operation.status = "done"
    operation.validated_at = utcnow()
    add_audit(
        db,
        actor_user_id=user.id,
        action="stock_operation.validated",
        entity_type="stock_operation",
        entity_id=operation.id,
        metadata={"ledger_rows": len(deltas)},
    )
    db.flush()
    loaded = db.scalar(
        select(StockOperation)
        .where(StockOperation.id == operation.id)
        .options(selectinload(StockOperation.lines).selectinload(StockOperationLine.serials))
    )
    assert loaded is not None
    return loaded


def get_operation(db: Session, user: User, operation_id: uuid.UUID) -> StockOperation:
    if user.role_code not in WAREHOUSE | {"sales"}:
        raise AppError(403, "forbidden", "You cannot view stock operations.")
    operation = db.scalar(
        select(StockOperation)
        .where(StockOperation.id == operation_id)
        .options(selectinload(StockOperation.lines).selectinload(StockOperationLine.serials))
    )
    if operation is None:
        raise AppError(404, "not_found", "Stock operation not found.")
    return operation


def reserve_for_order(db: Session, order: SalesOrder) -> list[StockReservation]:
    """Create one reservation per material line. Called from order confirmation."""
    created: list[StockReservation] = []
    for line in order.lines:
        if line.line_kind != "material" or line.component_code is None:
            continue
        existing = db.scalar(
            select(StockReservation).where(
                StockReservation.order_id == order.id,
                StockReservation.component_code == line.component_code,
            )
        )
        if existing is not None:
            created.append(existing)
            continue
        reservation = StockReservation(
            order_id=order.id,
            component_code=line.component_code,
            quantity=line.quantity,
            status="reserved",
        )
        db.add(reservation)
        created.append(reservation)
    db.flush()
    return created


def list_reservations(
    db: Session, user: User, order_id: uuid.UUID | None = None
) -> list[StockReservation]:
    if user.role_code not in WAREHOUSE | {"sales", "admin"}:
        raise AppError(403, "forbidden", "You cannot view reservations.")
    query = select(StockReservation).order_by(StockReservation.created_at)
    if order_id is not None:
        query = query.where(StockReservation.order_id == order_id)
    return list(db.scalars(query))


def consume_reservations(db: Session, order_id: uuid.UUID) -> None:
    rows = list(
        db.scalars(
            select(StockReservation).where(StockReservation.order_id == order_id).with_for_update()
        )
    )
    for row in rows:
        if row.status != "reserved":
            raise AppError(409, "invalid_transition", "Reservations are no longer reserved.")
        row.status = "consumed"
    db.flush()


def replacement_stock_movement(db, user, replacement_id, *, restock=False):
    """Post one exact unit for an authorized replacement, never generic dispatch.

    The persisted replacement owns authorization and idempotency. This path
    cannot be selected by stock-operation HTTP input and cannot move any unit
    other than the approved replacement's named serial.
    """
    from app.models.support import ServiceTicket
    from app.models.warranty import ReplacementDecision
    from app.services.location_allocation import outstanding

    if user.role_code not in WAREHOUSE:
        raise AppError(403, "forbidden", "Only warehouse staff can move replacement stock.")
    replacement = db.scalar(select(ReplacementDecision).where(
        ReplacementDecision.id == replacement_id).with_for_update())
    expected = "installed" if restock else "approved"
    if replacement is None or replacement.status != expected:
        raise AppError(409, "invalid_transition", "Replacement is not ready for this movement.")
    ticket = db.get(ServiceTicket, replacement.ticket_id)
    serial_id = replacement.old_serial_id if restock else replacement.new_serial_id
    peek = db.get(EquipmentSerial, serial_id)
    if ticket is None or peek is None:
        raise AppError(404, "not_found", "Replacement source not found.")
    lock_components(db, [peek.component_code])
    serial = db.scalar(select(EquipmentSerial).where(EquipmentSerial.id == serial_id)
                       .with_for_update().execution_options(populate_existing=True))
    required_status = "returned" if restock else "reserved"
    if serial.status != required_status or serial.order_id != ticket.order_id:
        raise AppError(409, "invalid_serial_state", "Replacement unit custody changed.")
    location = "MAIN" if restock else serial.location_code
    if not location or location == "QUARANTINE":
        raise AppError(409, "invalid_serial_state", "A usable exact stock location is required.")
    _check_location(db, location)
    if not restock:
        receipt = db.get(StockOperation, serial.operation_id) if serial.operation_id else None
        if receipt is None or receipt.operation_type != "receipt" or receipt.status != "done":
            raise AppError(409, "receipt_required", "A validated receipt must back the issued unit.")
        if on_hand(db, serial.component_code, location) - 1 < outstanding(
                db, serial.component_code, location):
            raise AppError(409, "insufficient_stock", "Replacement exceeds unallocated stock.")
    operation, reused = create_operation(
        db, user, "receipt" if restock else "delivery",
        [{"component_code": serial.component_code, "quantity": "1.0000",
          "from_location": None if restock else location,
          "to_location": location if restock else None}],
        f"Inspected replacement return {replacement.reference}" if restock
        else f"Approved replacement issue {replacement.reference}",
        ticket.order_id, f"replacement-{'return' if restock else 'issue'}-{replacement.id}",
    )
    if reused:
        raise AppError(409, "invalid_transition", "Replacement movement already exists.")
    line = operation.lines[0]
    db.add(StockSerialMovement(operation_id=operation.id, line_id=line.id,
                               serial_id=serial.id, serial_number=serial.serial_number))
    db.add(StockLedger(operation_id=operation.id, component_code=serial.component_code,
                       location_code=location, quantity_delta=1 if restock else -1))
    operation.status = "done"
    operation.validated_at = utcnow()
    serial.status = "in_stock" if restock else "in_transit"
    serial.location_code = location if restock else None
    if restock:
        serial.order_id = None
        serial.operation_id = operation.id
    add_audit(db, actor_user_id=user.id, action="replacement.stock_validated",
              entity_type="stock_operation", entity_id=operation.id,
              metadata={"replacement_id": str(replacement.id), "serial_id": str(serial.id),
                        "direction": "return" if restock else "issue"})
    db.flush()
    return operation


def scan_serial(
    db: Session, user: User, serial_number: str, component_code: str, operation_id: uuid.UUID | None
) -> EquipmentSerial:
    if user.role_code not in WAREHOUSE:
        raise AppError(403, "forbidden", "Only warehouse staff can scan serials.")
    _check_component(db, component_code)
    serial = serial_number.strip().upper()
    if (
        db.scalar(select(EquipmentSerial).where(EquipmentSerial.serial_number == serial))
        is not None
    ):
        raise AppError(409, "serial_exists", "This serial number is already registered.")
    operation = None
    if operation_id is not None:
        operation = db.scalar(
            select(StockOperation).where(StockOperation.id == operation_id).with_for_update()
        )
        if operation is None:
            raise AppError(404, "not_found", "Stock operation not found.")
        if operation.status != "done" or operation.operation_type != "receipt":
            raise AppError(
                409, "receipt_not_validated", "Serial custody requires a validated goods receipt."
            )
        matched = list(
            db.scalars(
                select(StockOperationLine).where(
                    StockOperationLine.operation_id == operation.id,
                    StockOperationLine.component_code == component_code,
                )
            )
        )
        locations = {line.to_location for line in matched if line.to_location}
        units = sum(line.quantity for line in matched)
        registered = int(
            db.scalar(
                select(func.count())
                .select_from(EquipmentSerial)
                .where(
                    EquipmentSerial.operation_id == operation.id,
                    EquipmentSerial.component_code == component_code,
                )
            )
            or 0
        )
        if len(locations) != 1 or registered + 1 > units:
            raise AppError(
                409,
                "serial_receipt_mismatch",
                "Receipt must contain an unregistered unit of this component at one location.",
            )
        location = next(iter(locations))
        usable = int(
            db.scalar(
                select(func.count())
                .select_from(EquipmentSerial)
                .where(
                    EquipmentSerial.component_code == component_code,
                    EquipmentSerial.location_code == location,
                    EquipmentSerial.status.in_(("in_stock", "reserved")),
                )
            )
            or 0
        )
        if Decimal(usable + 1) > on_hand(db, component_code, location):
            raise AppError(
                409,
                "serial_stock_mismatch",
                "No unidentified received unit remains in stock at this location.",
            )
    else:
        location = None
    row = EquipmentSerial(
        serial_number=serial,
        component_code=component_code,
        status="in_stock" if operation else "registered",
        location_code=location,
        order_id=None,
        operation_id=operation.id if operation else None,
    )
    db.add(row)
    db.flush()
    if operation:
        from app.services.serial_custody import attach_received_unit

        attach_received_unit(db, operation, row, component_code, location)
        db.flush()
    add_audit(
        db,
        actor_user_id=user.id,
        action="serial.scanned",
        entity_type="equipment_serial",
        entity_id=row.id,
        metadata={"serial_number": serial, "component_code": component_code},
    )
    db.flush()
    return row


def request_replenishment(
    db: Session, user: User, component_code: str, location_code: str, quantity: int
) -> ReplenishmentRequest:
    if user.role_code not in WAREHOUSE:
        raise AppError(403, "forbidden", "Only warehouse staff can request replenishment.")
    code = component_code.strip().upper()
    _check_component(db, code)
    _check_location(db, location_code)
    row = ReplenishmentRequest(
        reference=next_reference(db, "replenishment", "RPL"),
        component_code=code,
        location_code=location_code,
        quantity=quantity,
        status="proposed",
        requested_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    add_audit(
        db,
        actor_user_id=user.id,
        action="replenishment.requested",
        entity_type="replenishment_request",
        entity_id=row.id,
        metadata={"component_code": code, "quantity": quantity},
    )
    db.flush()
    return row


def decide_replenishment(
    db: Session, user: User, request_id: uuid.UUID, decision: str
) -> ReplenishmentRequest:
    if user.role_code not in MANAGER:
        raise AppError(403, "forbidden", "Only a warehouse manager can decide replenishment.")
    row = db.scalar(
        select(ReplenishmentRequest).where(ReplenishmentRequest.id == request_id).with_for_update()
    )
    if row is None:
        raise AppError(404, "not_found", "Replenishment request not found.")
    if row.status != "proposed":
        raise AppError(409, "invalid_transition", "This request is already decided.")
    if decision == "approve":
        row.status = "approved"
    elif decision == "reject":
        row.status = "rejected"
    else:
        raise AppError(400, "invalid_decision", "Decision must be approve or reject.")
    row.decided_by_user_id = user.id
    row.decided_at = utcnow()
    add_audit(
        db,
        actor_user_id=user.id,
        action="replenishment.decided",
        entity_type="replenishment_request",
        entity_id=row.id,
        metadata={"decision": decision},
    )
    db.flush()
    return row


def threshold_suggestion(db: Session, component_code: str, threshold: int = 10) -> dict:
    total = db.scalar(
        select(func.coalesce(func.sum(StockLedger.quantity_delta), 0)).where(
            StockLedger.component_code == component_code
        )
    )
    on_hand_total = int(Decimal(str(total or "0")))
    reserved = db.scalar(
        select(func.coalesce(func.sum(StockReservation.quantity), 0)).where(
            StockReservation.component_code == component_code,
            StockReservation.status == "reserved",
        )
    )
    reserved_total = int(reserved or 0)
    available = on_hand_total - reserved_total
    return {
        "component_code": component_code,
        "on_hand": on_hand_total,
        "reserved": reserved_total,
        "available": available,
        "below_threshold": available < threshold,
        "suggested_quantity": max(0, threshold * 2 - available),
    }
