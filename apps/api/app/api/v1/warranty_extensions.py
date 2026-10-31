"""Phase 4E warranty extension routes on the Phase 4B serial policy model.

Approval, rejection review and payment verification require a fresh
step-up grant (``X-Strong-Auth`` header). Activation never happens from a
browser-only success event: a paid extension waits in ``pending_payment``
until support records a verified payment reference.
"""

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_limiter, get_settings
from app.api.v1.auth_extra import require_strong_auth
from app.core.config import Settings
from app.core.rate_limit import RateLimiter
from app.db.session import get_db as get_db_dep
from app.models.identity import User
from app.schemas import (
    EligibilityResponse,
    ExtensionDecisionRequest,
    ExtensionOfferResponse,
    ExtensionPaymentRequest,
    ExtensionRequestCreate,
    ExtensionResponse,
    ExtensionTermsCreate,
    ExtensionTermsResponse,
)
from app.services import warranty_extension_service

router = APIRouter(tags=["warranty-extensions-4e"])


def _terms_response(row) -> ExtensionTermsResponse:
    return ExtensionTermsResponse(
        id=row.id, policy_id=row.policy_id, version=row.version,
        extension_days=row.extension_days, price_minor=row.price_minor,
        currency=row.currency, window_days=row.window_days,
        eligible_categories=list(row.eligible_categories),
        max_extensions=row.max_extensions, requires_approval=row.requires_approval,
        is_active=row.is_active, created_at=row.created_at,
    )


def _offer_response(row) -> ExtensionOfferResponse:
    return ExtensionOfferResponse(
        id=row.id, coverage_id=row.coverage_id, version=row.version,
        extension_days=row.extension_days, price_minor=row.price_minor,
        currency=row.currency, payment_required=row.payment_required,
        status=row.status, expires_at=row.expires_at,
    )


def _extension_response(row) -> ExtensionResponse:
    return ExtensionResponse(
        id=row.id, offer_id=row.offer_id, offer_version=row.offer_version,
        serial_id=row.serial_id, coverage_id=row.coverage_id, status=row.status,
        extension_days=row.extension_days, price_minor=row.price_minor,
        currency=row.currency, original_ends_at=row.original_ends_at,
        new_ends_at=row.new_ends_at, payment_reference=row.payment_reference,
        decision_note=row.decision_note, created_at=row.created_at,
    )


@router.get("/warranty/extensions/eligibility", response_model=EligibilityResponse)
def check_eligibility(
    serial_number: str = Query(min_length=1, max_length=64),
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep),
) -> EligibilityResponse:
    return EligibilityResponse(
        **warranty_extension_service.evaluate_eligibility(db, user, serial_number)
    )


@router.post("/warranty/extensions/terms", response_model=ExtensionTermsResponse,
             status_code=201)
def create_terms(
    payload: ExtensionTermsCreate,
    request: Request,
    user: User = Depends(require_strong_auth),
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> ExtensionTermsResponse:
    limiter.check(
        f"extension-terms:{user.id}", limit=10,
        window_seconds=settings.rate_limit_window_seconds,
    )
    return _terms_response(
        warranty_extension_service.create_terms(
            db, user, policy_id=payload.policy_id,
            extension_days=payload.extension_days, price_minor=payload.price_minor,
            currency=payload.currency, window_days=payload.window_days,
            eligible_categories=payload.eligible_categories,
            max_extensions=payload.max_extensions,
            requires_approval=payload.requires_approval,
        )
    )


@router.get("/warranty/extensions/terms", response_model=list[ExtensionTermsResponse])
def list_terms(
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep),
) -> list[ExtensionTermsResponse]:
    return [_terms_response(row) for row in warranty_extension_service.list_terms(db, user)]


@router.post("/warranty/extensions/offers", response_model=ExtensionOfferResponse,
             status_code=201)
def issue_offer(
    coverage_id: uuid.UUID = Query(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> ExtensionOfferResponse:
    limiter.check(
        f"extension-offer:{user.id}", limit=20,
        window_seconds=settings.rate_limit_window_seconds,
    )
    return _offer_response(
        warranty_extension_service.ensure_offer(db, user, coverage_id=coverage_id)
    )


@router.post("/warranty/extensions/requests", response_model=ExtensionResponse, status_code=201)
def request_extension(
    payload: ExtensionRequestCreate,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> ExtensionResponse:
    limiter.check(
        f"extension-request:{user.id}", limit=10,
        window_seconds=settings.rate_limit_window_seconds,
    )
    return _extension_response(
        warranty_extension_service.request_extension(
            db, user, coverage_id=payload.coverage_id,
            idempotency_key=payload.idempotency_key,
        )
    )


@router.get("/warranty/extensions/requests", response_model=list[ExtensionResponse])
def list_extensions(
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep),
) -> list[ExtensionResponse]:
    return [
        _extension_response(row)
        for row in warranty_extension_service.list_extensions(db, user)
    ]


@router.get("/warranty/extensions/requests/{extension_id}", response_model=ExtensionResponse)
def get_extension(
    extension_id: uuid.UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep),
) -> ExtensionResponse:
    return _extension_response(
        warranty_extension_service.get_extension(db, user, extension_id)
    )


@router.post("/warranty/extensions/requests/{extension_id}/approve",
             response_model=ExtensionResponse)
def approve_extension(
    extension_id: uuid.UUID,
    payload: ExtensionDecisionRequest,
    request: Request,
    user: User = Depends(require_strong_auth),
    db: Session = Depends(get_db_dep),
) -> ExtensionResponse:
    return _extension_response(
        warranty_extension_service.approve_extension(
            db, user, extension_id=extension_id, note=payload.note
        )
    )


@router.post("/warranty/extensions/requests/{extension_id}/reject",
             response_model=ExtensionResponse)
def reject_extension(
    extension_id: uuid.UUID,
    payload: ExtensionDecisionRequest,
    request: Request,
    user: User = Depends(require_strong_auth),
    db: Session = Depends(get_db_dep),
) -> ExtensionResponse:
    if not payload.note:
        from app.core.errors import AppError

        raise AppError(422, "validation_error", "A rejection needs a short note.")
    return _extension_response(
        warranty_extension_service.reject_extension(
            db, user, extension_id=extension_id, note=payload.note
        )
    )


@router.post("/warranty/extensions/requests/{extension_id}/cancel",
             response_model=ExtensionResponse)
def cancel_extension(
    extension_id: uuid.UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep),
) -> ExtensionResponse:
    return _extension_response(
        warranty_extension_service.cancel_extension(db, user, extension_id=extension_id)
    )


@router.post("/warranty/extensions/requests/{extension_id}/activate",
             response_model=ExtensionResponse)
def record_payment_and_activate(
    extension_id: uuid.UUID,
    payload: ExtensionPaymentRequest,
    request: Request,
    user: User = Depends(require_strong_auth),
    db: Session = Depends(get_db_dep),
) -> ExtensionResponse:
    return _extension_response(
        warranty_extension_service.record_payment_and_activate(
            db, user, extension_id=extension_id, payment_reference=payload.payment_reference
        )
    )
