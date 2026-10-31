"""Warranty-aware equipment replacement with real warehouse custody.

A defective installed unit is swapped for a warehouse unit through explicit,
role-checked steps: propose, approve (with manufacturer evidence when the
policy requires it), reserve, issue through a validated delivery operation,
install confirmation, and inspected return of the defective unit. Every serial
transition is validated, the new unit gets transferred coverage, and the old
unit's history is preserved. Nothing here invents manufacturer authorization
or silently corrects inventory.
"""

import hashlib
import json
import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import utcnow
from app.models.identity import User
from app.models.phase3 import EquipmentSerial
from app.models.support import (
    ResolutionAcknowledgment,
    ServiceTicket,
    ServiceTicketAttachment,
    ServiceTicketEvent,
    TicketRepairJob,
)
from app.models.warranty import (
    CoverageDecision,
    ReplacementDecision,
    ReturnInspection,
    SerializedAssetCoverage,
)
from app.repositories.queries import add_audit
from app.services import inventory_service
from app.services.references import next_reference

SUPPORT = {"support", "admin"}
WAREHOUSE = {"warehouse_staff", "warehouse_manager", "admin"}
TECHNICIAN = "technician"


def _digest(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _require_roles(user: User, allowed: set[str]) -> None:
    if user.role_code not in allowed:
        raise AppError(403, "forbidden", "You do not have access to this action.")


def _serial_or_404(db: Session, serial_number: str) -> EquipmentSerial:
    serial = db.scalar(
        select(EquipmentSerial).where(
            func.lower(EquipmentSerial.serial_number) == serial_number.strip().lower())
    )
    if serial is None:
        raise AppError(404, "not_found", "Equipment serial not found.")
    return serial


def _lock_replacement(db: Session, replacement_id: uuid.UUID) -> ReplacementDecision:
    row = db.scalar(
        select(ReplacementDecision)
        .where(ReplacementDecision.id == replacement_id)
        .with_for_update()
    )
    if row is None:
        raise AppError(404, "not_found", "Replacement decision not found.")
    return row


def _record(db: Session, user: User, ticket: ServiceTicket, action: str,
            reason: str | None, evidence: dict | None = None) -> None:
    db.add(
        ServiceTicketEvent(
            ticket_id=ticket.id, from_status=ticket.status, to_status=None,
            actor_user_id=user.id, action=action, reason=reason, evidence=evidence,
        )
    )
    ticket.updated_at = utcnow()
    add_audit(db, actor_user_id=user.id, action=f"replacement.{action}",
              entity_type="replacement_decision",
              entity_id=evidence.get("replacement_id") if evidence else None,
              metadata=evidence or {})
    db.flush()


def _latest_decision(db: Session, ticket_id: uuid.UUID) -> CoverageDecision:
    decision = db.scalar(
        select(CoverageDecision)
        .where(CoverageDecision.ticket_id == ticket_id)
        .order_by(CoverageDecision.created_at.desc())
    )
    if decision is None:
        raise AppError(409, "coverage_decision_required",
                       "Record a coverage decision for this ticket first.")
    return decision


def propose_replacement(db: Session, user: User, ticket_id: uuid.UUID, old_serial: str,
                        new_serial: str, idempotency_key: str) -> tuple[ReplacementDecision, bool]:
    _require_roles(user, SUPPORT)
    ticket = db.get(ServiceTicket, ticket_id)
    if ticket is None:
        raise AppError(404, "not_found", "Ticket not found.")
    old = _serial_or_404(db, old_serial)
    new = _serial_or_404(db, new_serial)
    if old.order_id != ticket.order_id or old.status != "installed":
        raise AppError(404, "not_found", "Original unit not found installed on this order.")
    if new.status != "in_stock":
        raise AppError(409, "replacement_unavailable",
                       "The replacement unit is not available in stock.")
    if new.component_code != old.component_code:
        raise AppError(422, "validation_error",
                       "The replacement unit must be the same component.")
    decision = _latest_decision(db, ticket.id)
    snapshot = decision.policy_snapshot or {}
    if not snapshot.get("replacement_allowed", False):
        raise AppError(409, "replacement_not_allowed",
                       "The applicable policy does not allow replacement.")
    digest = _digest({"ticket_id": str(ticket.id), "old_serial_id": str(old.id),
                      "new_serial_id": str(new.id)})
    existing = db.scalar(
        select(ReplacementDecision).where(
            ReplacementDecision.ticket_id == ticket.id,
            ReplacementDecision.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.request_hash != digest:
            raise AppError(409, "idempotency_conflict",
                           "This Idempotency-Key was already used for a different replacement.")
        return existing, False
    prior = db.scalar(
        select(ReplacementDecision).where(
            ReplacementDecision.old_serial_id == old.id,
            ReplacementDecision.status != "cancelled",
        )
    )
    if prior is not None and not snapshot.get("repeat_replacement_allowed", False):
        raise AppError(409, "replacement_exists",
                       "This unit already has an active replacement.")
    row = ReplacementDecision(
        reference=next_reference(db, "replacement", "RPL"),
        ticket_id=ticket.id, coverage_decision_id=decision.id,
        old_serial_id=old.id, new_serial_id=new.id,
        status="proposed",
        manufacturer_status=("pending" if snapshot.get("manufacturer_auth_required", False)
                             else "not_required"),
        idempotency_key=idempotency_key, request_hash=digest,
        created_by_user_id=user.id,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "replacement_exists",
                       "This replacement unit is already assigned elsewhere.") from exc
    _record(db, user, ticket, "replacement_proposed", None,
            {"replacement_id": str(row.id), "old_serial": old.serial_number,
             "new_serial": new.serial_number})
    return row, True


def approve_replacement(db: Session, user: User,
                        replacement_id: uuid.UUID) -> ReplacementDecision:
    _require_roles(user, SUPPORT)
    row = _lock_replacement(db, replacement_id)
    if row.status != "proposed":
        raise AppError(409, "invalid_transition", "Only a proposed replacement can be approved.")
    ticket = db.get(ServiceTicket, row.ticket_id)
    assert ticket is not None
    old = db.get(EquipmentSerial, row.old_serial_id)
    assert old is not None
    if old.status != "installed":
        raise AppError(409, "replacement_unavailable",
                       "The original unit is no longer installed.")
    row.status = "pending_manufacturer" if row.manufacturer_status == "pending" else "approved"
    row.approved_by_user_id = user.id
    old.status = "faulty"
    db.flush()
    _record(db, user, ticket, "replacement_approved", None,
            {"replacement_id": str(row.id), "manufacturer_status": row.manufacturer_status})
    return row


def record_manufacturer_auth(db: Session, user: User, replacement_id: uuid.UUID,
                             evidence_ref: str) -> ReplacementDecision:
    _require_roles(user, SUPPORT)
    if len((evidence_ref or "").strip()) < 3:
        raise AppError(422, "validation_error",
                       "Manufacturer authorization needs recorded evidence.")
    row = _lock_replacement(db, replacement_id)
    if row.manufacturer_status != "pending" or row.status != "pending_manufacturer":
        raise AppError(409, "invalid_transition",
                       "This replacement is not waiting on manufacturer authorization.")
    ticket = db.get(ServiceTicket, row.ticket_id)
    assert ticket is not None
    row.manufacturer_status = "approved"
    row.manufacturer_evidence_ref = evidence_ref.strip()
    row.status = "approved"
    db.flush()
    _record(db, user, ticket, "manufacturer_authorized", evidence_ref.strip(),
            {"replacement_id": str(row.id)})
    return row


def reserve_replacement(db: Session, user: User,
                        replacement_id: uuid.UUID) -> ReplacementDecision:
    _require_roles(user, WAREHOUSE)
    row = _lock_replacement(db, replacement_id)
    if row.status != "approved":
        raise AppError(409, "invalid_transition",
                       "Only an approved replacement can be reserved.")
    ticket = db.get(ServiceTicket, row.ticket_id)
    assert ticket is not None
    peek = db.get(EquipmentSerial, row.new_serial_id)
    assert peek is not None
    inventory_service.lock_components(db, [peek.component_code])
    new = db.scalar(select(EquipmentSerial).where(EquipmentSerial.id == row.new_serial_id)
                    .with_for_update().execution_options(populate_existing=True))
    assert new is not None
    if new.status == "reserved" and new.order_id == ticket.order_id:
        return row
    if new.status != "in_stock":
        raise AppError(409, "replacement_unavailable",
                       "The replacement unit left stock while waiting.")
    new.status = "reserved"
    new.order_id = ticket.order_id
    db.flush()
    _record(db, user, ticket, "replacement_reserved", None,
            {"replacement_id": str(row.id), "new_serial": new.serial_number})
    return row


def issue_replacement(db: Session, user: User, replacement_id: uuid.UUID,
                      idempotency_key: str) -> ReplacementDecision:
    _require_roles(user, WAREHOUSE)
    row = _lock_replacement(db, replacement_id)
    if row.status == "issued" and row.issue_operation_id is not None:
        return row
    if row.status != "approved":
        raise AppError(409, "invalid_transition",
                       "Only an approved replacement can be issued.")
    ticket = db.get(ServiceTicket, row.ticket_id)
    assert ticket is not None
    new = db.get(EquipmentSerial, row.new_serial_id)
    old = db.get(EquipmentSerial, row.old_serial_id)
    assert new is not None and old is not None
    if new.status != "reserved" or new.order_id != ticket.order_id:
        raise AppError(409, "replacement_unavailable",
                       "Reserve the replacement unit for this order first.")
    operation = inventory_service.replacement_stock_movement(db, user, row.id)
    row.issue_operation_id = operation.id
    row.status = "issued"
    db.flush()
    _record(db, user, ticket, "replacement_issued", None,
            {"replacement_id": str(row.id), "operation_id": str(operation.id),
             "new_serial": new.serial_number, "old_serial": old.serial_number})
    return row


def _activate_replacement_coverage(db, row, ticket, old, new):
    now = utcnow()
    new.status = "installed"
    new.location_code = None
    old.status = "faulty"
    old.location_code = None
    old_coverage = db.scalar(
        select(SerializedAssetCoverage).where(
            SerializedAssetCoverage.serial_id == old.id)
    )
    decision = db.get(CoverageDecision, row.coverage_decision_id)
    snapshot = (decision.policy_snapshot or {}) if decision else {}
    if snapshot.get("replacement_continuation") == "fixed_days":
        ends_at = now + timedelta(days=snapshot.get("replacement_warranty_days") or 0)
    elif old_coverage is not None:
        ends_at = old_coverage.ends_at
    else:
        ends_at = now
    new_coverage = SerializedAssetCoverage(
        serial_id=new.id, policy_version_id=decision.policy_version_id if decision else None,
        order_id=ticket.order_id, customer_user_id=ticket.customer_user_id,
        site_id=ticket.site_id, delivery_id=(old_coverage.delivery_id if old_coverage else None),
        activated_at=now, starts_at=now, ends_at=ends_at, status="active",
        supersedes_coverage_id=old_coverage.id if old_coverage else None,
    ) if (decision and decision.policy_version_id and old_coverage) else None
    if old_coverage is not None:
        old_coverage.status = "superseded"
        old_coverage.replaced_by_serial_id = new.id
    if new_coverage is not None:
        db.add(new_coverage)
    db.flush()


def confirm_install(db: Session, user: User,
                    replacement_id: uuid.UUID) -> ReplacementDecision:
    row = _lock_replacement(db, replacement_id)
    ticket = db.get(ServiceTicket, row.ticket_id)
    assert ticket is not None
    if user.role_code == TECHNICIAN:
        job = db.scalar(
            select(TicketRepairJob).where(
                TicketRepairJob.ticket_id == ticket.id,
                TicketRepairJob.technician_user_id == user.id,
            )
        )
        if job is None:
            raise AppError(404, "not_found", "Replacement decision not found.")
    else:
        _require_roles(user, SUPPORT)
    if row.status != "issued":
        raise AppError(409, "invalid_transition",
                       "Only an issued replacement can be confirmed installed.")
    ticket = db.scalar(select(ServiceTicket).where(ServiceTicket.id == ticket.id).with_for_update())
    summary = ticket.resolution_summary or {}
    job = db.get(TicketRepairJob, uuid.UUID(summary["repair_job_id"])) if summary.get("repair_job_id") else None
    acknowledgment = db.scalar(select(ResolutionAcknowledgment).where(
        ResolutionAcknowledgment.ticket_id == ticket.id,
        ResolutionAcknowledgment.summary_version == ticket.resolution_version,
        ResolutionAcknowledgment.decision == "confirmed",
        ResolutionAcknowledgment.customer_user_id == ticket.customer_user_id,
    ))
    evidence = db.scalar(select(ServiceTicketAttachment.id).where(
        ServiceTicketAttachment.ticket_id == ticket.id,
        ServiceTicketAttachment.repair_job_id == job.id,
    )) if job else None
    if (job is None or job.status != "work_submitted" or not job.work_performed
            or not job.work_finished_at or not evidence or acknowledgment is None
            or ticket.status not in {"customer_confirmed", "closed"}):
        raise AppError(409, "installation_evidence_required",
                       "Submit assigned repair work and evidence, then obtain customer acknowledgment.")
    if user.role_code == TECHNICIAN and job.technician_user_id != user.id:
        raise AppError(404, "not_found", "Replacement decision not found.")
    old = db.scalar(select(EquipmentSerial).where(EquipmentSerial.id == row.old_serial_id)
                    .with_for_update())
    new = db.scalar(select(EquipmentSerial).where(EquipmentSerial.id == row.new_serial_id)
                    .with_for_update())
    if new is None or old is None or new.status != "in_transit" or old.status != "faulty":
        raise AppError(409, "invalid_serial_state", "Replacement custody changed before installation.")
    from app.models.phase3 import StockOperation
    from app.services.ticket_service import resolution_payload

    operation = db.get(StockOperation, row.issue_operation_id)
    if (operation is None or operation.status != "done" or not operation.validated_at
            or job.work_finished_at < operation.validated_at
            or old.serial_number not in job.work_performed.upper()
            or new.serial_number not in job.work_performed.upper()
            or acknowledgment.repair_job_id != job.id
            or acknowledgment.payload_hash != resolution_payload(ticket)["payload_hash"]):
        raise AppError(409, "installation_evidence_required",
                       "Acknowledged work must identify the exact issued replacement and original unit.")
    _activate_replacement_coverage(db, row, ticket, old, new)
    row.status = "installed"
    db.flush()
    _record(db, user, ticket, "replacement_installed", None,
            {"replacement_id": str(row.id)})
    return row


def cancel_replacement(db: Session, user: User, replacement_id: uuid.UUID,
                       reason: str) -> ReplacementDecision:
    _require_roles(user, SUPPORT)
    if len(reason.strip()) < 3:
        raise AppError(422, "validation_error", "Cancelling needs a reason.")
    row = _lock_replacement(db, replacement_id)
    if row.status not in ("proposed", "approved", "pending_manufacturer"):
        raise AppError(409, "invalid_transition",
                       "This replacement can no longer be cancelled.")
    ticket = db.get(ServiceTicket, row.ticket_id)
    assert ticket is not None
    new = db.get(EquipmentSerial, row.new_serial_id)
    assert new is not None
    if new.status == "reserved":
        new.status = "in_stock"
        new.order_id = None
    row.status = "cancelled"
    db.flush()
    _record(db, user, ticket, "replacement_cancelled", reason.strip(),
            {"replacement_id": str(row.id)})
    return row


def inspect_return(db: Session, user: User, replacement_id: uuid.UUID, verdict: str,
                   note: str) -> ReturnInspection:
    _require_roles(user, WAREHOUSE)
    if verdict not in ("quarantined", "restocked", "scrapped"):
        raise AppError(422, "validation_error", "Unknown inspection verdict.")
    if len(note.strip()) < 10:
        raise AppError(422, "validation_error", "Inspection needs a real recorded note.")
    row = _lock_replacement(db, replacement_id)
    if row.status != "installed":
        raise AppError(409, "invalid_transition",
                       "The defective unit has not been returned yet.")
    existing = db.scalar(
        select(ReturnInspection).where(ReturnInspection.replacement_id == row.id)
    )
    if existing is not None:
        raise AppError(409, "inspection_exists", "This return was already inspected.")
    ticket = db.get(ServiceTicket, row.ticket_id)
    assert ticket is not None
    old = db.scalar(select(EquipmentSerial).where(EquipmentSerial.id == row.old_serial_id)
                    .with_for_update())
    assert old is not None
    if old.status != "faulty":
        raise AppError(409, "invalid_transition", "The defective unit is not in returns.")
    # This explicit warehouse inspection records physical receipt of the
    # defective unit; dispatching its replacement never implies a return.
    old.status = "returned"
    old.location_code = "MAIN"
    db.flush()
    operation = inventory_service.replacement_stock_movement(
        db, user, row.id, return_verdict=verdict)
    # All physical returns, including unusable quarantine/scrap custody, have
    # an exact serialized receipt and ledger record at their actual location.
    restock_operation_id = operation.id
    inspection = ReturnInspection(
        replacement_id=row.id, serial_id=old.id, verdict=verdict, note=note.strip(),
        restock_operation_id=restock_operation_id, inspected_by_user_id=user.id,
    )
    db.add(inspection)
    db.flush()
    _record(db, user, ticket, "return_inspected", note.strip(),
            {"replacement_id": str(row.id), "verdict": verdict,
             "old_serial": old.serial_number})
    return inspection


def list_replacements(db: Session, user: User,
                      ticket_id: uuid.UUID | None) -> list[ReplacementDecision]:
    statement = select(ReplacementDecision).order_by(ReplacementDecision.created_at.desc())
    if user.role_code in SUPPORT or user.role_code in WAREHOUSE:
        pass
    elif user.role_code == TECHNICIAN:
        statement = statement.where(
            ReplacementDecision.ticket_id.in_(
                select(TicketRepairJob.ticket_id).where(
                    TicketRepairJob.technician_user_id == user.id)
            )
        )
    elif user.role_code == "customer":
        statement = statement.where(
            ReplacementDecision.ticket_id.in_(
                select(ServiceTicket.id).where(ServiceTicket.customer_user_id == user.id)
            )
        )
    else:
        _require_roles(user, SUPPORT)
    if ticket_id is not None:
        ticket = db.get(ServiceTicket, ticket_id)
        if ticket is None:
            raise AppError(404, "not_found", "Ticket not found.")
        if user.role_code == "customer" and ticket.customer_user_id != user.id:
            raise AppError(404, "not_found", "Ticket not found.")
        statement = statement.where(ReplacementDecision.ticket_id == ticket_id)
    return list(db.scalars(statement).all())


def get_replacement(db: Session, user: User,
                    replacement_id: uuid.UUID) -> ReplacementDecision:
    row = db.get(ReplacementDecision, replacement_id)
    if row is None:
        raise AppError(404, "not_found", "Replacement decision not found.")
    ticket = db.get(ServiceTicket, row.ticket_id)
    assert ticket is not None
    if user.role_code in SUPPORT or user.role_code in WAREHOUSE:
        return row
    if user.role_code == "customer" and ticket.customer_user_id == user.id:
        return row
    if user.role_code == TECHNICIAN:
        job = db.scalar(
            select(TicketRepairJob).where(
                TicketRepairJob.ticket_id == ticket.id,
                TicketRepairJob.technician_user_id == user.id)
        )
        if job is not None:
            return row
    raise AppError(404, "not_found", "Replacement decision not found.")
