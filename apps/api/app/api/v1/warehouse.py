from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.identity import User
from app.schemas import parse_idempotency_key
from app.schemas.phase3 import (
    DeliveryCreate,
    DeliveryLineResponse,
    DeliveryResponse,
    ReplenishmentCreate,
    ReplenishmentDecision,
    ReplenishmentResponse,
    ReservationCreate,
    ReservationResponse,
    SerialAssign,
    SerialResponse,
    SerialScanCreate,
    StockLevelResponse,
    StockOperationCreate,
    StockOperationLineResponse,
    StockOperationResponse,
)
from app.services import fulfillment_service, inventory_service

router = APIRouter(tags=["warehouse"])


def _key(value: str | None) -> str:
    try:
        return parse_idempotency_key(value)
    except ValueError as exc:
        raise AppError(400, "idempotency_key_required", str(exc)) from exc


def _operation_payload(operation) -> StockOperationResponse:
    return StockOperationResponse(
        id=operation.id,
        reference=operation.reference,
        operation_type=operation.operation_type,
        status=operation.status,
        source_order_id=operation.source_order_id,
        note=operation.note,
        lines=[
            StockOperationLineResponse(
                component_code=line.component_code,
                quantity=line.quantity,
                from_location=line.from_location,
                to_location=line.to_location,
                sort_order=line.sort_order,
            )
            for line in operation.lines
        ],
        created_at=operation.created_at,
        validated_at=operation.validated_at,
    )


def _delivery_payload(delivery) -> DeliveryResponse:
    return DeliveryResponse(
        id=delivery.id,
        reference=delivery.reference,
        order_id=delivery.order_id,
        status=delivery.status,
        lines=[
            DeliveryLineResponse(
                id=line.id, location_code=line.location_code,
                component_code=line.component_code,
                quantity=line.quantity,
                sort_order=line.sort_order,
            )
            for line in delivery.lines
        ],
        confirmed_at=delivery.confirmed_at,
        created_at=delivery.created_at,
    )


@router.get("/stock", response_model=list[StockLevelResponse])
def read_stock(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [
        StockLevelResponse(
            component_code=row["component_code"],
            location_code=row["location_code"],
            on_hand=row["on_hand"],
        )
        for row in inventory_service.stock_levels(db, user)
    ]


@router.post("/stock/operations", response_model=StockOperationResponse)
def create_stock_operation(
    payload: StockOperationCreate,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    operation, replayed = inventory_service.create_operation(
        db,
        user,
        payload.operation_type,
        [line.model_dump() for line in payload.lines],
        payload.note,
        payload.source_order_id,
        _key(idempotency_key),
    )
    response.status_code = 200 if replayed else 201
    return _operation_payload(operation)


@router.get("/stock/operations/{operation_id}", response_model=StockOperationResponse)
def read_stock_operation(
    operation_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _operation_payload(inventory_service.get_operation(db, user, operation_id))


@router.post("/stock/operations/{operation_id}/ready", response_model=StockOperationResponse)
def ready_stock_operation(
    operation_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _operation_payload(inventory_service.mark_ready(db, user, operation_id))


@router.post("/stock/operations/{operation_id}/validate", response_model=StockOperationResponse)
def validate_stock_operation(
    operation_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _operation_payload(inventory_service.validate_operation(db, user, operation_id))


@router.post("/stock/operations/{operation_id}/cancel", response_model=StockOperationResponse)
def cancel_stock_operation(
    operation_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _operation_payload(inventory_service.cancel_operation(db, user, operation_id))


@router.post("/stock/reservations", response_model=list[ReservationResponse])
def create_reservations(
    payload: ReservationCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from app.models.workflow import SalesOrder

    if user.role_code not in {"sales", "admin", "warehouse_staff", "warehouse_manager"}:
        raise AppError(403, "forbidden", "You cannot create reservations.")
    order = db.get(SalesOrder, payload.order_id)
    if order is None:
        raise AppError(404, "not_found", "Order not found.")
    rows = inventory_service.reserve_for_order(db, order)
    return [
        ReservationResponse(
            id=row.id,
            order_id=row.order_id,
            component_code=row.component_code,
            quantity=row.quantity,
            status=row.status,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/stock/reservations", response_model=list[ReservationResponse])
def read_reservations(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    order_id: UUID | None = Query(default=None),
):
    return [
        ReservationResponse(
            id=row.id,
            order_id=row.order_id,
            component_code=row.component_code,
            quantity=row.quantity,
            status=row.status,
            created_at=row.created_at,
        )
        for row in inventory_service.list_reservations(db, user, order_id)
    ]


@router.post("/serials/scan", response_model=SerialResponse)
def scan_serial(
    payload: SerialScanCreate,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = inventory_service.scan_serial(
        db, user, payload.serial_number, payload.component_code, payload.operation_id
    )
    response.status_code = 201
    return SerialResponse(
        id=row.id,
        serial_number=row.serial_number,
        component_code=row.component_code,
        status=row.status,
        location_code=row.location_code,
        order_id=row.order_id,
        operation_id=row.operation_id,
        created_at=row.created_at,
    )


@router.post("/serials/{serial_id}/assign", response_model=SerialResponse)
def assign_serial(
    serial_id: UUID,
    payload: SerialAssign,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = fulfillment_service.assign_serial(db, user, serial_id, payload.order_id)
    return SerialResponse(
        id=row.id,
        serial_number=row.serial_number,
        component_code=row.component_code,
        status=row.status,
        location_code=row.location_code,
        order_id=row.order_id,
        operation_id=row.operation_id,
        created_at=row.created_at,
    )


@router.post("/replenishment/requests", response_model=ReplenishmentResponse)
def request_replenishment(
    payload: ReplenishmentCreate,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = inventory_service.request_replenishment(
        db, user, payload.component_code, payload.location_code, payload.quantity
    )
    response.status_code = 201
    return ReplenishmentResponse(
        id=row.id,
        reference=row.reference,
        component_code=row.component_code,
        location_code=row.location_code,
        quantity=row.quantity,
        status=row.status,
        requested_by_user_id=row.requested_by_user_id,
        decided_by_user_id=row.decided_by_user_id,
        created_at=row.created_at,
    )


@router.post("/replenishment/requests/{request_id}/decision", response_model=ReplenishmentResponse)
def decide_replenishment(
    request_id: UUID,
    payload: ReplenishmentDecision,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = inventory_service.decide_replenishment(db, user, request_id, payload.decision)
    return ReplenishmentResponse(
        id=row.id,
        reference=row.reference,
        component_code=row.component_code,
        location_code=row.location_code,
        quantity=row.quantity,
        status=row.status,
        requested_by_user_id=row.requested_by_user_id,
        decided_by_user_id=row.decided_by_user_id,
        created_at=row.created_at,
    )


@router.post("/deliveries", response_model=DeliveryResponse)
def create_delivery(
    payload: DeliveryCreate,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    delivery, replayed = fulfillment_service.create_delivery(
        db, user, payload.order_id, _key(idempotency_key), [line.model_dump() for line in payload.lines] if payload.lines is not None else None
    )
    response.status_code = 200 if replayed else 201
    return _delivery_payload(delivery)


@router.get("/deliveries", response_model=list[DeliveryResponse])
def list_deliveries(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [_delivery_payload(row) for row in fulfillment_service.list_deliveries(db, user)]


@router.get("/deliveries/{delivery_id}", response_model=DeliveryResponse)
def read_delivery(
    delivery_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _delivery_payload(fulfillment_service.get_delivery(db, user, delivery_id))


@router.post("/deliveries/{delivery_id}/transit", response_model=DeliveryResponse)
def delivery_in_transit(
    delivery_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _delivery_payload(fulfillment_service.transition(db, user, delivery_id, "in_transit"))


@router.post("/deliveries/{delivery_id}/deliver", response_model=DeliveryResponse)
def delivery_delivered(
    delivery_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _delivery_payload(fulfillment_service.transition(db, user, delivery_id, "delivered"))


@router.post("/deliveries/{delivery_id}/confirm", response_model=DeliveryResponse)
def delivery_confirm(
    delivery_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _delivery_payload(fulfillment_service.transition(db, user, delivery_id, "confirmed"))


@router.post("/deliveries/{delivery_id}/cancel", response_model=DeliveryResponse)
def delivery_cancel(
    delivery_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _delivery_payload(fulfillment_service.transition(db, user, delivery_id, "cancelled"))
