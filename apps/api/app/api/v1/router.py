from fastapi import APIRouter, Depends

from app.api.deps import require_csrf
from app.api.v1 import (
    admin,
    auth,
    auth_extra,
    billing,
    calendar,
    coverage,
    dev,
    enquiries,
    finance,
    health,
    installation,
    intelligence,
    offline,
    operations,
    orders,
    packages,
    payments,
    quotations,
    razorpay,
    replacements,
    surveys,
    tickets,
    warehouse,
    warranty,
    warranty_extensions,
    work_context,
    workspace_reads,
)

api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_csrf)])
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(auth_extra.router)
api_router.include_router(offline.router)
api_router.include_router(warranty_extensions.router)
api_router.include_router(enquiries.router)
api_router.include_router(packages.router)
api_router.include_router(surveys.router)
api_router.include_router(quotations.router)
api_router.include_router(payments.router)
api_router.include_router(razorpay.router)
api_router.include_router(orders.router)
api_router.include_router(warehouse.router)
api_router.include_router(operations.router)
api_router.include_router(workspace_reads.router)
api_router.include_router(work_context.router)
api_router.include_router(installation.router)
api_router.include_router(calendar.router)
api_router.include_router(coverage.router)
api_router.include_router(tickets.router)
api_router.include_router(warranty.router)
api_router.include_router(replacements.router)
api_router.include_router(billing.router)
api_router.include_router(finance.router)
api_router.include_router(admin.router)
api_router.include_router(dev.router)
api_router.include_router(intelligence.router)
