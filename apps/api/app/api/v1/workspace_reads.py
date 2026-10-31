"""Scoped read models needed by the real role workspaces; no mock fallback."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_role
from app.api.v1.warehouse import _operation_payload
from app.db.session import get_db
from app.models.identity import EmployeeProfile, User
from app.models.phase3 import (
    EquipmentSerial,
    ReplenishmentRequest,
    StockOperation,
    StockOperationLine,
    WarehouseLocation,
)
from app.models.workflow import CatalogueComponent
from app.schemas.phase3 import ReplenishmentResponse, SerialResponse, StockOperationResponse

router = APIRouter(tags=["workspace-read-models"])
warehouse = require_role("warehouse_staff", "warehouse_manager", "admin")


class TechnicianChoice(BaseModel):
    id: UUID
    full_name: str
    employee_code: str


class ComponentChoice(BaseModel):
    code: str
    name: str
    unit: str
    requires_serial_tracking: bool


class LocationChoice(BaseModel):
    code: str
    name: str


class WarehouseCatalogue(BaseModel):
    components: list[ComponentChoice]
    locations: list[LocationChoice]


@router.get("/workspace/technicians", response_model=list[TechnicianChoice])
def technicians(_: User = Depends(require_role("sales", "admin")), db: Session = Depends(get_db)):
    rows = db.execute(
        select(User, EmployeeProfile)
        .join(EmployeeProfile, EmployeeProfile.user_id == User.id)
        .where(User.role_code == "technician", User.is_active.is_(True))
        .order_by(EmployeeProfile.employee_code)
    ).all()
    return [
        TechnicianChoice(
            id=user.id, full_name=profile.full_name, employee_code=profile.employee_code
        )
        for user, profile in rows
    ]


@router.get("/workspace/warehouse-catalogue", response_model=WarehouseCatalogue)
def catalogue(_: User = Depends(warehouse), db: Session = Depends(get_db)):
    return WarehouseCatalogue(
        components=[
            ComponentChoice(
                code=r.code,
                name=r.name,
                unit=r.unit,
                requires_serial_tracking=r.requires_serial_tracking,
            )
            for r in db.scalars(select(CatalogueComponent).order_by(CatalogueComponent.code))
        ],
        locations=[
            LocationChoice(code=r.code, name=r.name)
            for r in db.scalars(select(WarehouseLocation).order_by(WarehouseLocation.code))
        ],
    )


@router.get("/stock/operations", response_model=list[StockOperationResponse])
def operations(_: User = Depends(warehouse), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(StockOperation)
        .options(selectinload(StockOperation.lines).selectinload(StockOperationLine.serials))
        .order_by(StockOperation.created_at.desc())
        .limit(200)
    )
    return [_operation_payload(r) for r in rows]


@router.get("/replenishment/requests", response_model=list[ReplenishmentResponse])
def replenishments(_: User = Depends(warehouse), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ReplenishmentRequest).order_by(ReplenishmentRequest.created_at.desc()).limit(200)
    )
    return [
        ReplenishmentResponse(
            id=r.id,
            reference=r.reference,
            component_code=r.component_code,
            location_code=r.location_code,
            quantity=r.quantity,
            status=r.status,
            requested_by_user_id=r.requested_by_user_id,
            decided_by_user_id=r.decided_by_user_id,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/serials", response_model=list[SerialResponse])
def serials(_: User = Depends(warehouse), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(EquipmentSerial).order_by(EquipmentSerial.created_at.desc()).limit(200)
    )
    return [
        SerialResponse(
            id=r.id,
            serial_number=r.serial_number,
            component_code=r.component_code,
            status=r.status,
            location_code=r.location_code,
            order_id=r.order_id,
            operation_id=r.operation_id,
            created_at=r.created_at,
        )
        for r in rows
    ]
