"""Payment requirements and verification.

A sandbox intent is test-only. Posting a succeeded sandbox outcome is the
development adapter; it is not a bank confirmation and it is refused in
production. A customer-supplied reference never verifies a payment by itself.
Cash becomes verified only when sales or admin records a receipt.
"""

import json
import uuid
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import utcnow
from app.models.enquiry import Enquiry
from app.models.identity import User
from app.models.workflow import PaymentAttempt, PaymentIntent, PaymentRequirement, Quotation
from app.repositories.queries import add_audit
from app.schemas.workflow import CashReceiptCreate, PaymentIntentCreate, SandboxOutcome

SALES = {"sales", "admin"}


def _hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(raw.encode("utf-8")).hexdigest()


def requirement_for(db: Session, quotation_id: uuid.UUID) -> PaymentRequirement | None:
    return db.scalar(
        select(PaymentRequirement).where(PaymentRequirement.quotation_id == quotation_id)
    )


def quotation_family_ids(db: Session, quotation_id: uuid.UUID) -> list[uuid.UUID]:
    """This quotation and the revisions it replaced, each id once.

    Verified money stays on the quotation it was paid against. The current
    quotation's balance includes that history so a revision does not ask for
    the same money again and does not drop it.
    """
    found: list[uuid.UUID] = []
    seen: set[uuid.UUID] = set()
    current: uuid.UUID | None = quotation_id
    while current is not None and current not in seen:
        seen.add(current)
        found.append(current)
        current = db.scalar(
            select(Quotation.supersedes_quotation_id).where(Quotation.id == current)
        )
    return found


def verified_total(db: Session, quotation_id: uuid.UUID) -> int:
    family = quotation_family_ids(db, quotation_id)
    value = db.scalar(
        select(func.coalesce(func.sum(PaymentIntent.amount_minor), 0)).where(
            PaymentIntent.quotation_id.in_(family),
            PaymentIntent.status == "verified",
        )
    )
    from app.models.provider import ProviderPaymentOrder

    refunded = db.scalar(
        select(func.coalesce(func.sum(ProviderPaymentOrder.refunded_minor), 0))
        .join(PaymentIntent, ProviderPaymentOrder.intent_id == PaymentIntent.id)
        .where(PaymentIntent.quotation_id.in_(family), PaymentIntent.status == "verified")
    )
    return max(0, int(value or 0) - int(refunded or 0))


def _lock_enquiry(db: Session, enquiry_id: uuid.UUID) -> None:
    locked = db.scalar(select(Enquiry.id).where(Enquiry.id == enquiry_id).with_for_update())
    if locked is None:
        raise AppError(404, "not_found", "Enquiry not found.")


def get_requirement(
    db: Session, user: User, quotation_id: uuid.UUID
) -> tuple[PaymentRequirement, int]:
    quotation = db.get(Quotation, quotation_id)
    if quotation is None:
        raise AppError(404, "not_found", "Quotation not found.")
    if user.role_code == "customer" and quotation.customer_user_id != user.id:
        raise AppError(404, "not_found", "Quotation not found.")
    if user.role_code not in SALES | {"customer"}:
        raise AppError(403, "forbidden", "You cannot view this payment requirement.")
    requirement = requirement_for(db, quotation.id)
    if requirement is None:
        raise AppError(404, "not_found", "Payment requirement not found.")
    return requirement, verified_total(db, quotation.id)


def create_sandbox_intent(
    db: Session,
    settings: Settings,
    user: User,
    payload: PaymentIntentCreate,
    idempotency_key: str,
) -> tuple[PaymentIntent, bool]:
    if settings.app_env == "production":
        raise AppError(403, "sandbox_disabled", "Sandbox payments are disabled in production.")
    quotation = db.get(Quotation, payload.quotation_id)
    if quotation is None:
        raise AppError(404, "not_found", "Quotation not found.")
    if user.role_code == "customer" and quotation.customer_user_id != user.id:
        raise AppError(404, "not_found", "Quotation not found.")
    if user.role_code not in SALES | {"customer"}:
        raise AppError(403, "forbidden", "You cannot start a payment.")
    if quotation.status not in {"issued", "accepted"}:
        raise AppError(409, "invalid_transition", "This quotation cannot be paid.")
    digest = _hash(
        {
            "quotation_id": str(payload.quotation_id),
            "amount_minor": payload.amount_minor,
            "method": "sandbox",
        }
    )
    existing = db.scalar(
        select(PaymentIntent).where(
            PaymentIntent.customer_user_id == quotation.customer_user_id,
            PaymentIntent.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.request_hash != digest:
            raise AppError(
                409,
                "idempotency_conflict",
                "This Idempotency-Key was already used for a different payment.",
            )
        return existing, True
    _lock_enquiry(db, quotation.enquiry_id)
    _guard_amount(db, quotation, payload.amount_minor)
    intent = PaymentIntent(
        quotation_id=quotation.id,
        customer_user_id=quotation.customer_user_id,
        amount_minor=payload.amount_minor,
        currency_code=quotation.currency_code,
        method="sandbox",
        status="pending",
        is_test_only=True,
        provider="sandbox",
        idempotency_key=idempotency_key,
        request_hash=digest,
    )
    db.add(intent)
    db.flush()
    db.refresh(intent)
    db.add(
        PaymentAttempt(
            intent_id=intent.id,
            actor_user_id=user.id,
            outcome="created",
            detail={"test_only": True, "provider": "sandbox"},
        )
    )
    add_audit(
        db,
        actor_user_id=user.id,
        action="payment.sandbox_intent_created",
        entity_type="payment_intent",
        entity_id=intent.id,
        metadata={"test_only": True, "amount_minor": payload.amount_minor},
    )
    db.flush()
    return intent, False


def apply_sandbox_outcome(
    db: Session,
    settings: Settings,
    user: User,
    intent_id: uuid.UUID,
    payload: SandboxOutcome,
) -> PaymentIntent:
    if settings.app_env == "production":
        raise AppError(403, "sandbox_disabled", "Sandbox payments are disabled in production.")
    located = db.get(PaymentIntent, intent_id)
    if located is None:
        raise AppError(404, "not_found", "Payment not found.")
    quotation = db.get(Quotation, located.quotation_id)
    if quotation is None:
        raise AppError(404, "not_found", "Quotation not found.")
    _lock_enquiry(db, quotation.enquiry_id)
    intent = db.scalar(select(PaymentIntent).where(PaymentIntent.id == intent_id).with_for_update())
    if intent is None:
        raise AppError(404, "not_found", "Payment not found.")
    if user.role_code == "customer" and intent.customer_user_id != user.id:
        raise AppError(404, "not_found", "Payment not found.")
    if user.role_code not in SALES | {"customer"}:
        raise AppError(403, "forbidden", "You cannot update this payment.")
    if intent.method != "sandbox" or not intent.is_test_only:
        raise AppError(409, "invalid_transition", "This payment is not a sandbox intent.")
    target = {"succeeded": "verified", "failed": "failed", "unknown": "unresolved"}[payload.outcome]
    if intent.status == target:
        return intent
    if intent.status in {"verified", "failed", "unresolved"}:
        raise AppError(409, "invalid_transition", "This sandbox payment already has an outcome.")
    if intent.status not in {"pending", "processing"}:
        raise AppError(409, "invalid_transition", "This payment cannot be updated.")
    intent.status = "processing"
    intent.updated_at = utcnow()
    if target == "verified":
        quotation = db.get(Quotation, intent.quotation_id)
        if quotation is None:
            raise AppError(404, "not_found", "Quotation not found.")
        _guard_amount(db, quotation, intent.amount_minor)
        intent.transaction_reference = f"SANDBOX-{intent.id.hex[:12]}"
    intent.status = target
    db.add(
        PaymentAttempt(
            intent_id=intent.id,
            actor_user_id=user.id,
            outcome=payload.outcome,
            detail={"test_only": True, "provider": "sandbox", "status": target},
        )
    )
    add_audit(
        db,
        actor_user_id=user.id,
        action="payment.sandbox_outcome",
        entity_type="payment_intent",
        entity_id=intent.id,
        metadata={"test_only": True, "status": target},
    )
    db.flush()
    return intent


def record_cash_receipt(
    db: Session,
    user: User,
    payload: CashReceiptCreate,
    idempotency_key: str,
) -> tuple[PaymentIntent, bool]:
    if user.role_code not in SALES:
        raise AppError(403, "forbidden", "Only sales can record a cash receipt.")
    quotation = db.get(Quotation, payload.quotation_id)
    if quotation is None:
        raise AppError(404, "not_found", "Quotation not found.")
    _lock_enquiry(db, quotation.enquiry_id)
    quotation = db.scalar(
        select(Quotation).where(Quotation.id == payload.quotation_id).with_for_update()
    )
    if quotation is None:
        raise AppError(404, "not_found", "Quotation not found.")
    if quotation.status not in {"issued", "accepted"}:
        raise AppError(409, "invalid_transition", "This quotation cannot be paid.")
    digest = _hash(
        {
            "quotation_id": str(payload.quotation_id),
            "amount_minor": payload.amount_minor,
            "receipt_reference": payload.receipt_reference,
            "method": "cash",
        }
    )
    existing = db.scalar(
        select(PaymentIntent).where(
            PaymentIntent.customer_user_id == quotation.customer_user_id,
            PaymentIntent.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.request_hash != digest:
            raise AppError(
                409,
                "idempotency_conflict",
                "This Idempotency-Key was already used for a different payment.",
            )
        return existing, True
    duplicate_receipt = db.scalar(
        select(PaymentIntent.id).where(
            PaymentIntent.quotation_id == quotation.id,
            PaymentIntent.transaction_reference == payload.receipt_reference,
        )
    )
    if duplicate_receipt is not None:
        raise AppError(409, "duplicate_receipt", "This receipt reference is already recorded.")
    _guard_amount(db, quotation, payload.amount_minor)
    intent = PaymentIntent(
        quotation_id=quotation.id,
        customer_user_id=quotation.customer_user_id,
        amount_minor=payload.amount_minor,
        currency_code=quotation.currency_code,
        method="cash",
        status="verified",
        is_test_only=False,
        provider="cash_receipt",
        transaction_reference=payload.receipt_reference,
        idempotency_key=idempotency_key,
        request_hash=digest,
    )
    db.add(intent)
    db.flush()
    db.refresh(intent)
    db.add(
        PaymentAttempt(
            intent_id=intent.id,
            actor_user_id=user.id,
            outcome="cash_recorded",
            detail={"receipt_reference": payload.receipt_reference, "test_only": False},
        )
    )
    add_audit(
        db,
        actor_user_id=user.id,
        action="payment.cash_recorded",
        entity_type="payment_intent",
        entity_id=intent.id,
        metadata={"amount_minor": payload.amount_minor, "test_only": False},
    )
    db.flush()
    return intent, False


def get_intent(db: Session, user: User, intent_id: uuid.UUID) -> PaymentIntent:
    intent = db.get(PaymentIntent, intent_id)
    if intent is None:
        raise AppError(404, "not_found", "Payment not found.")
    if user.role_code == "customer" and intent.customer_user_id != user.id:
        raise AppError(404, "not_found", "Payment not found.")
    if user.role_code not in SALES | {"customer"}:
        raise AppError(403, "forbidden", "You cannot view this payment.")
    return intent


def _guard_amount(db: Session, quotation: Quotation, amount_minor: int) -> None:
    requirement = requirement_for(db, quotation.id)
    if requirement is None:
        raise AppError(
            409, "payment_requirement_missing", "This quotation has no payment requirement."
        )
    already = verified_total(db, quotation.id)
    if already + amount_minor > requirement.full_amount_minor:
        raise AppError(
            409,
            "amount_exceeds_balance",
            "The payment is larger than the outstanding quotation total.",
        )


def verified_payments(db: Session, quotation_id: uuid.UUID) -> list[PaymentIntent]:
    family = quotation_family_ids(db, quotation_id)
    return list(
        db.scalars(
            select(PaymentIntent).where(
                PaymentIntent.quotation_id.in_(family),
                PaymentIntent.status == "verified",
            )
        )
    )
