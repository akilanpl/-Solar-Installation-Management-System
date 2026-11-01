"""Razorpay test adapter: authenticated requests and provider facts only.

Production/live credentials are intentionally blocked. Uncertain order creation
is persisted as unresolved and must not be retried with a new provider order.
Official references are recorded in docs/release/SECURITY_AND_RELIABILITY_REPORT.md.
"""

import hashlib
import hmac
import json
import re

import httpx
from sqlalchemy import select

from app.core.errors import AppError
from app.core.security import utcnow
from app.models.provider import ProviderEvent, ProviderPaymentOrder
from app.models.workflow import PaymentAttempt, PaymentIntent, Quotation
from app.repositories.queries import add_audit
from app.services import payment_service

BASE = "https://api.razorpay.com/v1"


def configured(settings):
    return settings.app_env != "production" and bool(
        settings.razorpay_key_id
        and settings.razorpay_key_id.startswith("rzp_test_")
        and settings.razorpay_key_secret
        and settings.razorpay_webhook_secret
    )


def require_test(settings):
    if not configured(settings):
        raise AppError(
            503,
            "provider_unavailable",
            "Razorpay test credentials/webhook secret are missing, or live/production operation is blocked.",
        )


def provider_request(settings, method, path, payload=None):
    require_test(settings)
    # Fixed provider origin; no client-supplied URLs or redirect credential leaks.
    with httpx.Client(timeout=httpx.Timeout(12, connect=5), follow_redirects=False) as client:
        response = client.request(
            method,
            BASE + path,
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret.get_secret_value()),
            json=payload,
        )
    response.raise_for_status()
    value = response.json()
    if not isinstance(value, dict):
        raise ValueError("Invalid provider response")
    return value


def _create_owned(db, settings, user, payload, key):
    require_test(settings)
    quotation = db.get(Quotation, payload.quotation_id)
    if quotation is None or user.role_code == "customer" and quotation.customer_user_id != user.id:
        raise AppError(404, "not_found", "Quotation not found.")
    if user.role_code not in {"customer", "sales", "admin"}:
        raise AppError(403, "forbidden", "You cannot create a payment order.")
    payment_service._lock_enquiry(db, quotation.enquiry_id)
    digest = payment_service._hash(
        {
            "quotation_id": str(quotation.id),
            "amount_minor": payload.amount_minor,
            "method": "razorpay",
        }
    )
    old = db.scalar(
        select(PaymentIntent).where(
            PaymentIntent.customer_user_id == quotation.customer_user_id,
            PaymentIntent.idempotency_key == key,
        )
    )
    if old:
        if old.request_hash != digest:
            raise AppError(
                409, "idempotency_conflict", "This key already belongs to another payment."
            )
        return old, db.get(ProviderPaymentOrder, old.id)
    inflight = db.scalar(
        select(PaymentIntent)
        .join(Quotation, PaymentIntent.quotation_id == Quotation.id)
        .where(
            Quotation.enquiry_id == quotation.enquiry_id,
            PaymentIntent.method == "razorpay",
            PaymentIntent.status.in_(("pending", "processing", "unresolved")),
        )
        .with_for_update(of=PaymentIntent)
    )
    if inflight is not None:
        if inflight.quotation_id == quotation.id and inflight.amount_minor == payload.amount_minor:
            return inflight, db.get(ProviderPaymentOrder, inflight.id)
        raise AppError(
            409,
            "payment_reconciliation_required",
            "Resolve the existing pending/unknown provider order before creating another.",
        )
    if quotation.status not in {"issued", "accepted"}:
        raise AppError(409, "invalid_transition", "Quotation cannot be paid.")
    if quotation.currency_code != "INR":
        raise AppError(422, "unsupported_currency", "Only INR is enabled.")
    payment_service._guard_amount(db, quotation, payload.amount_minor)
    intent = PaymentIntent(
        quotation_id=quotation.id,
        customer_user_id=quotation.customer_user_id,
        amount_minor=payload.amount_minor,
        currency_code="INR",
        method="razorpay",
        status="pending",
        is_test_only=True,
        provider="razorpay",
        idempotency_key=key,
        request_hash=digest,
    )
    db.add(intent)
    db.flush()
    order = ProviderPaymentOrder(intent_id=intent.id, refunded_minor=0, unapplied_minor=0)
    db.add(order)
    db.flush()
    # This function runs in a dedicated unit of work. Commit the local intent
    # before calling the provider, so a crash/timeout cannot erase its identity.
    db.commit()
    try:
        result = provider_request(
            settings,
            "POST",
            "/orders",
            {
                "amount": intent.amount_minor,
                "currency": "INR",
                "receipt": intent.id.hex,
                "partial_payment": False,
            },
        )
        if (
            not re.fullmatch(r"order_[A-Za-z0-9]+", str(result.get("id", "")))
            or type(result.get("amount")) is not int
            or result["amount"] != intent.amount_minor
            or result.get("currency") != "INR"
            or result.get("receipt") != intent.id.hex
        ):
            raise ValueError("Provider order did not match request")
        order.provider_order_id = result["id"]
    except (httpx.HTTPError, ValueError, KeyError):
        # The provider may have created an order before a timeout. Preserve the
        # uncertainty, block checkout, and do not automatically repeat POST.
        intent.status = "unresolved"
    db.add(
        PaymentAttempt(
            intent_id=intent.id,
            actor_user_id=user.id,
            outcome="provider_order_created"
            if order.provider_order_id
            else "provider_order_unknown",
            detail={"provider": "razorpay", "test_only": True},
        )
    )
    add_audit(
        db,
        actor_user_id=user.id,
        action="payment.razorpay_order_requested",
        entity_type="payment_intent",
        entity_id=intent.id,
        metadata={"status": intent.status, "test_only": True},
    )
    db.flush()
    return intent, order


def apply_payment(db, settings, intent, order, payment):
    pid = payment.get("id")
    if (
        not re.fullmatch(r"pay_[A-Za-z0-9]+", str(pid or ""))
        or payment.get("order_id") != order.provider_order_id
        or type(payment.get("amount")) is not int
        or payment["amount"] != intent.amount_minor
        or payment.get("currency") != intent.currency_code
    ):
        raise AppError(
            409,
            "provider_mismatch",
            "Provider amount, currency, transaction or order does not match.",
        )
    if order.provider_payment_id and order.provider_payment_id != pid:
        raise AppError(
            409,
            "provider_transaction_conflict",
            "A different transaction is already linked; reconcile manually.",
        )
    known = db.scalar(
        select(ProviderPaymentOrder).where(
            ProviderPaymentOrder.provider_payment_id == pid,
            ProviderPaymentOrder.intent_id != intent.id,
        )
    )
    if known:
        raise AppError(
            409, "provider_transaction_reused", "Transaction already belongs to another order."
        )
    refunded = payment.get("amount_refunded", 0)
    if type(refunded) is not int or not 0 <= refunded <= intent.amount_minor:
        raise AppError(409, "invalid_provider_refund", "Provider refund amount is invalid.")
    if payment.get("status") in {"captured", "refunded"} and payment.get("captured") is True:
        order.provider_payment_id = pid
        intent.transaction_reference = pid
        # Never discard an authenticated capture, even if two pending orders
        # captured concurrently. Excess is an explicit unapplied balance.
        already = payment_service.verified_total(db, intent.quotation_id)
        quotation = db.get(Quotation, intent.quotation_id)
        if intent.status != "verified":
            order.unapplied_minor = min(intent.amount_minor, max(0, already + intent.amount_minor - quotation.total_minor))
        intent.status = "verified"
        order.refunded_minor = max(order.refunded_minor, refunded)
    elif intent.status != "verified":
        intent.status = "failed" if payment.get("status") == "failed" else "processing"
    order.reconciled_at = utcnow()
    intent.updated_at = utcnow()
    db.add(
        PaymentAttempt(
            intent_id=intent.id,
            actor_user_id=None,
            outcome="provider_reconciled",
            detail={
                "provider": "razorpay",
                "status": intent.status,
                "test_only": True,
                "refunded_minor": order.refunded_minor,
                "unapplied_minor": order.unapplied_minor,
            },
        )
    )
    db.flush()
    return intent


def reconcile(db, settings, user, intent_id, payment_id, signature):
    require_test(settings)
    intent = payment_service.get_intent(db, user, intent_id)
    quote = db.get(Quotation, intent.quotation_id)
    payment_service._lock_enquiry(db, quote.enquiry_id)
    intent = db.scalar(select(PaymentIntent).where(PaymentIntent.id == intent_id).with_for_update())
    order = db.scalar(
        select(ProviderPaymentOrder)
        .where(ProviderPaymentOrder.intent_id == intent_id)
        .with_for_update()
    )
    if not order or not order.provider_order_id:
        raise AppError(
            409,
            "provider_order_unresolved",
            "No confirmed provider order; manual reconciliation required.",
        )
    expected = hmac.new(
        settings.razorpay_key_secret.get_secret_value().encode(),
        f"{order.provider_order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise AppError(400, "invalid_provider_signature", "Checkout signature is invalid.")
    if not re.fullmatch(r"pay_[A-Za-z0-9]+", payment_id):
        raise AppError(422, "invalid_payment_id", "Invalid provider transaction ID.")
    try:
        payment = provider_request(settings, "GET", "/payments/" + payment_id)
    except (httpx.HTTPError, ValueError):
        raise AppError(
            503,
            "provider_unavailable",
            "Payment status could not be verified; retry reconciliation, not payment.",
        ) from None
    return apply_payment(db, settings, intent, order, payment)


def webhook(db, settings, raw, signature, event_id):
    require_test(settings)
    expected = hmac.new(
        settings.razorpay_webhook_secret.get_secret_value().encode(), raw, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise AppError(400, "invalid_provider_signature", "Webhook signature is invalid.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", event_id):
        raise AppError(400, "event_id_required", "A valid provider event ID is required.")
    digest = hashlib.sha256(raw).hexdigest()
    # Transaction advisory lock protects duplicate event IDs before insert.
    from sqlalchemy import text

    db.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {"key": int.from_bytes(hashlib.sha256(event_id.encode()).digest()[:8], "big", signed=True)},
    )
    prior = db.get(ProviderEvent, event_id)
    if prior:
        if prior.body_hash != digest:
            raise AppError(409, "event_conflict", "Event ID was reused with another payload.")
        return prior
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise AppError(400, "invalid_webhook", "Webhook must be JSON.") from None
    if not isinstance(payload, dict):
        raise AppError(400, "invalid_webhook", "Webhook must be an object.")
    event_type = payload.get("event")
    if not isinstance(event_type, str) or len(event_type) > 80:
        raise AppError(400, "invalid_webhook", "Missing event type.")
    event = ProviderEvent(
        event_id=event_id, body_hash=digest, event_type=event_type, status="ignored"
    )
    if event_type in {"payment.captured", "payment.failed", "payment.authorized"}:
        try:
            payment = payload["payload"]["payment"]["entity"]
            provider_id = payment["order_id"]
        except (KeyError, TypeError):
            raise AppError(400, "invalid_webhook", "Missing provider payment entity.") from None
        located = db.scalar(
            select(ProviderPaymentOrder).where(
                ProviderPaymentOrder.provider_order_id == provider_id
            )
        )
        if located is None:
            raise AppError(409, "unknown_provider_order", "Provider order is not known locally.")
        intent = db.get(PaymentIntent, located.intent_id)
        quote = db.get(Quotation, intent.quotation_id)
        payment_service._lock_enquiry(db, quote.enquiry_id)
        intent = db.scalar(
            select(PaymentIntent).where(PaymentIntent.id == intent.id).with_for_update()
        )
        order = db.scalar(
            select(ProviderPaymentOrder)
            .where(ProviderPaymentOrder.intent_id == intent.id)
            .with_for_update()
        )
        if event_type == "payment.captured" and (
            payment.get("status") != "captured" or payment.get("captured") is not True
        ):
            raise AppError(409, "provider_mismatch", "Capture event has no captured payment.")
        apply_payment(db, settings, intent, order, payment)
        event.intent_id = intent.id
        event.status = "applied"
    elif event_type == "refund.processed":
        try:
            refund = payload["payload"]["refund"]["entity"]
            payment_id = refund["payment_id"]
        except (KeyError, TypeError):
            raise AppError(400, "invalid_webhook", "Missing refund payment identity.") from None
        if refund.get("status") != "processed" or not re.fullmatch(
            r"pay_[A-Za-z0-9]+", str(payment_id)
        ):
            raise AppError(409, "provider_mismatch", "Refund is not a processed provider record.")
        located = db.scalar(
            select(ProviderPaymentOrder).where(
                ProviderPaymentOrder.provider_payment_id == payment_id
            )
        )
        if located is None:
            raise AppError(
                409, "unknown_provider_payment", "Refund payment is not yet reconciled locally."
            )
        intent = db.get(PaymentIntent, located.intent_id)
        quote = db.get(Quotation, intent.quotation_id)
        payment_service._lock_enquiry(db, quote.enquiry_id)
        intent = db.scalar(
            select(PaymentIntent).where(PaymentIntent.id == intent.id).with_for_update()
        )
        order = db.scalar(
            select(ProviderPaymentOrder)
            .where(ProviderPaymentOrder.intent_id == intent.id)
            .with_for_update()
        )
        try:
            payment = provider_request(settings, "GET", "/payments/" + payment_id)
        except (httpx.HTTPError, ValueError):
            raise AppError(
                503,
                "provider_unavailable",
                "Refund reconciliation awaits an authenticated provider response.",
            ) from None
        apply_payment(db, settings, intent, order, payment)
        event.intent_id = intent.id
        event.status = "applied"
    db.add(event)
    db.flush()
    return event


def create(db, settings, user, payload, key):
    from sqlalchemy.orm import Session

    from app.models.identity import User

    with Session(db.get_bind(), expire_on_commit=False) as owned:
        actor = owned.get(User, user.id)
        if actor is None or not actor.is_active:
            raise AppError(403, "forbidden", "An active authenticated account is required.")
        intent, order = _create_owned(owned, settings, actor, payload, key)
        owned.commit()
        return intent, order
