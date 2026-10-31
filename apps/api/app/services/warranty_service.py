"""Serial-level warranty intelligence.

Order-level Phase 3 warranties are left alone. This module answers one
question for one exact installed unit: given the customer, the serial, the
reported fault, and an evaluation timestamp, which policy version applies and
is the fault covered. Every verdict freezes the policy and coverage it used,
so later policy revisions cannot rewrite history. Example durations from the
original scenario (two-year inverters, twenty-year panels) are entered as
policy versions through the admin API, never hardcoded here.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import utcnow
from app.models.identity import User
from app.models.phase3 import Delivery, EquipmentSerial
from app.models.support import ServiceTicket, ServiceTicketEvent
from app.models.warranty import (
    CoverageDecision,
    SerializedAssetCoverage,
    WarrantyException,
    WarrantyPolicy,
    WarrantyPolicyVersion,
)
from app.models.workflow import SalesOrder
from app.repositories.queries import add_audit

CUSTOMER = "customer"
SUPPORT = {"support", "admin"}
ADMIN = {"admin"}


def _digest(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _require_roles(user: User, allowed: set[str]) -> None:
    if user.role_code not in allowed:
        raise AppError(403, "forbidden", "You do not have access to this action.")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_code(code: str) -> str:
    cleaned = (code or "").strip().upper()
    if len(cleaned) < 3 or len(cleaned) > 32:
        raise AppError(422, "validation_error", "Policy code must be 3-32 characters.")
    if any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-" for char in cleaned):
        raise AppError(422, "validation_error", "Policy code allows letters, digits, dash.")
    return cleaned


def create_policy(db: Session, user: User, code: str, issuer: str,
                  category: str, description: str) -> WarrantyPolicy:
    _require_roles(user, ADMIN)
    normalized = _normalize_code(code)
    if db.scalar(select(WarrantyPolicy).where(WarrantyPolicy.code == normalized)) is not None:
        raise AppError(409, "policy_exists", "This warranty policy code already exists.")
    if len(issuer.strip()) < 2 or len(category.strip()) < 2 or len(description.strip()) < 10:
        raise AppError(422, "validation_error", "Issuer, category, and description are required.")
    policy = WarrantyPolicy(
        code=normalized, issuer=issuer.strip(), category=category.strip(),
        description=description.strip(), created_by_user_id=user.id,
    )
    db.add(policy)
    db.flush()
    add_audit(db, actor_user_id=user.id, action="warranty.policy_created",
              entity_type="warranty_policy", entity_id=policy.id,
              metadata={"code": normalized})
    db.flush()
    return policy


def create_policy_version(db: Session, user: User, policy_id: uuid.UUID,
                          payload: dict) -> WarrantyPolicyVersion:
    _require_roles(user, ADMIN)
    policy = db.get(WarrantyPolicy, policy_id)
    if policy is None:
        raise AppError(404, "not_found", "Warranty policy not found.")
    duration = payload.get("duration_days", 0)
    if not isinstance(duration, int) or duration <= 0:
        raise AppError(422, "validation_error", "Duration must be a positive number of days.")
    covered_faults = payload.get("covered_fault_categories") or []
    if not covered_faults:
        raise AppError(422, "validation_error", "Covered fault categories cannot be empty.")
    continuation = payload.get("replacement_continuation", "remainder")
    if continuation not in ("remainder", "fixed_days"):
        raise AppError(422, "validation_error", "Continuation must be remainder or fixed_days.")
    fixed_days = payload.get("replacement_warranty_days")
    if continuation == "fixed_days" and (not isinstance(fixed_days, int) or fixed_days <= 0):
        raise AppError(422, "validation_error", "Fixed-day continuation needs positive days.")
    effective_from = _as_utc(payload["effective_from"])
    effective_to = payload.get("effective_to")
    if effective_to is not None:
        effective_to = _as_utc(effective_to)
        if effective_to <= effective_from:
            raise AppError(422, "validation_error", "The version must end after it starts.")
    latest = db.scalar(
        select(func.max(WarrantyPolicyVersion.version_number)).where(
            WarrantyPolicyVersion.policy_id == policy.id)
    ) or 0
    version = WarrantyPolicyVersion(
        policy_id=policy.id, version_number=latest + 1, duration_days=duration,
        applicable_components=list(payload.get("applicable_components") or []),
        covered_fault_categories=list(covered_faults),
        covered_components=list(payload.get("covered_components") or []),
        covered_repair_types=list(payload.get("covered_repair_types") or []),
        exclusions=dict(payload.get("exclusions") or {"fault_categories": [], "components": []}),
        labour_covered=bool(payload.get("labour_covered", False)),
        replacement_allowed=bool(payload.get("replacement_allowed", False)),
        replacement_continuation=continuation,
        replacement_warranty_days=fixed_days if continuation == "fixed_days" else None,
        manufacturer_auth_required=bool(payload.get("manufacturer_auth_required", False)),
        repeat_replacement_allowed=bool(payload.get("repeat_replacement_allowed", False)),
        effective_from=effective_from, effective_to=effective_to,
        created_by_user_id=user.id,
    )
    db.add(version)
    db.flush()
    add_audit(db, actor_user_id=user.id, action="warranty.policy_version_created",
              entity_type="warranty_policy_version", entity_id=version.id,
              metadata={"policy": policy.code, "version": version.version_number})
    db.flush()
    return version


def list_policies(db: Session, user: User) -> list[WarrantyPolicy]:
    _require_roles(user, SUPPORT)
    return list(db.scalars(select(WarrantyPolicy).order_by(WarrantyPolicy.code)).all())


def list_policy_versions(db: Session, user: User,
                         policy_id: uuid.UUID) -> list[WarrantyPolicyVersion]:
    _require_roles(user, SUPPORT)
    policy = db.get(WarrantyPolicy, policy_id)
    if policy is None:
        raise AppError(404, "not_found", "Warranty policy not found.")
    return list(
        db.scalars(
            select(WarrantyPolicyVersion)
            .where(WarrantyPolicyVersion.policy_id == policy.id)
            .order_by(WarrantyPolicyVersion.version_number.desc())
        ).all()
    )


def _matching_versions(db: Session, component_code: str,
                       at: datetime) -> list[tuple[WarrantyPolicy, WarrantyPolicyVersion]]:
    """All versions covering a component at a timestamp, newest first."""
    rows = db.execute(
        select(WarrantyPolicy, WarrantyPolicyVersion)
        .join(WarrantyPolicyVersion, WarrantyPolicyVersion.policy_id == WarrantyPolicy.id)
        .where(WarrantyPolicyVersion.effective_from <= at)
        .where(
            (WarrantyPolicyVersion.effective_to.is_(None))
            | (WarrantyPolicyVersion.effective_to >= at)
        )
        .order_by(WarrantyPolicyVersion.effective_from.desc(), WarrantyPolicy.code.asc())
    ).all()
    matched = []
    for policy, version in rows:
        applicable = version.applicable_components or []
        if not applicable or component_code in applicable:
            matched.append((policy, version))
    return matched


def _confirmed_delivery(db: Session, order_id: uuid.UUID) -> Delivery | None:
    return db.scalar(
        select(Delivery)
        .where(Delivery.order_id == order_id, Delivery.status == "confirmed")
        .order_by(Delivery.created_at.desc())
    )


def activate_coverages_for_order(db: Session, user: User,
                                 order_id: uuid.UUID) -> list[SerializedAssetCoverage]:
    _require_roles(user, SUPPORT)
    order = db.get(SalesOrder, order_id)
    if order is None:
        raise AppError(404, "not_found", "Order not found.")
    delivery = _confirmed_delivery(db, order.id)
    if delivery is None or delivery.confirmed_at is None:
        raise AppError(
            409, "no_confirmed_delivery",
            "Coverages activate only from a valid confirmed delivery.",
        )
    confirmed_at = _as_utc(delivery.confirmed_at)
    created: list[SerializedAssetCoverage] = []
    serials = list(
        db.scalars(
            select(EquipmentSerial).where(
                EquipmentSerial.order_id == order.id,
                EquipmentSerial.status == "installed",
            )
        ).all()
    )
    for serial in serials:
        if (
            db.scalar(
                select(SerializedAssetCoverage).where(
                    SerializedAssetCoverage.serial_id == serial.id)
            )
            is not None
        ):
            continue
        matched = _matching_versions(db, serial.component_code, confirmed_at)
        if not matched:
            continue
        _, version = matched[0]
        starts_at = confirmed_at
        ends_at = starts_at + timedelta(days=version.duration_days)
        coverage = SerializedAssetCoverage(
            serial_id=serial.id, policy_version_id=version.id, order_id=order.id,
            customer_user_id=order.customer_user_id, site_id=None,
            delivery_id=delivery.id, activated_at=utcnow(),
            starts_at=starts_at, ends_at=ends_at,
            status="active" if utcnow() <= ends_at else "expired",
        )
        db.add(coverage)
        db.flush()
        add_audit(db, actor_user_id=user.id, action="warranty.coverage_activated",
                  entity_type="serialized_asset_coverage", entity_id=coverage.id,
                  metadata={"serial": serial.serial_number, "ends_at": ends_at.isoformat()})
        created.append(coverage)
    db.flush()
    return created


def _ticket_serial(db: Session, ticket_id: uuid.UUID,
                   serial_number: str) -> tuple[ServiceTicket, EquipmentSerial]:
    ticket = db.get(ServiceTicket, ticket_id)
    if ticket is None:
        raise AppError(404, "not_found", "Ticket not found.")
    serial = db.scalar(
        select(EquipmentSerial).where(
            func.lower(EquipmentSerial.serial_number) == serial_number.strip().lower())
    )
    if serial is None or serial.order_id != ticket.order_id:
        raise AppError(404, "not_found", "Equipment serial not found on this ticket order.")
    if serial.status != "installed":
        raise AppError(409, "serial_not_installed", "Only installed equipment is covered.")
    return ticket, serial


def _snapshot_version(version: WarrantyPolicyVersion) -> dict:
    return {
        "policy_id": str(version.policy_id), "version_id": str(version.id),
        "version_number": version.version_number, "duration_days": version.duration_days,
        "applicable_components": version.applicable_components,
        "covered_fault_categories": version.covered_fault_categories,
        "covered_components": version.covered_components,
        "covered_repair_types": version.covered_repair_types,
        "exclusions": version.exclusions, "labour_covered": version.labour_covered,
        "replacement_allowed": version.replacement_allowed,
        "replacement_continuation": version.replacement_continuation,
        "replacement_warranty_days": version.replacement_warranty_days,
        "manufacturer_auth_required": version.manufacturer_auth_required,
        "repeat_replacement_allowed": version.repeat_replacement_allowed,
    }


def _snapshot_coverage(coverage: SerializedAssetCoverage) -> dict:
    return {
        "coverage_id": str(coverage.id), "serial_id": str(coverage.serial_id),
        "status": coverage.status, "starts_at": _as_utc(coverage.starts_at).isoformat(),
        "ends_at": _as_utc(coverage.ends_at).isoformat(),
        "delivery_id": str(coverage.delivery_id),
    }


def evaluate_coverage(db: Session, user: User, ticket_id: uuid.UUID, serial_number: str,
                      fault_category: str | None, evaluated_at: datetime | None,
                      idempotency_key: str) -> tuple[CoverageDecision, bool]:
    _require_roles(user, SUPPORT)
    ticket, serial = _ticket_serial(db, ticket_id, serial_number)
    at = _as_utc(evaluated_at) if evaluated_at is not None else utcnow()
    category = (fault_category or ticket.category or "").strip() or None
    digest = _digest({"ticket_id": str(ticket.id), "serial_id": str(serial.id),
                      "fault_category": category, "fault_code": ticket.fault_code,
                      "evaluation": at.isoformat() if evaluated_at is not None else at.date().isoformat()})
    keyed = db.scalar(
        select(CoverageDecision).where(
            CoverageDecision.ticket_id == ticket.id,
            CoverageDecision.idempotency_key == idempotency_key,
        )
    )
    if keyed is not None:
        if keyed.request_hash != digest:
            raise AppError(409, "idempotency_conflict",
                           "This Idempotency-Key was already used for a different evaluation.")
        return keyed, False
    matched = _matching_versions(db, serial.component_code, at)
    version = matched[0][1] if matched else None
    exception = db.scalar(
        select(WarrantyException).where(
            WarrantyException.ticket_id == ticket.id,
            WarrantyException.serial_id == serial.id)
    )
    coverage = db.scalar(
        select(SerializedAssetCoverage).where(SerializedAssetCoverage.serial_id == serial.id)
    )
    repeat_key = {"version_id": str(version.id) if version else None,
                  "coverage": _snapshot_coverage(coverage) if coverage else None,
                  "fault_code": ticket.fault_code,
                  "fault_category": category,
                  "exception_id": str(exception.id) if exception else None}
    latest = db.scalar(
        select(CoverageDecision)
        .where(CoverageDecision.ticket_id == ticket.id,
               CoverageDecision.serial_id == serial.id)
        .order_by(CoverageDecision.created_at.desc())
    )
    if latest is not None and latest.evidence is not None:
        prior = latest.evidence.get("repeat_key")
        if (prior == repeat_key
                and (_as_utc(latest.evaluated_at) == at if evaluated_at is not None
                     else _as_utc(latest.evaluated_at).date() == at.date())):
            return latest, False
    coverage = db.scalar(
        select(SerializedAssetCoverage).where(
            SerializedAssetCoverage.serial_id == serial.id)
    )
    evidence: dict = {
        "serial_number": serial.serial_number, "component_code": serial.component_code,
        "order_id": str(ticket.order_id), "repeat_key": repeat_key,
    }
    if exception is not None:
        verdict = exception.decision
        reason = (f"Manager-approved exception {exception.id} decides "
                  f"{verdict}: {exception.reason}")
        decision = _store(db, user, ticket, serial, None, None, None, None, category,
                          ticket.fault_code, at, verdict, reason, evidence, digest,
                          idempotency_key)
        return decision, True
    if coverage is None:
        decision = _store(db, user, ticket, serial, None, None, None, None, category,
                          ticket.fault_code, at, "blocked",
                          "No coverage record exists for this unit. Activate coverages "
                          "from the confirmed delivery first.", evidence, digest,
                          idempotency_key)
        return decision, True
    while coverage.status == "superseded" and coverage.replaced_by_serial_id is not None:
        replacement = db.scalar(
            select(SerializedAssetCoverage).where(
                SerializedAssetCoverage.serial_id == coverage.replaced_by_serial_id)
        )
        if replacement is None:
            break
        coverage = replacement
    evidence["coverage_id"] = str(coverage.id)
    if coverage.status == "void":
        decision = _store(db, user, ticket, serial, version, coverage, None, None,
                          category, ticket.fault_code, at, "not_covered",
                          f"Coverage was voided: {coverage.void_reason or 'no reason recorded'}.",
                          evidence, digest, idempotency_key)
        return decision, True
    if version is None:
        decision = _store(db, user, ticket, serial, None, coverage, None, None,
                          category, ticket.fault_code, at, "pending_verification",
                          "No policy version applies to this component at the evaluation "
                          "timestamp. A policy owner must review it.", evidence, digest,
                          idempotency_key)
        return decision, True
    if at > _as_utc(coverage.ends_at):
        decision = _store(db, user, ticket, serial, version, coverage,
                          _snapshot_version(version), _snapshot_coverage(coverage),
                          category, ticket.fault_code, at, "not_covered",
                          f"Coverage ended on {coverage.ends_at.date().isoformat()}; the "
                          f"evaluation date is past the boundary.", evidence, digest,
                          idempotency_key)
        return decision, True
    if category is None:
        decision = _store(db, user, ticket, serial, version, coverage,
                          _snapshot_version(version), _snapshot_coverage(coverage),
                          category, ticket.fault_code, at, "pending_verification",
                          "No fault category is classified yet. Triage the ticket before "
                          "a coverage verdict.", evidence, digest, idempotency_key)
        return decision, True
    exclusions = version.exclusions or {}
    if category in (exclusions.get("fault_categories") or []):
        decision = _store(db, user, ticket, serial, version, coverage,
                          _snapshot_version(version), _snapshot_coverage(coverage),
                          category, ticket.fault_code, at, "not_covered",
                          f"Fault category {category} is excluded by policy version "
                          f"{version.version_number}.", evidence, digest, idempotency_key)
        return decision, True
    if category not in (version.covered_fault_categories or []):
        decision = _store(db, user, ticket, serial, version, coverage,
                          _snapshot_version(version), _snapshot_coverage(coverage),
                          category, ticket.fault_code, at, "not_covered",
                          f"Fault category {category} is not in the covered list of policy "
                          f"version {version.version_number}.", evidence, digest,
                          idempotency_key)
        return decision, True
    decision = _store(db, user, ticket, serial, version, coverage,
                      _snapshot_version(version), _snapshot_coverage(coverage),
                      category, ticket.fault_code, at, "covered",
                      f"Unit is within coverage until {coverage.ends_at.date().isoformat()} "
                      f"under policy version {version.version_number}; the fault category "
                      f"is covered and not excluded.", evidence, digest, idempotency_key)
    return decision, True


def _store(db: Session, user: User, ticket: ServiceTicket, serial: EquipmentSerial,
           version: WarrantyPolicyVersion | None, coverage: SerializedAssetCoverage | None,
           policy_snapshot: dict | None, coverage_snapshot: dict | None,
           category: str | None, fault_code: str | None, at: datetime, verdict: str,
           reason: str, evidence: dict, digest: str, idempotency_key: str) -> CoverageDecision:
    decision = CoverageDecision(
        ticket_id=ticket.id, serial_id=serial.id,
        policy_version_id=version.id if version else None,
        coverage_id=coverage.id if coverage else None,
        policy_snapshot=policy_snapshot, coverage_snapshot=coverage_snapshot,
        fault_category=category, fault_code=fault_code, evaluated_at=at,
        verdict=verdict, reason=reason, evidence=evidence,
        decided_by_user_id=user.id, idempotency_key=idempotency_key, request_hash=digest,
    )
    db.add(decision)
    db.flush()
    db.add(
        ServiceTicketEvent(
            ticket_id=ticket.id, from_status=ticket.status, to_status=None,
            actor_user_id=user.id, action="coverage_decided", reason=reason,
            evidence={"decision_id": str(decision.id), "verdict": verdict,
                      "serial_number": serial.serial_number},
        )
    )
    add_audit(db, actor_user_id=user.id, action="warranty.coverage_decided",
              entity_type="coverage_decision", entity_id=decision.id,
              metadata={"ticket_id": str(ticket.id), "verdict": verdict})
    db.flush()
    return decision


def create_exception(db: Session, user: User, ticket_id: uuid.UUID, serial_number: str,
                     decision: str, reason: str,
                     evidence_ref: str | None) -> WarrantyException:
    _require_roles(user, ADMIN)
    if decision not in ("covered", "not_covered"):
        raise AppError(422, "validation_error", "Exception decision must be covered or not_covered.")
    if len(reason.strip()) < 10:
        raise AppError(422, "validation_error", "An exception needs a real recorded reason.")
    ticket, serial = _ticket_serial(db, ticket_id, serial_number)
    existing = db.scalar(
        select(WarrantyException).where(
            WarrantyException.ticket_id == ticket.id,
            WarrantyException.serial_id == serial.id)
    )
    if existing is not None:
        raise AppError(409, "exception_exists",
                       "An exception already exists for this ticket and unit.")
    row = WarrantyException(
        ticket_id=ticket.id, serial_id=serial.id, decision=decision,
        reason=reason.strip(), evidence_ref=(evidence_ref or None),
        decided_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    add_audit(db, actor_user_id=user.id, action="warranty.exception_created",
              entity_type="warranty_exception", entity_id=row.id,
              metadata={"ticket_id": str(ticket.id), "decision": decision})
    db.flush()
    return row


def void_coverage(db: Session, user: User, coverage_id: uuid.UUID,
                  reason: str) -> SerializedAssetCoverage:
    _require_roles(user, SUPPORT)
    if len(reason.strip()) < 10:
        raise AppError(422, "validation_error", "Voiding coverage needs a recorded reason.")
    coverage = db.get(SerializedAssetCoverage, coverage_id)
    if coverage is None:
        raise AppError(404, "not_found", "Coverage record not found.")
    if coverage.status == "void":
        raise AppError(409, "invalid_transition", "This coverage is already void.")
    coverage.status = "void"
    coverage.void_reason = reason.strip()
    db.flush()
    add_audit(db, actor_user_id=user.id, action="warranty.coverage_voided",
              entity_type="serialized_asset_coverage", entity_id=coverage.id,
              metadata={"reason": coverage.void_reason})
    db.flush()
    return coverage


def my_coverages(db: Session, user: User) -> list[dict]:
    _require_roles(user, {CUSTOMER})
    rows = list(
        db.scalars(
            select(SerializedAssetCoverage)
            .where(SerializedAssetCoverage.customer_user_id == user.id)
            .order_by(SerializedAssetCoverage.ends_at.desc())
        ).all()
    )
    result = []
    for coverage in rows:
        serial = db.get(EquipmentSerial, coverage.serial_id)
        version = db.get(WarrantyPolicyVersion, coverage.policy_version_id)
        policy = db.get(WarrantyPolicy, version.policy_id) if version else None
        result.append({
            "coverage_id": coverage.id, "serial_number": serial.serial_number if serial else None,
            "component_code": serial.component_code if serial else None,
            "policy_code": policy.code if policy else None,
            "policy_version": version.version_number if version else None,
            "status": coverage.status, "starts_at": coverage.starts_at,
            "ends_at": coverage.ends_at, "order_id": coverage.order_id,
        })
    return result


def lookup_serial(db: Session, user: User, serial_number: str) -> dict:
    _require_roles(user, SUPPORT)
    serial = db.scalar(
        select(EquipmentSerial).where(
            func.lower(EquipmentSerial.serial_number) == serial_number.strip().lower())
    )
    if serial is None:
        raise AppError(404, "not_found", "Equipment serial not found.")
    coverage = db.scalar(
        select(SerializedAssetCoverage).where(
            SerializedAssetCoverage.serial_id == serial.id)
    )
    decisions = list(
        db.scalars(
            select(CoverageDecision)
            .where(CoverageDecision.serial_id == serial.id)
            .order_by(CoverageDecision.created_at.desc())
        ).all()
    )
    order = db.get(SalesOrder, serial.order_id) if serial.order_id else None
    return {
        "serial_number": serial.serial_number, "component_code": serial.component_code,
        "status": serial.status, "order_id": serial.order_id,
        "customer_user_id": order.customer_user_id if order else None,
        "coverage": ({
            "coverage_id": coverage.id, "status": coverage.status,
            "starts_at": coverage.starts_at, "ends_at": coverage.ends_at,
            "policy_version_id": coverage.policy_version_id,
        } if coverage else None),
        "decisions": [{
            "decision_id": item.id, "ticket_id": item.ticket_id,
            "verdict": item.verdict, "reason": item.reason,
            "evaluated_at": item.evaluated_at,
        } for item in decisions],
    }


def ticket_decisions(db: Session, user: User,
                     ticket_id: uuid.UUID) -> list[CoverageDecision]:
    ticket = db.get(ServiceTicket, ticket_id)
    if ticket is None:
        raise AppError(404, "not_found", "Ticket not found.")
    if user.role_code in SUPPORT:
        pass
    elif user.role_code == CUSTOMER and ticket.customer_user_id == user.id:
        pass
    else:
        raise AppError(404, "not_found", "Ticket not found.")
    return list(
        db.scalars(
            select(CoverageDecision)
            .where(CoverageDecision.ticket_id == ticket.id)
            .order_by(CoverageDecision.created_at)
        ).all()
    )
