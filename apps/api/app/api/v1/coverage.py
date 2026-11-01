from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.errors import AppError
from app.core.security import utcnow
from app.db.session import get_db
from app.models.coverage import ProductWarrantyPolicy, SerialWarranty
from app.models.identity import User
from app.models.phase3 import EquipmentSerial
from app.models.workflow import SalesOrder
from app.services import coverage_service

router = APIRouter(tags=["product-warranty"])


class PolicyInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    component_code: str = Field(min_length=2, max_length=32)
    months: int = Field(ge=1, le=600)
    activation_event: Literal["delivery", "installation"]
    terms: str = Field(min_length=10, max_length=4000)


class PolicyResponse(PolicyInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    version: int


@router.post("/warranty-policies", response_model=PolicyResponse, operation_id="create_product_warranty_policy")
def create_policy(
    payload: PolicyInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    return coverage_service.create_policy(db, user, payload)


@router.get("/warranty-policies", response_model=list[PolicyResponse])
def policies(user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    if user.role_code not in {"admin", "sales", "support", "warehouse_manager"}:
        raise AppError(403, "forbidden", "Product policy access denied.")
    return list(
        db.scalars(
            select(ProductWarrantyPolicy)
            .order_by(ProductWarrantyPolicy.created_at.desc())
            .limit(200)
        )
    )


class UnitCoverageResponse(BaseModel):
    id: UUID
    serial_number: str
    component_code: str
    policy: PolicyResponse
    delivery_id: UUID
    starts_at: datetime
    ends_at: datetime
    status: str
    void_reason: str | None


@router.get("/orders/{order_id}/unit-warranties", response_model=list[UnitCoverageResponse])
def unit_warranties(
    order_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    order = db.get(SalesOrder, order_id)
    if order is None or user.role_code == "customer" and order.customer_user_id != user.id:
        raise AppError(404, "not_found", "Order not found.")
    if user.role_code not in {"customer", "sales", "support", "admin", "warehouse_manager"}:
        raise AppError(403, "forbidden", "Coverage access denied.")
    rows = db.execute(
        select(SerialWarranty, EquipmentSerial, ProductWarrantyPolicy)
        .join(EquipmentSerial, SerialWarranty.serial_id == EquipmentSerial.id)
        .join(ProductWarrantyPolicy, SerialWarranty.policy_id == ProductWarrantyPolicy.id)
        .where(SerialWarranty.order_id == order_id)
    ).all()
    return [
        UnitCoverageResponse(
            id=w.id,
            serial_number=s.serial_number,
            component_code=s.component_code,
            policy=PolicyResponse.model_validate(p),
            delivery_id=w.delivery_id,
            starts_at=w.starts_at,
            ends_at=w.ends_at,
            status="expired" if w.status == "active" and w.ends_at <= utcnow() else w.status,
            void_reason=w.void_reason,
        )
        for w, s, p in rows
    ]
