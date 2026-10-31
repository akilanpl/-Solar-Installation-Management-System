from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.identity import User
from app.schemas import EmployeeCreate, EmployeeResponse
from app.services import auth_service

router = APIRouter(prefix="/admin", tags=["admin"])


def _employee_response(user: User, profile) -> EmployeeResponse:
    return EmployeeResponse(
        id=user.id,
        email=user.email,
        full_name=profile.full_name,
        phone=profile.phone,
        employee_code=profile.employee_code,
        role=user.role_code,
        is_active=user.is_active,
        email_verified=user.email_verified_at is not None,
    )


@router.get("/employees", response_model=list[EmployeeResponse])
def read_employees(
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> list[EmployeeResponse]:
    return [_employee_response(user, profile) for user, profile in auth_service.list_staff(db)]


@router.post("/employees", response_model=EmployeeResponse, status_code=201)
def create_employee(
    payload: EmployeeCreate,
    actor: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> EmployeeResponse:
    user, profile = auth_service.provision_employee(db, actor, payload)
    return _employee_response(user, profile)
