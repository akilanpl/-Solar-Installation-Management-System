"""Location-specific fulfilment and auditable operational records."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.api.v1.warehouse import _key
from app.db.session import get_db
from app.models.identity import User
from app.models.operations import GoodsReturn, StockAllocation, SupplierOrder
from app.models.phase3 import StockReservation
from app.schemas.phase3 import DeliveryPickLine
from app.services import location_allocation, operational_records

router = APIRouter(tags=["operational-custody"])


class AllocationLine(DeliveryPickLine):
    quantity: int = Field(ge=0, le=100000)


class AllocationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    order_id: UUID
    lines: list[AllocationLine] = Field(min_length=1, max_length=200)


class AllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    reservation_id: UUID
    location_code: str
    quantity: int
    picked_quantity: int


@router.post("/stock/allocations", response_model=list[AllocationResponse])
def allocate(
    payload: AllocationCreate, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return location_allocation.allocate(
        db, user, payload.order_id, [line.model_dump() for line in payload.lines]
    )


@router.get("/stock/allocations", response_model=list[AllocationResponse])
def allocations(order_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    operational_records.permit(user, operational_records.WAREHOUSE)
    return list(
        db.scalars(
            select(StockAllocation)
            .join(StockReservation, StockAllocation.reservation_id == StockReservation.id)
            .where(StockReservation.order_id == order_id)
        )
    )


class ReturnCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    delivery_line_id: UUID
    quantity: int = Field(gt=0, le=100000)
    reason: str = Field(min_length=5, max_length=1000)
    serial_id: UUID | None = None


class ReturnInspection(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    disposition: Literal["restock", "damaged"]
    note: str = Field(min_length=5, max_length=1000)


class ReturnResponse(ReturnCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    disposition: str | None
    inspection_note: str | None
    operation_id: UUID | None
    inspected_at: datetime | None


@router.post("/stock/returns", response_model=ReturnResponse)
def authorize_return(
    payload: ReturnCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    return operational_records.authorize_return(db, user, payload.model_dump(), _key(key))


@router.get("/stock/returns", response_model=list[ReturnResponse])
def returns(user: User = Depends(current_user), db: Session = Depends(get_db)):
    operational_records.permit(user, operational_records.WAREHOUSE)
    return list(db.scalars(select(GoodsReturn).order_by(GoodsReturn.created_at.desc()).limit(200)))


@router.post("/stock/returns/{return_id}/inspection", response_model=ReturnResponse)
def inspect_return(
    return_id: UUID,
    payload: ReturnInspection,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return operational_records.inspect_return(
        db, user, return_id, payload.disposition, payload.note
    )


class SupplierOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    replenishment_request_id: UUID
    supplier_name: str = Field(min_length=2, max_length=160)
    supplier_reference: str = Field(min_length=2, max_length=160)


class SupplierOrderResponse(SupplierOrderCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    received_operation_id: UUID | None


class SupplierReceiptLink(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    operation_id: UUID


@router.post("/procurement/orders", response_model=SupplierOrderResponse)
def supplier_order(
    payload: SupplierOrderCreate, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return operational_records.supplier_order(
        db,
        user,
        payload.replenishment_request_id,
        payload.supplier_name,
        payload.supplier_reference,
    )


@router.get("/procurement/orders", response_model=list[SupplierOrderResponse])
def supplier_orders(user: User = Depends(current_user), db: Session = Depends(get_db)):
    operational_records.permit(user, operational_records.WAREHOUSE)
    return list(
        db.scalars(select(SupplierOrder).order_by(SupplierOrder.created_at.desc()).limit(200))
    )


@router.post("/procurement/orders/{order_id}/receipt", response_model=SupplierOrderResponse)
def supplier_receipt(
    order_id: UUID,
    payload: SupplierReceiptLink,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return operational_records.link_supplier_receipt(db, user, order_id, payload.operation_id)
