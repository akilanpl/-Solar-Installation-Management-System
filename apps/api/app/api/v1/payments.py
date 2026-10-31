from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_settings
from app.core.config import Settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models.identity import User
from app.models.workflow import PaymentIntent
from app.schemas import parse_idempotency_key
from app.schemas.workflow import (
    CashReceiptCreate,
    PaymentIntentCreate,
    PaymentIntentResponse,
    PaymentRequirementResponse,
    SandboxOutcome,
)
from app.services import payment_service

router = APIRouter(tags=["payments"])


def _key(value: str | None) -> str:
    try:
        return parse_idempotency_key(value)
    except ValueError as exc:
        raise AppError(400, "idempotency_key_required", str(exc)) from exc


def intent_response(intent: PaymentIntent) -> PaymentIntentResponse:
    return PaymentIntentResponse(
        id=intent.id,
        quotation_id=intent.quotation_id,
        amount_minor=intent.amount_minor,
        currency_code=intent.currency_code,
        method=intent.method,
        status=intent.status,
        is_test_only=intent.is_test_only,
        provider=intent.provider,
        transaction_reference=intent.transaction_reference,
        created_at=intent.created_at,
    )


@router.get(
    "/quotations/{quotation_id}/payment-requirement",
    response_model=PaymentRequirementResponse,
)
def read_requirement(
    quotation_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> PaymentRequirementResponse:
    requirement, verified = payment_service.get_requirement(db, user, quotation_id)
    return PaymentRequirementResponse(
        quotation_id=requirement.quotation_id,
        currency_code=requirement.currency_code,
        minimum_advance_minor=requirement.minimum_advance_minor,
        full_amount_minor=requirement.full_amount_minor,
        advance_percent=requirement.advance_percent,
        verified_minor=verified,
        outstanding_minor=max(0, requirement.full_amount_minor - verified),
    )


@router.post("/payments/intents", response_model=PaymentIntentResponse)
def create_intent(
    payload: PaymentIntentCreate,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> PaymentIntentResponse:
    intent, replayed = payment_service.create_sandbox_intent(
        db, settings, user, payload, _key(idempotency_key)
    )
    response.status_code = 200 if replayed else 201
    return intent_response(intent)


@router.post("/payments/intents/{intent_id}/sandbox-outcome", response_model=PaymentIntentResponse)
def sandbox_outcome(
    intent_id: UUID,
    payload: SandboxOutcome,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PaymentIntentResponse:
    return intent_response(
        payment_service.apply_sandbox_outcome(db, settings, user, intent_id, payload)
    )


@router.post("/payments/cash-receipts", response_model=PaymentIntentResponse)
def cash_receipt(
    payload: CashReceiptCreate,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> PaymentIntentResponse:
    intent, replayed = payment_service.record_cash_receipt(
        db, user, payload, _key(idempotency_key)
    )
    response.status_code = 200 if replayed else 201
    return intent_response(intent)


@router.get("/payments/{intent_id}", response_model=PaymentIntentResponse)
def read_payment(
    intent_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> PaymentIntentResponse:
    return intent_response(payment_service.get_intent(db, user, intent_id))
