from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.identity import User
from app.models.workflow import SalesOrder
from app.schemas import parse_idempotency_key
from app.schemas.workflow import (
    OrderCreate,
    OrderLineResponse,
    OrderList,
    OrderResponse,
    SchedulingRequestResponse,
    WarehouseLineResponse,
    WarehouseRequestResponse,
)
from app.services import order_service

router = APIRouter(tags=["orders"])


def _key(value: str | None) -> str:
    try:
        return parse_idempotency_key(value)
    except ValueError as exc:
        raise AppError(400, "idempotency_key_required", str(exc)) from exc


def order_response(db: Session, order: SalesOrder) -> OrderResponse:
    warehouse_id, scheduling_id = order_service.handoff_ids(db, order.id)
    return OrderResponse(
        id=order.id,
        reference=order.reference,
        quotation_id=order.quotation_id,
        quotation_version=order.quotation_version,
        customer_user_id=order.customer_user_id,
        site_id=order.site_id,
        package_code=order.package_code,
        template_version_id=order.template_version_id,
        material_total_minor=order.material_total_minor,
        installation_total_minor=order.installation_total_minor,
        discount_minor=order.discount_minor,
        tax_minor=order.tax_minor,
        total_minor=order.total_minor,
        currency_code=order.currency_code,
        payment_verification_state=order.payment_verification_state,
        test_only_payment=order.test_only_payment,
        status=order.status,
        confirmed_at=order.confirmed_at,
        lines=[
            OrderLineResponse(
                component_code=line.component_code,
                description=line.description,
                line_kind=line.line_kind,
                quantity=line.quantity,
                unit=line.unit,
                unit_price_minor=line.unit_price_minor,
                line_total_minor=line.line_total_minor,
                sort_order=line.sort_order,
            )
            for line in order.lines
        ],
        warehouse_request_id=warehouse_id,
        scheduling_request_id=scheduling_id,
    )


@router.post("/orders", response_model=OrderResponse)
def create_order(
    payload: OrderCreate,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> OrderResponse:
    order, replayed = order_service.confirm_order(
        db, user, payload.quotation_id, _key(idempotency_key)
    )
    response.status_code = 200 if replayed else 201
    return order_response(db, order)


@router.get("/orders", response_model=OrderList)
def list_orders(
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> OrderList:
    rows, total = order_service.list_orders(db, user, page=page, page_size=page_size)
    return OrderList(
        items=[order_response(db, row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
def read_order(
    order_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> OrderResponse:
    return order_response(db, order_service.get_order(db, user, order_id))


@router.get("/warehouse/preparation", response_model=list[WarehouseRequestResponse])
def warehouse_queue(
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> list[WarehouseRequestResponse]:
    return [
        WarehouseRequestResponse(
            id=row.id,
            order_id=row.order_id,
            order_reference=order_service.order_reference(db, row.order_id),
            status=row.status,
            lines=[
                WarehouseLineResponse(
                    component_code=line.component_code,
                    description=line.description,
                    quantity=line.quantity,
                    unit=line.unit,
                )
                for line in row.lines
            ],
            created_at=row.created_at,
        )
        for row in order_service.list_warehouse(db, user)
    ]


@router.get("/scheduling/installations", response_model=list[SchedulingRequestResponse])
def scheduling_queue(
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> list[SchedulingRequestResponse]:
    return [
        SchedulingRequestResponse(
            id=row.id,
            order_id=row.order_id,
            order_reference=order_service.order_reference(db, row.order_id),
            customer_user_id=row.customer_user_id,
            site_id=row.site_id,
            work_summary=row.work_summary,
            status=row.status,
            slot_starts_at=row.slot_starts_at,
            created_at=row.created_at,
        )
        for row in order_service.list_scheduling(db, user)
    ]
