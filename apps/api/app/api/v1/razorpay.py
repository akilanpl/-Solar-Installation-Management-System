"""Test-mode provider checkout. The public webhook authenticates raw bytes by HMAC."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_settings
from app.api.v1.payments import _key, intent_response
from app.core.config import Settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models.identity import User
from app.schemas.workflow import PaymentIntentResponse
from app.services import razorpay_service

router = APIRouter(tags=["razorpay-test"])
webhook_router = APIRouter(tags=["razorpay-webhook"])


class ProviderCapability(BaseModel):
    enabled: bool
    mode: str
    reason: str


@router.get("/payments/razorpay/capability", response_model=ProviderCapability)
def capability(_: User = Depends(current_user), settings: Settings = Depends(get_settings)):
    enabled = razorpay_service.configured(settings)
    return ProviderCapability(
        enabled=enabled,
        mode="test",
        reason="Razorpay test checkout configured; actual method availability depends on the provider account."
        if enabled
        else "Test credentials and webhook secret are required. Live/production checkout is blocked.",
    )


class RazorpayOrderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quotation_id: UUID
    amount_minor: int = Field(ge=100, le=100000000)


class RazorpayOrderResponse(BaseModel):
    payment: PaymentIntentResponse
    provider_order_id: str | None
    public_key_id: str
    refunded_minor: int
    unapplied_minor: int


class ReconcileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payment_id: str = Field(pattern=r"^pay_[A-Za-z0-9]+$", max_length=80)
    signature: str = Field(pattern=r"^[0-9a-f]{64}$")


@router.post("/payments/razorpay/orders", response_model=RazorpayOrderResponse)
def create_order(
    payload: RazorpayOrderInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
    settings: Settings = Depends(get_settings),
    key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    intent, order = razorpay_service.create(db, settings, user, payload, _key(key))
    return RazorpayOrderResponse(
        payment=intent_response(intent),
        provider_order_id=order.provider_order_id,
        public_key_id=settings.razorpay_key_id,
        refunded_minor=order.refunded_minor,
        unapplied_minor=order.unapplied_minor,
    )


@router.post("/payments/razorpay/{intent_id}/reconcile", response_model=PaymentIntentResponse)
def reconcile(
    intent_id: UUID,
    payload: ReconcileInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
    settings: Settings = Depends(get_settings),
):
    return intent_response(
        razorpay_service.reconcile(
            db, settings, user, intent_id, payload.payment_id, payload.signature
        )
    )


class ProviderEventResponse(BaseModel):
    event_id: str
    status: str


@webhook_router.post("/payments/razorpay/webhook", response_model=ProviderEventResponse)
async def webhook(
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    settings: Settings = Depends(get_settings),
    signature: str = Header(default="", alias="X-Razorpay-Signature"),
    event_id: str = Header(default="", alias="X-Razorpay-Event-Id"),
):
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 65536:
            raise AppError(413, "webhook_too_large", "Webhook exceeds the permitted size.")
    row = razorpay_service.webhook(db, settings, bytes(raw), signature, event_id)
    return ProviderEventResponse(event_id=row.event_id, status=row.status)
