from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.session import get_db
from app.models.identity import User
from app.repositories.queries import list_packages
from app.schemas import PackageResponse
from app.schemas.workflow import TemplateLineResponse, TemplateVersionResponse
from app.services import quotation_service

router = APIRouter(prefix="/packages", tags=["packages"])


@router.get("", response_model=list[PackageResponse])
def read_packages(
    _: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> list[PackageResponse]:
    return [
        PackageResponse(
            id=package.id,
            code=package.code,
            name=package.name,
            category=package.category,
            grid_type=package.grid_type,
            capacity_w=package.capacity_w,
            description=package.description,
            is_active=package.is_active,
        )
        for package in list_packages(db)
    ]


@router.get("/{package_code}/versions/current", response_model=TemplateVersionResponse)
def read_current_version(
    package_code: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> TemplateVersionResponse:
    return _version_response(db, user, package_code, None)


@router.get("/{package_code}/versions/{version_number}", response_model=TemplateVersionResponse)
def read_version(
    package_code: str,
    version_number: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> TemplateVersionResponse:
    return _version_response(db, user, package_code, version_number)


def _version_response(
    db: Session, user: User, package_code: str, version_number: int | None
) -> TemplateVersionResponse:
    package, version = quotation_service.template_version(db, user, package_code, version_number)
    names = quotation_service.component_map(db)
    return TemplateVersionResponse(
        id=version.id,
        package_code=package.code,
        version_number=version.version_number,
        is_current=version.is_current,
        note=version.note,
        lines=[
            TemplateLineResponse(
                component_code=line.component_code,
                component_name=names[line.component_code].name,
                line_kind=line.line_kind,
                quantity=line.quantity,
                unit=names[line.component_code].unit,
                unit_cost_minor=line.unit_cost_minor,
                unit_price_minor=line.unit_price_minor,
                sort_order=line.sort_order,
            )
            for line in version.lines
        ],
    )
