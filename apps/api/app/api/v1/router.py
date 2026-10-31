from fastapi import APIRouter, Depends

from app.api.deps import require_csrf
from app.api.v1 import admin, auth, dev, enquiries, health, packages

api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_csrf)])
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(enquiries.router)
api_router.include_router(packages.router)
api_router.include_router(admin.router)
api_router.include_router(dev.router)
