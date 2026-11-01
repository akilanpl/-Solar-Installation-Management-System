"""Minimal site/equipment context after authorizing the actual work record."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.enquiry import CustomerSite, Enquiry
from app.models.identity import User
from app.models.phase3 import EquipmentSerial
from app.models.workflow import SalesOrder
from app.schemas import SiteResponse
from app.services import installation_service, survey_service

router = APIRouter(tags=["assigned-work-context"])


class WorkUnit(BaseModel):
    id: UUID
    serial_number: str
    component_code: str
    status: str


class AssignedWorkContext(BaseModel):
    enquiry_reference: str
    order_reference: str | None
    contact_name: str
    site: SiteResponse
    equipment: list[WorkUnit]


def _context(db, enquiry_id, order=None):
    enquiry = db.get(Enquiry, enquiry_id)
    site = db.get(CustomerSite, enquiry.site_id) if enquiry else None
    if enquiry is None or site is None:
        raise AppError(404, "not_found", "Authorized work context is unavailable.")
    units = []
    if order:
        units = [
            WorkUnit(
                id=row.id,
                serial_number=row.serial_number,
                component_code=row.component_code,
                status=row.status,
            )
            for row in db.scalars(
                select(EquipmentSerial)
                .where(EquipmentSerial.order_id == order.id)
                .order_by(EquipmentSerial.serial_number)
            )
        ]
    return AssignedWorkContext(
        enquiry_reference=enquiry.reference,
        order_reference=order.reference if order else None,
        contact_name=enquiry.contact_name,
        site=SiteResponse(
            id=site.id,
            line1=site.line1,
            line2=site.line2,
            city=site.city,
            state=site.state,
            postal_code=site.postal_code,
            country_code=site.country_code,
        ),
        equipment=units,
    )


@router.get("/surveys/{survey_id}/site-context", response_model=AssignedWorkContext)
def survey_context(
    survey_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    survey = survey_service.get_survey(db, user, survey_id)
    return _context(db, survey.enquiry_id)


@router.get("/jobs/{job_id}/site-context", response_model=AssignedWorkContext)
def job_context(
    job_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    job = installation_service.get_job(db, user, job_id)
    order = db.get(SalesOrder, job.order_id)
    if order is None:
        raise AppError(404, "not_found", "Order context is unavailable.")
    return _context(db, order.enquiry_id, order)
