from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.session import get_db
from app.models.identity import User
from app.repositories.queries import list_packages
from app.schemas import PackageResponse

router = APIRouter(prefix="/packages", tags=["packages"])


@router.get("", response_model=list[PackageResponse])
def read_packages(
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
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
