"""Active technicians for survey assignment.

Sales cannot read the admin employee directory. This list is only the
fields needed to choose an assignee.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.identity import User
from app.repositories.queries import list_employees
from app.schemas import TechnicianOption

router = APIRouter(prefix="/technicians", tags=["technicians"])


@router.get("", response_model=list[TechnicianOption])
def list_technicians(
    _: User = Depends(require_role("sales", "admin")),
    db: Session = Depends(get_db),
) -> list[TechnicianOption]:
    return [
        TechnicianOption(
            id=user.id,
            full_name=profile.full_name,
            employee_code=profile.employee_code,
        )
        for user, profile in list_employees(db)
        if user.role_code == "technician" and user.is_active
    ]
