"""Warranty extensions on top of Phase 4B's serial-level policy model.

No parallel warranty system is introduced: eligibility reads the exact
``SerializedAssetCoverage`` row plus its ``WarrantyPolicyVersion`` (the same
rows coverage decisions snapshot). An extension lengthens that row's
``ends_at``; the extension row snapshots the original end date and the full
lifecycle, so historical decisions keep pointing at unchanged snapshots.

Money never moves here. A paid extension waits in ``pending_payment`` until
support records a verified real-world payment reference. Phase 4C owns
invoices and accounting; the offer row is the purchase contract 4C can
consume (offer id/version, customer, serial, price, terms source).
"""

import hashlib
import json
import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import utcnow
from app.models.identity import User
from app.models.phase3 import EquipmentSerial
from app.models.phase4e import (
    WarrantyExtension,
    WarrantyExtensionOffer,
    WarrantyExtensionTerms,
)
from app.models.warranty import SerializedAssetCoverage, WarrantyPolicy, WarrantyPolicyVersion
from app.models.workflow import SalesOrder
from app.repositories.queries import add_audit

CUSTOMER = "customer"
SUPPORT = {"support", "admin"}
ADMIN = {"admin"}
OFFER_VALIDITY_DAYS = 30


def _digest(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_terms(
    db: Session, user: User, *, policy_id: uuid.UUID, extension_days: int,
    price_minor: int, currency: str, window_days: int,
    eligible_categories: list[str], max_extensions: int,
    requires_approval: bool,
) -> WarrantyExtensionTerms:
    if user.role_code not in ADMIN:
        raise AppError(403, "forbidden", "Only an administrator can manage extension terms.")
    policy = db.get(WarrantyPolicy, policy_id)
    if policy is None:
        raise AppError(404, "not_found", "Warranty policy not found.")
    if extension_days <= 0 or price_minor < 0 or window_days < 0 or max_extensions < 1:
        raise AppError(422, "validation_error", "Extension terms must be positive.")
    if not eligible_categories:
        raise AppError(422, "validation_error", "At least one eligible category is required.")
    latest = db.scalar(
        select(func.max(WarrantyExtensionTerms.version)).where(
            WarrantyExtensionTerms.policy_id == policy.id
        )
    ) or 0
    db.query(WarrantyExtensionTerms).filter(
        WarrantyExtensionTerms.policy_id == policy.id,
        WarrantyExtensionTerms.is_active.is_(True),
    ).update({"is_active": False})
    terms = WarrantyExtensionTerms(
        policy_id=policy.id, version=latest + 1, extension_days=extension_days,
        price_minor=price_minor, currency=currency, window_days=window_days,
        eligible_categories=list(eligible_categories), max_extensions=max_extensions,
        requires_approval=requires_approval, is_active=True,
        created_by_user_id=user.id,
    )
    db.add(terms)
    add_audit(db, actor_user_id=user.id, action="warranty.extension_terms_created",
              entity_type="warranty_extension_terms", entity_id=terms.id,
              metadata={"policy": policy.code, "version": terms.version})
    db.flush()
    return terms


def list_terms(db: Session, user: User) -> list[WarrantyExtensionTerms]:
    if user.role_code not in SUPPORT:
        raise AppError(403, "forbidden", "You do not have access to extension terms.")
    return list(
        db.scalars(
            select(WarrantyExtensionTerms).order_by(
                WarrantyExtensionTerms.policy_id, WarrantyExtensionTerms.version.desc()
            )
        ).all()
    )


def _active_terms(db: Session, policy_id: uuid.UUID) -> WarrantyExtensionTerms | None:
    return db.scalar(
        select(WarrantyExtensionTerms)
        .where(
            WarrantyExtensionTerms.policy_id == policy_id,
            WarrantyExtensionTerms.is_active.is_(True),
        )
        .order_by(WarrantyExtensionTerms.version.desc())
    )


def _serial_for_customer(db: Session, user: User, serial_number: str) -> EquipmentSerial:
    serial = db.scalar(
        select(EquipmentSerial).where(
            func.lower(EquipmentSerial.serial_number) == serial_number.strip().lower()
        )
    )
    if serial is None:
        raise AppError(404, "not_found", "Equipment serial not found.")
    order = db.get(SalesOrder, serial.order_id) if serial.order_id else None
    if order is None or order.customer_user_id != user.id:
        raise AppError(404, "not_found", "Equipment serial not found.")
    return serial


def _coverage_for_serial(db: Session, serial: EquipmentSerial) -> SerializedAssetCoverage:
    coverage = db.scalar(
        select(SerializedAssetCoverage).where(
            SerializedAssetCoverage.serial_id == serial.id
        )
    )
    if coverage is None:
        raise AppError(404, "not_found", "No warranty coverage exists for this unit.")
    return coverage


def _live_extensions(db: Session, coverage_id: uuid.UUID) -> list[WarrantyExtension]:
    return list(
        db.scalars(
            select(WarrantyExtension)
            .where(
                WarrantyExtension.coverage_id == coverage_id,
                WarrantyExtension.status.not_in(
                    ["rejected", "cancelled", "expired"]
                ),
            )
        ).all()
    )


def evaluate_eligibility(
    db: Session, user: User, serial_number: str
) -> dict:
    """Eligible equipment check for the owning customer. Never invents coverage."""
    if user.role_code != CUSTOMER:
        raise AppError(403, "forbidden", "Extension eligibility is checked by customers.")
    serial = _serial_for_customer(db, user, serial_number)
    coverage = _coverage_for_serial(db, serial)
    version = db.get(WarrantyPolicyVersion, coverage.policy_version_id)
    policy = db.get(WarrantyPolicy, version.policy_id) if version else None
    if version is None or policy is None:
        return _ineligible(serial, coverage, "The coverage policy is no longer available.")
    terms = _active_terms(db, policy.id)
    if terms is None:
        return _ineligible(serial, coverage, "Extensions are not offered for this policy.")
    if policy.category not in terms.eligible_categories:
        return _ineligible(serial, coverage, "This product category cannot be extended.")
    exclusions = dict(version.exclusions or {})
    excluded_components = set(exclusions.get("components") or [])
    if serial.component_code in excluded_components:
        return _ineligible(serial, coverage, "This unit is excluded from extension.")
    if coverage.status in {"void", "superseded"}:
        return _ineligible(serial, coverage, "This coverage cannot be extended.")
    deadline = coverage.ends_at + timedelta(days=terms.window_days)
    if utcnow() > deadline:
        return _ineligible(serial, coverage, "The extension window has closed.")
    live = _live_extensions(db, coverage.id)
    if live:
        return _ineligible(serial, coverage, "An extension is already in progress.")
    active_count = db.scalar(
        select(func.count())
        .select_from(WarrantyExtension)
        .where(
            WarrantyExtension.coverage_id == coverage.id,
            WarrantyExtension.status == "active",
        )
    ) or 0
    if active_count >= terms.max_extensions:
        return _ineligible(serial, coverage, "The maximum number of extensions was reached.")
    offer = _live_offer(db, coverage.id)
    return {
        "eligible": True,
        "reason": None,
        "serial_number": serial.serial_number,
        "component_code": serial.component_code,
        "coverage_id": str(coverage.id),
        "coverage_status": coverage.status,
        "coverage_ends_at": coverage.ends_at.isoformat(),
        "policy_code": policy.code,
        "policy_version": version.version_number,
        "extension_days": terms.extension_days,
        "price_minor": terms.price_minor,
        "currency": terms.currency,
        "payment_required": terms.price_minor > 0,
        "window_days": terms.window_days,
        "offer_id": str(offer.id) if offer else None,
        "offer_version": offer.version if offer else None,
    }


def _ineligible(
    serial: EquipmentSerial, coverage: SerializedAssetCoverage, reason: str
) -> dict:
    return {
        "eligible": False,
        "reason": reason,
        "serial_number": serial.serial_number,
        "coverage_id": str(coverage.id),
        "coverage_status": coverage.status,
        "coverage_ends_at": coverage.ends_at.isoformat(),
        "extension_days": None,
        "price_minor": None,
        "currency": None,
        "payment_required": None,
        "offer_id": None,
        "offer_version": None,
    }


def _live_offer(db: Session, coverage_id: uuid.UUID) -> WarrantyExtensionOffer | None:
    offer = db.scalar(
        select(WarrantyExtensionOffer)
        .where(
            WarrantyExtensionOffer.coverage_id == coverage_id,
            WarrantyExtensionOffer.status == "offered",
        )
        .order_by(WarrantyExtensionOffer.version.desc())
    )
    if offer is not None and offer.expires_at <= utcnow():
        offer.status = "expired"
        return None
    return offer


def ensure_offer(
    db: Session, user: User, *, coverage_id: uuid.UUID
) -> WarrantyExtensionOffer:
    if user.role_code not in SUPPORT:
        raise AppError(403, "forbidden", "Only support can issue extension offers.")
    coverage = db.get(SerializedAssetCoverage, coverage_id)
    if coverage is None:
        raise AppError(404, "not_found", "Coverage not found.")
    version = db.get(WarrantyPolicyVersion, coverage.policy_version_id)
    terms = _active_terms(db, version.policy_id) if version else None
    if version is None or terms is None:
        raise AppError(409, "terms_missing", "No active extension terms for this policy.")
    existing = _live_offer(db, coverage.id)
    if existing is not None and existing.terms_id == terms.id:
        return existing
    if existing is not None:
        existing.status = "superseded"
    latest_version = db.scalar(
        select(func.max(WarrantyExtensionOffer.version)).where(
            WarrantyExtensionOffer.coverage_id == coverage.id
        )
    ) or 0
    offer = WarrantyExtensionOffer(
        coverage_id=coverage.id, version=latest_version + 1, terms_id=terms.id,
        policy_version_id=version.id, extension_days=terms.extension_days,
        price_minor=terms.price_minor, currency=terms.currency,
        payment_required=terms.price_minor > 0, status="offered",
        expires_at=utcnow() + timedelta(days=OFFER_VALIDITY_DAYS),
        created_by_user_id=user.id,
    )
    db.add(offer)
    add_audit(db, actor_user_id=user.id, action="warranty.extension_offered",
              entity_type="warranty_extension_offer", entity_id=offer.id,
              metadata={"coverage_id": str(coverage.id), "version": offer.version})
    db.flush()
    return offer


def request_extension(
    db: Session, user: User, *, coverage_id: uuid.UUID, idempotency_key: str
) -> WarrantyExtension:
    if user.role_code != CUSTOMER:
        raise AppError(403, "forbidden", "Extensions are requested by customers.")
    duplicate = db.scalar(
        select(WarrantyExtension).where(
            WarrantyExtension.idempotency_key == idempotency_key
        )
    )
    if duplicate is not None:
        if duplicate.customer_user_id != user.id:
            raise AppError(409, "conflict", "This request conflicts with existing data.")
        return duplicate
    coverage = db.get(SerializedAssetCoverage, coverage_id)
    if coverage is None or coverage.customer_user_id != user.id:
        raise AppError(404, "not_found", "Coverage not found.")
    version = db.get(WarrantyPolicyVersion, coverage.policy_version_id)
    terms = _active_terms(db, version.policy_id) if version else None
    if version is None or terms is None:
        raise AppError(409, "terms_missing", "Extensions are not offered for this policy.")
    serial = db.get(EquipmentSerial, coverage.serial_id)
    check = evaluate_eligibility(db, user, serial.serial_number if serial else "")
    if not check["eligible"]:
        raise AppError(409, "ineligible", check["reason"] or "This unit cannot be extended.")
    offer = _live_offer(db, coverage.id)
    if offer is None or offer.terms_id != terms.id:
        latest_version = db.scalar(
            select(func.max(WarrantyExtensionOffer.version)).where(
                WarrantyExtensionOffer.coverage_id == coverage.id
            )
        ) or 0
        offer = WarrantyExtensionOffer(
            coverage_id=coverage.id, version=latest_version + 1, terms_id=terms.id,
            policy_version_id=version.id, extension_days=terms.extension_days,
            price_minor=terms.price_minor, currency=terms.currency,
            payment_required=terms.price_minor > 0, status="offered",
            expires_at=utcnow() + timedelta(days=OFFER_VALIDITY_DAYS),
            created_by_user_id=user.id,
        )
        db.add(offer)
        db.flush()
    extension = WarrantyExtension(
        offer_id=offer.id, offer_version=offer.version, serial_id=coverage.serial_id,
        coverage_id=coverage.id, customer_user_id=user.id,
        policy_version_id=version.id, status="requested",
        extension_days=offer.extension_days, price_minor=offer.price_minor,
        currency=offer.currency, original_ends_at=coverage.ends_at,
        new_ends_at=None, idempotency_key=idempotency_key,
        request_hash=_digest({"coverage_id": str(coverage.id), "offer_version": offer.version}),
    )
    db.add(extension)
    db.flush()
    add_audit(db, actor_user_id=user.id, action="warranty.extension_requested",
              entity_type="warranty_extension", entity_id=extension.id,
              metadata={"offer_version": offer.version})
    if terms.requires_approval:
        extension.status = "pending_approval"
        add_audit(db, actor_user_id=user.id, action="warranty.extension_pending_approval",
                  entity_type="warranty_extension", entity_id=extension.id, metadata={})
    elif offer.payment_required:
        extension.status = "pending_payment"
        add_audit(db, actor_user_id=user.id, action="warranty.extension_pending_payment",
                  entity_type="warranty_extension", entity_id=extension.id, metadata={})
    else:
        _activate(db, user, extension, offer, coverage)
    db.flush()
    return extension


def _activate(
    db: Session, user: User, extension: WarrantyExtension,
    offer: WarrantyExtensionOffer, coverage: SerializedAssetCoverage,
) -> None:
    if offer.status != "offered" or offer.expires_at <= utcnow():
        offer.status = "expired"
        raise AppError(409, "offer_expired", "The extension offer expired.")
    if extension.offer_id != offer.id or extension.offer_version != offer.version:
        raise AppError(409, "stale_offer", "The extension offer changed. Request again.")
    extension.new_ends_at = extension.original_ends_at + timedelta(days=extension.extension_days)
    coverage.ends_at = extension.new_ends_at
    coverage.status = "active"
    extension.status = "active"
    add_audit(db, actor_user_id=user.id, action="warranty.extension_activated",
              entity_type="warranty_extension", entity_id=extension.id,
              metadata={"new_ends_at": extension.new_ends_at.isoformat()})


def approve_extension(
    db: Session, user: User, *, extension_id: uuid.UUID, note: str | None
) -> WarrantyExtension:
    if user.role_code not in SUPPORT:
        raise AppError(403, "forbidden", "Only support can approve extensions.")
    extension = db.get(WarrantyExtension, extension_id)
    if extension is None:
        raise AppError(404, "not_found", "Extension not found.")
    if extension.status != "pending_approval":
        raise AppError(409, "invalid_transition", "This extension cannot be approved.")
    offer = db.get(WarrantyExtensionOffer, extension.offer_id)
    coverage = db.get(SerializedAssetCoverage, extension.coverage_id)
    extension.decided_by_user_id = user.id
    extension.decision_note = note
    if offer.payment_required:
        extension.status = "pending_payment"
    else:
        _activate(db, user, extension, offer, coverage)
    add_audit(db, actor_user_id=user.id, action="warranty.extension_approved",
              entity_type="warranty_extension", entity_id=extension.id,
              metadata={"status": extension.status})
    db.flush()
    return extension


def reject_extension(
    db: Session, user: User, *, extension_id: uuid.UUID, note: str
) -> WarrantyExtension:
    if user.role_code not in SUPPORT:
        raise AppError(403, "forbidden", "Only support can reject extensions.")
    extension = db.get(WarrantyExtension, extension_id)
    if extension is None:
        raise AppError(404, "not_found", "Extension not found.")
    if extension.status not in {"requested", "pending_approval", "pending_payment"}:
        raise AppError(409, "invalid_transition", "This extension cannot be rejected.")
    if not note or len(note.strip()) < 3:
        raise AppError(422, "validation_error", "A rejection needs a short note.")
    extension.status = "rejected"
    extension.decided_by_user_id = user.id
    extension.decision_note = note.strip()
    add_audit(db, actor_user_id=user.id, action="warranty.extension_rejected",
              entity_type="warranty_extension", entity_id=extension.id, metadata={})
    db.flush()
    return extension


def cancel_extension(db: Session, user: User, *, extension_id: uuid.UUID) -> WarrantyExtension:
    extension = db.get(WarrantyExtension, extension_id)
    if extension is None or extension.customer_user_id != user.id:
        raise AppError(404, "not_found", "Extension not found.")
    if extension.status not in {"requested", "pending_approval", "pending_payment"}:
        raise AppError(409, "invalid_transition", "This extension can no longer be cancelled.")
    extension.status = "cancelled"
    add_audit(db, actor_user_id=user.id, action="warranty.extension_cancelled",
              entity_type="warranty_extension", entity_id=extension.id, metadata={})
    db.flush()
    return extension


def record_payment_and_activate(
    db: Session, user: User, *, extension_id: uuid.UUID, payment_reference: str
) -> WarrantyExtension:
    """Support confirms a real-world payment, then the extension activates.

    The reference is evidence of money received outside SolarOps (bank
    transfer, UPI, cash receipt). Nothing here settles an invoice; Phase 4C
    owns accounting and can reconcile against the offer contract.
    """
    if user.role_code not in SUPPORT:
        raise AppError(403, "forbidden", "Only support can verify extension payments.")
    extension = db.get(WarrantyExtension, extension_id)
    if extension is None:
        raise AppError(404, "not_found", "Extension not found.")
    if extension.status != "pending_payment":
        raise AppError(409, "invalid_transition", "This extension is not awaiting payment.")
    reference = (payment_reference or "").strip()
    if len(reference) < 4:
        raise AppError(422, "validation_error", "A payment reference is required.")
    offer = db.get(WarrantyExtensionOffer, extension.offer_id)
    coverage = db.get(SerializedAssetCoverage, extension.coverage_id)
    extension.payment_reference = reference[:120]
    extension.verified_payment_at = utcnow()
    extension.verified_payment_by = user.id
    add_audit(db, actor_user_id=user.id, action="warranty.extension_payment_verified",
              entity_type="warranty_extension", entity_id=extension.id,
              metadata={"payment_reference": extension.payment_reference})
    _activate(db, user, extension, offer, coverage)
    db.flush()
    return extension


def list_extensions(db: Session, user: User) -> list[WarrantyExtension]:
    query = select(WarrantyExtension).order_by(WarrantyExtension.created_at.desc())
    if user.role_code == CUSTOMER:
        query = query.where(WarrantyExtension.customer_user_id == user.id)
    elif user.role_code not in SUPPORT:
        raise AppError(403, "forbidden", "You do not have access to extensions.")
    return list(db.scalars(query).all())


def get_extension(db: Session, user: User, extension_id: uuid.UUID) -> WarrantyExtension:
    extension = db.get(WarrantyExtension, extension_id)
    if extension is None:
        raise AppError(404, "not_found", "Extension not found.")
    if user.role_code == CUSTOMER and extension.customer_user_id != user.id:
        raise AppError(404, "not_found", "Extension not found.")
    if user.role_code not in SUPPORT and user.role_code != CUSTOMER:
        raise AppError(403, "forbidden", "You do not have access to extensions.")
    return extension
