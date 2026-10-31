"""Customer complaint to confirmed resolution.

A ticket always references the owning customer's confirmed order and, when a
unit is named, one installed serial from that order. Ownership is checked
inside every function: another customer's id answers 404 so existence never
leaks. Every status change locks the ticket row, validates the transition
table in ``app.models.support``, and writes a history event plus an audit row
in the same transaction. A support employee can never confirm a resolution:
confirmation requires the owning customer's session and binds the exact
resolution version and payload hash.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import utcnow
from app.models.enquiry import CustomerSite
from app.models.identity import User
from app.models.support import (
    TICKET_TRANSITIONS,
    ResolutionAcknowledgment,
    ServiceTicket,
    ServiceTicketAttachment,
    ServiceTicketEvent,
    TicketRepairJob,
)
from app.models.workflow import SalesOrder
from app.repositories.queries import add_audit
from app.services.references import next_reference

CUSTOMER = "customer"
SUPPORT = {"support", "admin"}
TECHNICIAN = "technician"
OPEN_REPAIR_STATUSES = ("assigned", "in_progress")
REPAIR_JOB_CAP = 5


def _digest(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _require_roles(user: User, allowed: set[str]) -> None:
    if user.role_code not in allowed:
        raise AppError(403, "forbidden", "You do not have access to this action.")


def _lock_ticket(db: Session, ticket_id: uuid.UUID) -> ServiceTicket:
    ticket = db.scalar(
        select(ServiceTicket).where(ServiceTicket.id == ticket_id).with_for_update()
    )
    if ticket is None:
        raise AppError(404, "not_found", "Ticket not found.")
    return ticket


def _visible_ticket(db: Session, user: User, ticket_id: uuid.UUID) -> ServiceTicket:
    ticket = db.get(ServiceTicket, ticket_id)
    if ticket is None:
        raise AppError(404, "not_found", "Ticket not found.")
    if user.role_code in SUPPORT:
        return ticket
    if user.role_code == CUSTOMER and ticket.customer_user_id == user.id:
        return ticket
    if user.role_code == TECHNICIAN:
        job = db.scalar(
            select(TicketRepairJob).where(
                TicketRepairJob.ticket_id == ticket.id,
                TicketRepairJob.technician_user_id == user.id,
            )
        )
        if job is not None:
            return ticket
    raise AppError(404, "not_found", "Ticket not found.")


def _move(
    db: Session,
    user: User,
    ticket: ServiceTicket,
    to_status: str,
    action: str,
    reason: str | None = None,
    evidence: dict | None = None,
) -> None:
    allowed = TICKET_TRANSITIONS.get(ticket.status, ())
    if to_status not in allowed:
        raise AppError(
            409,
            "invalid_transition",
            f"A ticket cannot move from {ticket.status} to {to_status}.",
        )
    event = ServiceTicketEvent(
        ticket_id=ticket.id,
        from_status=ticket.status,
        to_status=to_status,
        actor_user_id=user.id,
        action=action,
        reason=reason,
        evidence=evidence,
    )
    db.add(event)
    ticket.status = to_status
    ticket.updated_at = utcnow()
    add_audit(
        db,
        actor_user_id=user.id,
        action=f"ticket.{action}",
        entity_type="service_ticket",
        entity_id=ticket.id,
        metadata={"from": event.from_status, "to": to_status},
    )
    db.flush()


def _record(
    db: Session,
    user: User,
    ticket: ServiceTicket,
    action: str,
    reason: str | None = None,
    evidence: dict | None = None,
) -> None:
    db.add(
        ServiceTicketEvent(
            ticket_id=ticket.id,
            from_status=ticket.status,
            to_status=None,
            actor_user_id=user.id,
            action=action,
            reason=reason,
            evidence=evidence,
        )
    )
    ticket.updated_at = utcnow()
    add_audit(
        db,
        actor_user_id=user.id,
        action=f"ticket.{action}",
        entity_type="service_ticket",
        entity_id=ticket.id,
        metadata=evidence or {},
    )
    db.flush()


def create_ticket(
    db: Session,
    user: User,
    payload: dict,
    idempotency_key: str,
) -> tuple[ServiceTicket, bool]:
    from app.models.phase3 import EquipmentSerial

    _require_roles(user, {CUSTOMER})
    order_id = payload["order_id"]
    order = db.get(SalesOrder, order_id)
    if order is None or order.customer_user_id != user.id:
        raise AppError(404, "not_found", "Order not found.")
    site_id = payload.get("site_id")
    if site_id is not None:
        site = db.scalar(
            select(CustomerSite).where(
                CustomerSite.id == site_id, CustomerSite.customer_user_id == user.id
            )
        )
        if site is None:
            raise AppError(404, "not_found", "Site not found.")
    serial = None
    serial_number = (payload.get("serial_number") or "").strip()
    if serial_number:
        serial = db.scalar(
            select(EquipmentSerial).where(
                func.lower(EquipmentSerial.serial_number) == serial_number.lower()
            )
        )
        if serial is None or serial.order_id != order.id:
            raise AppError(404, "not_found", "Equipment serial not found on this order.")
        if serial.status != "installed":
            raise AppError(
                409,
                "serial_not_installed",
                "Only installed equipment can be reported for repair.",
            )
    digest = _digest(
        {
            "order_id": str(order_id),
            "site_id": str(site_id) if site_id else None,
            "serial_number": serial_number or None,
            "fault_code": payload.get("fault_code"),
            "symptoms": payload["symptoms"],
            "customer_urgency": payload["customer_urgency"],
            "contact_preference": payload["contact_preference"],
        }
    )
    existing = db.scalar(
        select(ServiceTicket).where(
            ServiceTicket.customer_user_id == user.id,
            ServiceTicket.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.request_hash != digest:
            raise AppError(
                409,
                "idempotency_conflict",
                "This Idempotency-Key was already used for a different complaint.",
            )
        return existing, False
    ticket = ServiceTicket(
        reference=next_reference(db, "ticket", "TKT"),
        customer_user_id=user.id,
        site_id=site_id,
        order_id=order.id,
        serial_id=serial.id if serial else None,
        fault_code=(payload.get("fault_code") or None),
        symptoms=payload["symptoms"],
        customer_urgency=payload["customer_urgency"],
        contact_preference=payload["contact_preference"],
        status="open",
        idempotency_key=idempotency_key,
        request_hash=digest,
    )
    db.add(ticket)
    db.flush()
    db.add(
        ServiceTicketEvent(
            ticket_id=ticket.id,
            from_status=None,
            to_status="open",
            actor_user_id=user.id,
            action="created",
            reason=None,
            evidence={"order_id": str(order.id)},
        )
    )
    add_audit(
        db,
        actor_user_id=user.id,
        action="ticket.created",
        entity_type="service_ticket",
        entity_id=ticket.id,
        metadata={"reference": ticket.reference},
    )
    db.flush()
    return ticket, True


def list_tickets(
    db: Session, user: User, status: str | None, page: int, page_size: int
) -> tuple[list[ServiceTicket], int]:
    statement = select(ServiceTicket).order_by(ServiceTicket.created_at.desc())
    if user.role_code == CUSTOMER:
        statement = statement.where(ServiceTicket.customer_user_id == user.id)
    elif user.role_code == TECHNICIAN:
        statement = statement.where(
            ServiceTicket.id.in_(
                select(TicketRepairJob.ticket_id).where(
                    TicketRepairJob.technician_user_id == user.id
                )
            )
        )
    elif user.role_code not in SUPPORT:
        raise AppError(403, "forbidden", "You do not have access to tickets.")
    if status is not None:
        statement = statement.where(ServiceTicket.status == status)
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = list(
        db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all()
    )
    return rows, total


def get_ticket(db: Session, user: User, ticket_id: uuid.UUID) -> ServiceTicket:
    return _visible_ticket(db, user, ticket_id)


def triage_ticket(
    db: Session, user: User, ticket_id: uuid.UUID, category: str, priority: str, note: str
) -> ServiceTicket:
    _require_roles(user, SUPPORT)
    ticket = _lock_ticket(db, ticket_id)
    ticket.category = category
    ticket.verified_priority = priority
    _move(db, user, ticket, "triaged", "triaged", note,
          {"category": category, "verified_priority": priority})
    return ticket


def assign_support_owner(
    db: Session, user: User, ticket_id: uuid.UUID, support_user_id: uuid.UUID,
    note: str | None,
) -> ServiceTicket:
    _require_roles(user, SUPPORT)
    ticket = _lock_ticket(db, ticket_id)
    owner = db.get(User, support_user_id)
    if owner is None or owner.role_code not in SUPPORT or not owner.is_active:
        raise AppError(404, "not_found", "Support owner not found.")
    ticket.assigned_support_user_id = owner.id
    if ticket.status == "triaged":
        _move(db, user, ticket, "assigned", "support_assigned", note,
              {"support_user_id": str(owner.id)})
    else:
        _record(db, user, ticket, "support_assigned", note,
                {"support_user_id": str(owner.id)})
    return ticket


def request_info(
    db: Session, user: User, ticket_id: uuid.UUID, message: str
) -> ServiceTicket:
    _require_roles(user, SUPPORT)
    ticket = _lock_ticket(db, ticket_id)
    _move(db, user, ticket, "waiting_customer", "info_requested", message,
          {"return_to": ticket.status})
    return ticket


def customer_reply(
    db: Session, user: User, ticket_id: uuid.UUID, message: str
) -> ServiceTicket:
    _require_roles(user, {CUSTOMER})
    ticket = _lock_ticket(db, ticket_id)
    if ticket.customer_user_id != user.id:
        raise AppError(404, "not_found", "Ticket not found.")
    if ticket.status != "waiting_customer":
        raise AppError(409, "invalid_transition", "This ticket is not waiting on you.")
    last_request = db.scalar(
        select(ServiceTicketEvent)
        .where(ServiceTicketEvent.ticket_id == ticket.id,
               ServiceTicketEvent.action == "info_requested")
        .order_by(ServiceTicketEvent.created_at.desc())
    )
    target = "in_progress"
    if last_request and last_request.evidence:
        candidate = last_request.evidence.get("return_to")
        if candidate in TICKET_TRANSITIONS.get("waiting_customer", ()):
            target = candidate
    _move(db, user, ticket, target, "customer_replied", message)
    return ticket


def _check_technician(db: Session, technician_user_id: uuid.UUID) -> User:
    technician = db.get(User, technician_user_id)
    if technician is None or technician.role_code != TECHNICIAN or not technician.is_active:
        raise AppError(404, "not_found", "Technician not found.")
    return technician


def _technician_load(db: Session, technician_id: uuid.UUID,
                     ignore_job_id: uuid.UUID | None = None) -> int:
    statement = select(func.count()).select_from(TicketRepairJob).where(
        TicketRepairJob.technician_user_id == technician_id,
        TicketRepairJob.status.in_(OPEN_REPAIR_STATUSES),
    )
    if ignore_job_id is not None:
        statement = statement.where(TicketRepairJob.id != ignore_job_id)
    return int(db.scalar(statement) or 0)


def create_repair_job(
    db: Session,
    user: User,
    ticket_id: uuid.UUID,
    technician_user_id: uuid.UUID,
    scheduled_starts_at: datetime | None,
    note: str | None,
    idempotency_key: str,
) -> tuple[TicketRepairJob, bool]:
    _require_roles(user, SUPPORT)
    ticket = _lock_ticket(db, ticket_id)
    if ticket.status not in ("triaged", "assigned"):
        raise AppError(
            409, "invalid_transition",
            "A repair job can only be assigned to a triaged ticket.",
        )
    technician = _check_technician(db, technician_user_id)
    digest = _digest(
        {"ticket_id": str(ticket_id), "technician_user_id": str(technician_user_id),
         "scheduled_starts_at": scheduled_starts_at.isoformat() if scheduled_starts_at else None}
    )
    existing = db.scalar(
        select(TicketRepairJob).where(
            TicketRepairJob.ticket_id == ticket.id,
            TicketRepairJob.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.request_hash != digest:
            raise AppError(
                409, "idempotency_conflict",
                "This Idempotency-Key was already used for a different repair job.",
            )
        return existing, False
    active = db.scalar(
        select(TicketRepairJob).where(
            TicketRepairJob.ticket_id == ticket.id,
            TicketRepairJob.status.in_(OPEN_REPAIR_STATUSES),
        )
    )
    if active is not None:
        raise AppError(409, "job_already_active", "This ticket already has an open repair job.")
    if _technician_load(db, technician.id) >= REPAIR_JOB_CAP:
        raise AppError(
            409, "technician_unavailable",
            "This technician already has five open repair jobs.",
        )
    if scheduled_starts_at is not None:
        clash = db.scalar(
            select(TicketRepairJob).where(
                TicketRepairJob.technician_user_id == technician.id,
                TicketRepairJob.status.in_(OPEN_REPAIR_STATUSES),
                TicketRepairJob.scheduled_starts_at == scheduled_starts_at,
            )
        )
        if clash is not None:
            raise AppError(
                409, "technician_unavailable",
                "This technician already has a repair job at that time.",
            )
    job = TicketRepairJob(
        reference=next_reference(db, "repair_job", "RPJ"),
        ticket_id=ticket.id,
        order_id=ticket.order_id,
        serial_id=ticket.serial_id,
        technician_user_id=technician.id,
        status="assigned",
        scheduled_starts_at=scheduled_starts_at,
        idempotency_key=idempotency_key,
        request_hash=digest,
        created_by_user_id=user.id,
    )
    db.add(job)
    db.flush()
    _move(db, user, ticket, "assigned", "repair_job_created", note,
          {"repair_job_id": str(job.id), "technician_user_id": str(technician.id)})
    return job, True


def list_repair_jobs(
    db: Session, user: User, ticket_id: uuid.UUID | None
) -> list[TicketRepairJob]:
    statement = select(TicketRepairJob).order_by(TicketRepairJob.created_at.desc())
    if user.role_code == TECHNICIAN:
        statement = statement.where(TicketRepairJob.technician_user_id == user.id)
    elif user.role_code not in SUPPORT:
        raise AppError(403, "forbidden", "You do not have access to repair jobs.")
    if ticket_id is not None:
        _visible_ticket(db, user, ticket_id)
        statement = statement.where(TicketRepairJob.ticket_id == ticket_id)
    return list(db.scalars(statement).all())


def _job_for_technician(db: Session, user: User, job_id: uuid.UUID) -> TicketRepairJob:
    job = db.scalar(
        select(TicketRepairJob).where(TicketRepairJob.id == job_id).with_for_update()
    )
    if job is None:
        raise AppError(404, "not_found", "Repair job not found.")
    if user.role_code in SUPPORT:
        return job
    if user.role_code == TECHNICIAN and job.technician_user_id == user.id:
        return job
    raise AppError(404, "not_found", "Repair job not found.")


def get_repair_job(db: Session, user: User, job_id: uuid.UUID) -> TicketRepairJob:
    return _job_for_technician(db, user, job_id)


def _touch_ticket_for_job(db: Session, user: User, job: TicketRepairJob, action: str,
                          reason: str | None, evidence: dict | None = None) -> None:
    ticket = _lock_ticket(db, job.ticket_id)
    if job.status == "in_progress" and ticket.status == "assigned":
        _move(db, user, ticket, "in_progress", action, reason, evidence)
    else:
        _record(db, user, ticket, action, reason, evidence)


def record_arrival(db: Session, user: User, job_id: uuid.UUID) -> TicketRepairJob:
    _require_roles(user, {TECHNICIAN})
    job = _job_for_technician(db, user, job_id)
    if job.status != "assigned":
        raise AppError(409, "invalid_transition", "Arrival is already recorded.")
    job.arrival_at = utcnow()
    job.status = "in_progress"
    _touch_ticket_for_job(db, user, job, "technician_arrived", None,
                          {"repair_job_id": str(job.id)})
    db.flush()
    return job


def record_diagnostics(db: Session, user: User, job_id: uuid.UUID,
                       payload: dict) -> TicketRepairJob:
    _require_roles(user, {TECHNICIAN})
    job = _job_for_technician(db, user, job_id)
    if job.status == "work_submitted":
        raise AppError(409, "invalid_transition", "This repair job is already submitted.")
    if job.status == "cancelled":
        raise AppError(409, "invalid_transition", "This repair job was cancelled.")
    job.diagnostics = payload
    job.status = "in_progress"
    _touch_ticket_for_job(db, user, job, "diagnostics_recorded", None,
                          {"repair_job_id": str(job.id)})
    db.flush()
    return job


def record_work(db: Session, user: User, job_id: uuid.UUID,
                payload: dict) -> TicketRepairJob:
    from app.models.workflow import CatalogueComponent

    _require_roles(user, {TECHNICIAN})
    job = _job_for_technician(db, user, job_id)
    if job.status == "work_submitted":
        raise AppError(409, "invalid_transition", "This repair job is already submitted.")
    if job.status == "cancelled":
        raise AppError(409, "invalid_transition", "This repair job was cancelled.")
    started = payload["work_started_at"]
    finished = payload["work_finished_at"]
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    if finished.tzinfo is None:
        finished = finished.replace(tzinfo=UTC)
    if finished <= started:
        raise AppError(422, "validation_error", "Work must finish after it starts.")
    parts: list[dict] = []
    for entry in payload.get("parts_used", []):
        component = db.get(CatalogueComponent, entry.get("component_code"))
        if component is None:
            raise AppError(
                404, "not_found",
                f"Unknown component {entry.get('component_code')}.",
            )
        quantity = entry.get("quantity", 0)
        if not isinstance(quantity, int) or quantity <= 0:
            raise AppError(422, "validation_error", "Part quantity must be a positive integer.")
        parts.append({"component_code": component.code, "quantity": quantity})
    job.work_performed = payload["work_performed"]
    job.work_started_at = started
    job.work_finished_at = finished
    job.parts_used = parts
    job.status = "in_progress"
    _touch_ticket_for_job(db, user, job, "work_recorded", None,
                          {"repair_job_id": str(job.id), "parts_used": parts})
    db.flush()
    return job


def submit_repair_job(db: Session, user: User, job_id: uuid.UUID,
                      summary: str) -> TicketRepairJob:
    _require_roles(user, {TECHNICIAN})
    job = _job_for_technician(db, user, job_id)
    if job.status == "work_submitted":
        raise AppError(409, "invalid_transition", "This repair job is already submitted.")
    if job.status == "cancelled":
        raise AppError(409, "invalid_transition", "This repair job was cancelled.")
    if job.arrival_at is None:
        raise AppError(409, "arrival_required", "Record arrival before submitting the repair.")
    if not job.diagnostics:
        raise AppError(409, "diagnostics_required", "Record diagnostics before submitting the repair.")
    if not job.work_performed:
        raise AppError(409, "work_required", "Record the actual work before submitting the repair.")
    job.summary = summary
    job.summary_version += 1
    job.status = "work_submitted"
    _touch_ticket_for_job(db, user, job, "work_submitted", summary,
                          {"repair_job_id": str(job.id),
                           "summary_version": job.summary_version})
    db.flush()
    return job


def mark_resolution_ready(db: Session, user: User, ticket_id: uuid.UUID,
                          summary: str) -> ServiceTicket:
    _require_roles(user, SUPPORT)
    ticket = _lock_ticket(db, ticket_id)
    if ticket.status != "in_progress":
        raise AppError(
            409, "invalid_transition",
            "Only a ticket with recorded repair work can be marked resolved.",
        )
    job = db.scalar(
        select(TicketRepairJob)
        .where(TicketRepairJob.ticket_id == ticket.id,
               TicketRepairJob.status == "work_submitted")
        .order_by(TicketRepairJob.updated_at.desc())
    )
    if job is None or not job.summary:
        raise AppError(
            409, "work_required",
            "The technician must submit the repair summary first.",
        )
    ticket.resolution_version += 1
    ticket.resolution_summary = {
        "version": ticket.resolution_version,
        "summary": summary,
        "repair_job_id": str(job.id),
        "repair_job_reference": job.reference,
        "technician_user_id": str(job.technician_user_id),
        "diagnostics": job.diagnostics,
        "work_performed": job.work_performed,
        "work_started_at": job.work_started_at.isoformat() if job.work_started_at else None,
        "work_finished_at": job.work_finished_at.isoformat() if job.work_finished_at else None,
        "parts_used": job.parts_used or [],
        "technician_summary": job.summary,
        "ready_by_user_id": str(user.id),
    }
    _move(db, user, ticket, "resolved", "resolution_ready", summary,
          {"resolution_version": ticket.resolution_version,
           "repair_job_id": str(job.id)})
    return ticket


def resolution_payload(ticket: ServiceTicket) -> dict:
    if ticket.resolution_summary is None or ticket.status not in (
        "resolved", "customer_confirmed", "closed",
    ):
        raise AppError(404, "not_found", "No resolution summary is ready for review.")
    summary = dict(ticket.resolution_summary)
    payload_hash = _digest(summary)
    return {
        "ticket_id": ticket.id,
        "reference": ticket.reference,
        "status": ticket.status,
        "summary_version": summary["version"],
        "payload_hash": payload_hash,
        "summary": summary,
        "repair_job_id": summary["repair_job_id"],
        "technician_user_id": summary["technician_user_id"],
    }


def confirm_resolution(db: Session, user: User, ticket_id: uuid.UUID,
                       decision: str, summary_version: int,
                       note: str | None) -> ServiceTicket:
    _require_roles(user, {CUSTOMER})
    ticket = _lock_ticket(db, ticket_id)
    if ticket.customer_user_id != user.id:
        raise AppError(404, "not_found", "Ticket not found.")
    if ticket.status != "resolved":
        raise AppError(409, "invalid_transition", "This ticket has no pending resolution.")
    if ticket.resolution_summary is None or summary_version != ticket.resolution_version:
        raise AppError(
            409, "stale_summary",
            "This resolution version is no longer current. Review the latest summary.",
        )
    duplicate = db.scalar(
        select(ResolutionAcknowledgment).where(
            ResolutionAcknowledgment.ticket_id == ticket.id,
            ResolutionAcknowledgment.summary_version == summary_version,
        )
    )
    if duplicate is not None:
        raise AppError(
            409, "duplicate_confirmation",
            "This resolution version was already answered.",
        )
    if decision == "disputed" and not (note and len(note.strip()) >= 3):
        raise AppError(422, "validation_error", "A dispute needs a reason.")
    payload = resolution_payload(ticket)
    acknowledgment = ResolutionAcknowledgment(
        ticket_id=ticket.id,
        repair_job_id=uuid.UUID(payload["repair_job_id"]),
        summary_version=summary_version,
        payload_hash=payload["payload_hash"],
        decision=decision,
        note=(note or None),
        customer_user_id=user.id,
    )
    db.add(acknowledgment)
    db.flush()
    if decision == "confirmed":
        _move(db, user, ticket, "customer_confirmed", "resolution_confirmed", note,
              {"summary_version": summary_version, "payload_hash": payload["payload_hash"]})
    else:
        _move(db, user, ticket, "in_progress", "resolution_disputed", note,
              {"summary_version": summary_version, "payload_hash": payload["payload_hash"]})
    return ticket


def close_ticket(db: Session, user: User, ticket_id: uuid.UUID,
                 reason: str) -> ServiceTicket:
    _require_roles(user, SUPPORT)
    ticket = _lock_ticket(db, ticket_id)
    if ticket.status != "customer_confirmed":
        raise AppError(
            409, "invalid_transition",
            "Only a customer-confirmed ticket can be closed.",
        )
    acknowledgment = db.scalar(
        select(ResolutionAcknowledgment).where(
            ResolutionAcknowledgment.ticket_id == ticket.id,
            ResolutionAcknowledgment.summary_version == ticket.resolution_version,
            ResolutionAcknowledgment.decision == "confirmed",
        )
    )
    if acknowledgment is None:
        raise AppError(
            409, "confirmation_required",
            "The owning customer must confirm the resolution first.",
        )
    _move(db, user, ticket, "closed", "closed", reason,
          {"acknowledgment_id": str(acknowledgment.id)})
    return ticket


def reopen_ticket(db: Session, user: User, ticket_id: uuid.UUID,
                  reason: str) -> ServiceTicket:
    ticket = _lock_ticket(db, ticket_id)
    if user.role_code in SUPPORT:
        pass
    elif user.role_code == CUSTOMER and ticket.customer_user_id == user.id:
        pass
    else:
        raise AppError(404, "not_found", "Ticket not found.")
    if ticket.status not in ("resolved", "customer_confirmed", "closed"):
        raise AppError(409, "invalid_transition", "Only a finished ticket can be reopened.")
    _move(db, user, ticket, "in_progress", "reopened", reason)
    return ticket


def cancel_ticket(db: Session, user: User, ticket_id: uuid.UUID,
                  reason: str) -> ServiceTicket:
    ticket = _lock_ticket(db, ticket_id)
    if user.role_code in SUPPORT:
        pass
    elif user.role_code == CUSTOMER and ticket.customer_user_id == user.id:
        pass
    else:
        raise AppError(404, "not_found", "Ticket not found.")
    if ticket.status not in ("open", "triaged", "assigned"):
        raise AppError(
            409, "invalid_transition", "Work has started; resolve or close instead."
        )
    open_job = db.scalar(
        select(TicketRepairJob).where(
            TicketRepairJob.ticket_id == ticket.id,
            TicketRepairJob.status.in_(OPEN_REPAIR_STATUSES),
        )
    )
    if open_job is not None:
        open_job.status = "cancelled"
        open_job.cancelled_at = utcnow()
    _move(db, user, ticket, "cancelled", "cancelled", reason)
    return ticket


def escalate_ticket(db: Session, user: User, ticket_id: uuid.UUID,
                    reason: str, priority: str | None) -> ServiceTicket:
    _require_roles(user, SUPPORT)
    ticket = _lock_ticket(db, ticket_id)
    if ticket.status in ("closed", "cancelled", "customer_confirmed", "resolved", "open"):
        raise AppError(409, "invalid_transition", "This ticket cannot be escalated now.")
    ticket.escalated = True
    if priority is not None:
        ticket.verified_priority = priority
    _record(db, user, ticket, "escalated", reason, {"verified_priority": priority})
    return ticket


def add_note(db: Session, user: User, ticket_id: uuid.UUID, note: str) -> ServiceTicket:
    _require_roles(user, SUPPORT)
    ticket = _lock_ticket(db, ticket_id)
    if ticket.status in ("closed", "cancelled"):
        raise AppError(409, "invalid_transition", "This ticket is finished.")
    _record(db, user, ticket, "note_added", note)
    return ticket


def ticket_history(db: Session, user: User,
                   ticket_id: uuid.UUID) -> list[ServiceTicketEvent]:
    ticket = _visible_ticket(db, user, ticket_id)
    return list(
        db.scalars(
            select(ServiceTicketEvent)
            .where(ServiceTicketEvent.ticket_id == ticket.id)
            .order_by(ServiceTicketEvent.created_at)
        ).all()
    )


def ticket_attachments(db: Session, user: User,
                       ticket_id: uuid.UUID) -> list[ServiceTicketAttachment]:
    ticket = _visible_ticket(db, user, ticket_id)
    return list(
        db.scalars(
            select(ServiceTicketAttachment)
            .where(ServiceTicketAttachment.ticket_id == ticket.id)
            .order_by(ServiceTicketAttachment.created_at)
        ).all()
    )


def add_attachment(db: Session, user: User, ticket_id: uuid.UUID,
                   repair_job_id: uuid.UUID | None, storage_key: str,
                   filename: str, content_type: str,
                   size_bytes: int) -> ServiceTicketAttachment:
    ticket = _lock_ticket(db, ticket_id)
    if user.role_code == CUSTOMER and ticket.customer_user_id != user.id:
        raise AppError(404, "not_found", "Ticket not found.")
    if user.role_code == TECHNICIAN:
        job = db.scalar(
            select(TicketRepairJob).where(
                TicketRepairJob.ticket_id == ticket.id,
                TicketRepairJob.technician_user_id == user.id,
            )
        )
        if job is None:
            raise AppError(404, "not_found", "Ticket not found.")
    elif user.role_code not in SUPPORT and user.role_code != CUSTOMER:
        raise AppError(403, "forbidden", "You do not have access to tickets.")
    if ticket.status in ("closed", "cancelled"):
        raise AppError(409, "invalid_transition", "This ticket is finished.")
    job_id: uuid.UUID | None = None
    if repair_job_id is not None:
        job = db.get(TicketRepairJob, repair_job_id)
        if job is None or job.ticket_id != ticket.id:
            raise AppError(404, "not_found", "Repair job not found on this ticket.")
        job_id = job.id
    row = ServiceTicketAttachment(
        ticket_id=ticket.id,
        repair_job_id=job_id,
        storage_key=storage_key,
        original_filename=filename[:200],
        content_type=content_type,
        size_bytes=size_bytes,
        uploaded_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    _record(db, user, ticket, "attachment_added", filename,
            {"attachment_id": str(row.id), "repair_job_id": str(job_id) if job_id else None})
    return row


def list_assignable_staff(db: Session, user: User, role: str) -> list[dict]:
    from app.models.identity import EmployeeProfile

    _require_roles(user, SUPPORT)
    if role not in ("technician", "support"):
        raise AppError(422, "validation_error", "Role must be technician or support.")
    rows = db.execute(
        select(User, EmployeeProfile)
        .join(EmployeeProfile, EmployeeProfile.user_id == User.id)
        .where(User.role_code == role, User.is_active.is_(True))
        .order_by(EmployeeProfile.employee_code)
    ).all()
    result = []
    for staff_user, profile in rows:
        entry: dict = {
            "user_id": staff_user.id,
            "employee_code": profile.employee_code,
            "full_name": profile.full_name,
            "role_code": staff_user.role_code,
        }
        if role == "technician":
            entry["open_repair_jobs"] = _technician_load(db, staff_user.id)
        result.append(entry)
    return result


def get_attachment(db: Session, user: User, ticket_id: uuid.UUID,
                   attachment_id: uuid.UUID) -> ServiceTicketAttachment:
    ticket = _visible_ticket(db, user, ticket_id)
    row = db.get(ServiceTicketAttachment, attachment_id)
    if row is None or row.ticket_id != ticket.id:
        raise AppError(404, "not_found", "Attachment not found.")
    return row
