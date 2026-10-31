"""Offline-first intake for technician field work.

The browser keeps drafts in IndexedDB and replays them here once online.
Every operation carries a client-generated idempotency key plus the
record version the technician saw offline:

* the same key twice returns the stored verdict (exactly-once effect);
* a stale version yields ``conflict`` instead of a silent overwrite;
* a record that moved to a non-editable state yields ``rejected``;
* forbidden business actions (settlements, ledger postings, warranty
  decisions, signatures, OTP, invoicing, payroll, closures) have no
  operation type at all and can never be smuggled through this endpoint.

Evidence bytes are uploaded with the same idempotency key: a retried upload
returns the first stored evidence record instead of writing a duplicate.
"""

import hashlib
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import utcnow
from app.models.identity import User
from app.models.phase4e import TechnicianSyncOperation
from app.models.support import TicketRepairJob
from app.models.workflow import Survey
from app.repositories.queries import add_audit
from app.services import survey_service, ticket_service

OFFLINE_OP_TYPES = (
    "survey_draft",
    "repair_diagnostics",
    "repair_work",
    "repair_checklist",
    "measurement",
    "evidence_intent",
)

SURVEY_DRAFT_FIELDS = {
    "notes",
    "azimuth_deg",
    "tilt_deg",
    "shadow_free_area_sqm",
    "cable_distance_m",
    "grid_connection",
}
MEASUREMENT_FIELDS = {
    "azimuth_deg",
    "tilt_deg",
    "shadow_free_area_sqm",
    "cable_distance_m",
    "grid_connection",
}
SURVEY_EDITABLE_STATES = {"assigned", "in_progress"}
GRID_CHOICES = {"suitable", "unsuitable", "unknown"}
CHECKLIST_ITEM_LIMIT = 50

OFFLINE_CACHE_RETENTION_DAYS = 7


def _get_operation(
    db: Session, user_id: uuid.UUID, client_operation_id: str
) -> TechnicianSyncOperation | None:
    return db.scalar(
        select(TechnicianSyncOperation).where(
            TechnicianSyncOperation.user_id == user_id,
            TechnicianSyncOperation.client_operation_id == client_operation_id,
        )
    )


def submit_batch(
    db: Session, settings: Settings, user: User, operations: list[dict]
) -> list[dict]:
    if len(operations) > 25:
        raise AppError(422, "validation_error", "Send at most 25 operations per batch.")
    verdicts = []
    for entry in operations:
        try:
            with db.begin_nested():
                verdicts.append(submit_one(db, settings, user, entry))
        except AppError as exc:
            verdicts.append(
                {
                    "client_operation_id": str(entry.get("client_operation_id", ""))[:80],
                    "status": "rejected",
                    "error": {"code": exc.code, "message": exc.message},
                    "duplicate": False,
                }
            )
    return verdicts


def submit_one(
    db: Session, settings: Settings, user: User, entry: dict
) -> dict:
    op_type = entry.get("op_type")
    client_operation_id = entry.get("client_operation_id")
    if not isinstance(client_operation_id, str) or not (8 <= len(client_operation_id) <= 80):
        raise AppError(422, "validation_error", "Each operation needs a client operation id.")
    if op_type not in OFFLINE_OP_TYPES:
        raise AppError(
            403, "forbidden_offline_action",
            "This action cannot be performed offline. Reconnect and use the online flow.",
        )
    if user.role_code != "technician":
        raise AppError(403, "forbidden", "Offline sync is available to technicians.")
    # Serialize this user's operation keys, including the first use of a key.
    db.scalar(select(User.id).where(User.id == user.id).with_for_update())
    existing = _get_operation(db, user.id, client_operation_id)
    if existing is not None:
        return _verdict(existing, duplicate=True)
    operation = TechnicianSyncOperation(
        user_id=user.id,
        client_operation_id=client_operation_id,
        op_type=op_type,
        entity_type=str(entry.get("entity_type", ""))[:32],
        entity_id=_parse_uuid(entry.get("entity_id")),
        base_field_version=entry.get("base_field_version"),
        payload=dict(entry.get("payload") or {}),
        status="received",
        result=None,
    )
    db.add(operation)
    db.flush()
    try:
        result = _apply(db, settings, user, operation)
    except _Conflict as exc:
        operation.status = "conflict"
        operation.result = {"reason": str(exc)}
    except AppError as exc:
        operation.status = "rejected"
        operation.result = {"code": exc.code, "message": exc.message}
    else:
        operation.status = "applied"
        operation.result = result
        add_audit(
            db, actor_user_id=user.id, action=f"offline.{op_type}_applied",
            entity_type="technician_sync_operation", entity_id=operation.id,
            metadata={"entity_type": operation.entity_type},
        )
    db.flush()
    return _verdict(operation, duplicate=False)


def _verdict(operation: TechnicianSyncOperation, duplicate: bool) -> dict:
    return {
        "client_operation_id": operation.client_operation_id,
        "operation_id": str(operation.id),
        "op_type": operation.op_type,
        "status": operation.status,
        "result": operation.result,
        "duplicate": duplicate,
    }


class _Conflict(Exception):
    pass


def _parse_uuid(value: object) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError):
        raise AppError(422, "validation_error", "The referenced record id is invalid.")


def _apply(
    db: Session, settings: Settings, user: User, operation: TechnicianSyncOperation
) -> dict:
    handler = {
        "survey_draft": _apply_survey_draft,
        "measurement": _apply_measurement,
        "repair_diagnostics": _apply_repair_diagnostics,
        "repair_work": _apply_repair_work,
        "repair_checklist": _apply_repair_checklist,
        "evidence_intent": _apply_evidence_intent,
    }[operation.op_type]
    return handler(db, settings, user, operation)


def _lock_survey(db: Session, survey_id: uuid.UUID | None) -> Survey:
    if survey_id is None:
        raise AppError(422, "validation_error", "A survey id is required.")
    survey = db.scalar(
        select(Survey).where(Survey.id == survey_id).with_for_update()
    )
    if survey is None:
        raise AppError(404, "not_found", "Survey not found.")
    return survey


def _check_survey_access(user: User, survey: Survey) -> None:
    if user.role_code != "technician" or survey.assigned_technician_user_id != user.id:
        raise AppError(404, "not_found", "Survey not found.")


def _check_survey_version(survey: Survey, base: int | None) -> None:
    if base is None:
        raise AppError(422, "validation_error", "The offline record version is required.")
    if int(base) != survey.field_version:
        raise _Conflict(
            "This record changed on the server. Review the latest version and retry."
        )


def _apply_survey_fields(
    survey: Survey, payload: dict, allowed: set[str], latest_revision_id: uuid.UUID
) -> dict:
    unknown = set(payload) - allowed
    if unknown:
        raise AppError(422, "validation_error", "Unsupported draft fields.")
    if "grid_connection" in payload and payload["grid_connection"] not in GRID_CHOICES:
        raise AppError(422, "validation_error", "Unknown grid connection value.")
    applied = {}
    for field in sorted(allowed):
        if field in payload:
            setattr(survey, field, payload[field])
            applied[field] = payload[field]
    survey.field_version += 1
    return {"survey_id": str(latest_revision_id), "applied": applied,
            "field_version": survey.field_version}


def _apply_survey_draft(
    db: Session, settings: Settings, user: User, operation: TechnicianSyncOperation
) -> dict:
    survey = _lock_survey(db, operation.entity_id)
    _check_survey_access(user, survey)
    if survey.status not in SURVEY_EDITABLE_STATES:
        raise AppError(409, "invalid_transition", "This survey can no longer accept drafts.")
    _check_survey_version(survey, operation.base_field_version)
    return _apply_survey_fields(survey, operation.payload, SURVEY_DRAFT_FIELDS, survey.id)


def _apply_measurement(
    db: Session, settings: Settings, user: User, operation: TechnicianSyncOperation
) -> dict:
    survey = _lock_survey(db, operation.entity_id)
    _check_survey_access(user, survey)
    if survey.status not in SURVEY_EDITABLE_STATES:
        raise AppError(409, "invalid_transition", "This survey can no longer accept drafts.")
    _check_survey_version(survey, operation.base_field_version)
    return _apply_survey_fields(survey, operation.payload, MEASUREMENT_FIELDS, survey.id)


def _lock_job(db: Session, job_id: uuid.UUID | None) -> TicketRepairJob:
    if job_id is None:
        raise AppError(422, "validation_error", "A repair job id is required.")
    job = db.scalar(
        select(TicketRepairJob).where(TicketRepairJob.id == job_id).with_for_update()
    )
    if job is None:
        raise AppError(404, "not_found", "Repair job not found.")
    return job


def _check_job_access(user: User, job: TicketRepairJob) -> None:
    if user.role_code == "technician" and job.technician_user_id == user.id:
        return
    raise AppError(404, "not_found", "Repair job not found.")


def _check_job_version(job: TicketRepairJob, base: int | None) -> None:
    if base is None:
        raise AppError(422, "validation_error", "The offline record version is required.")
    if int(base) != job.field_version:
        raise _Conflict(
            "This repair job changed on the server. Review the latest version and retry."
        )


def _apply_repair_diagnostics(
    db: Session, settings: Settings, user: User, operation: TechnicianSyncOperation
) -> dict:
    job = _lock_job(db, operation.entity_id)
    _check_job_access(user, job)
    if job.status in {"work_submitted", "cancelled"}:
        raise AppError(409, "invalid_transition", "This repair job is already finished.")
    _check_job_version(job, operation.base_field_version)
    diagnostics = operation.payload.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise AppError(422, "validation_error", "Diagnostics notes are required.")
    updated = ticket_service.record_diagnostics(db, user, job.id, diagnostics)
    return {"repair_job_id": str(updated.id), "field_version": updated.field_version}


def _apply_repair_work(
    db: Session, settings: Settings, user: User, operation: TechnicianSyncOperation
) -> dict:
    from datetime import UTC, datetime

    job = _lock_job(db, operation.entity_id)
    _check_job_access(user, job)
    if job.status in {"work_submitted", "cancelled"}:
        raise AppError(409, "invalid_transition", "This repair job is already finished.")
    _check_job_version(job, operation.base_field_version)
    payload = dict(operation.payload)
    for key in ("work_started_at", "work_finished_at"):
        value = payload.get(key)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError:
                raise AppError(422, "validation_error", "Work timestamps must be ISO datetimes.")
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            payload[key] = parsed
    updated = ticket_service.record_work(db, user, job.id, payload)
    return {"repair_job_id": str(updated.id), "field_version": updated.field_version}


def _apply_repair_checklist(
    db: Session, settings: Settings, user: User, operation: TechnicianSyncOperation
) -> dict:
    job = _lock_job(db, operation.entity_id)
    _check_job_access(user, job)
    if job.status in {"work_submitted", "cancelled"}:
        raise AppError(409, "invalid_transition", "This repair job is already finished.")
    _check_job_version(job, operation.base_field_version)
    items = operation.payload.get("items")
    if not isinstance(items, list) or not items or len(items) > CHECKLIST_ITEM_LIMIT:
        raise AppError(422, "validation_error", "Checklist items are required.")
    for item in items:
        if not isinstance(item, dict) or not item.get("key") or not isinstance(item.get("done"), bool):
            raise AppError(422, "validation_error", "Each checklist item needs a key and done flag.")
    diagnostics = dict(job.diagnostics or {})
    checklist = {entry["key"]: entry for entry in items}
    diagnostics["checklist"] = checklist
    updated = ticket_service.record_diagnostics(db, user, job.id, diagnostics)
    return {"repair_job_id": str(updated.id), "field_version": updated.field_version,
            "checklist_keys": sorted(checklist)}


def _apply_evidence_intent(
    db: Session, settings: Settings, user: User, operation: TechnicianSyncOperation
) -> dict:
    payload = operation.payload
    target = payload.get("target")
    content_sha256 = payload.get("content_sha256")
    size_bytes = payload.get("size_bytes")
    if (target not in {"survey", "ticket"}
            or not isinstance(content_sha256, str)
            or len(content_sha256) != 64
            or any(char not in "0123456789abcdef" for char in content_sha256)
            or not isinstance(size_bytes, int) or isinstance(size_bytes, bool)):
        raise AppError(422, "validation_error", "Evidence intent needs a target and checksum.")
    if size_bytes <= 0 or size_bytes > settings.evidence_max_bytes:
        raise AppError(413, "file_too_large", "Survey evidence must be 5 MB or smaller.")
    _authorize_evidence(db, user, target, operation.entity_id)
    return {
        "target": target,
        "content_sha256": content_sha256,
        "upload_url": "/api/v1/offline/evidence",
        "note": "Upload the bytes with the same client operation id to store them.",
    }


def _authorize_evidence(
    db: Session, user: User, target: str, entity_id: uuid.UUID | None
) -> None:
    if target == "survey":
        survey = _lock_survey(db, entity_id)
        _check_survey_access(user, survey)
        if survey.status not in {"assigned", "in_progress", "submitted"}:
            raise AppError(409, "invalid_transition", "Evidence cannot be added in this state.")
    else:
        if entity_id is None:
            raise AppError(422, "validation_error", "A ticket id is required.")
        ticket = ticket_service.get_ticket(db, user, entity_id)
        if ticket.status in {"closed", "cancelled"}:
            raise AppError(409, "invalid_transition", "This ticket is finished.")


def upload_evidence(
    db: Session,
    settings: Settings,
    user: User,
    *,
    client_operation_id: str,
    target: str,
    entity_id: uuid.UUID,
    filename: str,
    payload: bytes,
) -> dict:
    from app.services.evidence_store import save_evidence

    if user.role_code != "technician":
        raise AppError(403, "forbidden", "Evidence upload is available to technicians.")
    if target not in {"survey", "ticket"}:
        raise AppError(422, "validation_error", "Unknown evidence target.")
    if not isinstance(client_operation_id, str) or not (8 <= len(client_operation_id) <= 80):
        raise AppError(422, "validation_error", "Each upload needs a client operation id.")
    db.scalar(select(User.id).where(User.id == user.id).with_for_update())
    _authorize_evidence(db, user, target, entity_id)
    existing = _get_operation(db, user.id, client_operation_id)
    digest = hashlib.sha256(payload).hexdigest()
    if existing is not None:
        if (existing.op_type != "evidence_intent" or existing.entity_id != entity_id
                or existing.payload.get("target") != target
                or existing.status != "applied" or not existing.result
                or existing.result.get("content_sha256") != digest):
            raise AppError(409, "upload_conflict", "This upload id is already in use.")
        if existing.result.get("evidence_id"):
            return dict(existing.result, duplicate=True)
        # An accepted intent is not a stored evidence record. Fulfil it with
        # the matching bytes, then replace its result with the durable receipt.
        if existing.payload.get("size_bytes") != len(payload):
            raise AppError(409, "upload_conflict", "The bytes differ from the evidence intent.")
    key, content_type = save_evidence(settings, payload)
    try:
        if target == "survey":
            row = survey_service.add_evidence(
                db, user, entity_id, storage_key=key, content_type=content_type,
                size_bytes=len(payload), original_filename=filename,
            )
            result = {"evidence_id": str(row.id), "target": target,
                      "content_sha256": digest, "size_bytes": len(payload)}
        else:
            row = ticket_service.add_attachment(
                db, user, entity_id, None, storage_key=key, filename=filename,
                content_type=content_type, size_bytes=len(payload),
            )
            result = {"evidence_id": str(row.id), "target": target,
                      "content_sha256": digest, "size_bytes": len(payload)}
    except Exception:
        from app.services.evidence_store import evidence_file

        evidence_file(settings, key).unlink(missing_ok=True)
        raise
    operation = existing or TechnicianSyncOperation(
        user_id=user.id,
        client_operation_id=client_operation_id,
        op_type="evidence_intent",
        entity_type="evidence",
        entity_id=entity_id,
        base_field_version=None,
        payload={"target": target, "content_sha256": digest, "size_bytes": len(payload)},
        status="applied",
        result=result,
    )
    operation.result = result
    db.add(operation)
    add_audit(
        db, actor_user_id=user.id, action="offline.evidence_uploaded",
        entity_type="technician_sync_operation", entity_id=operation.id,
        metadata={"target": target},
    )
    db.flush()
    return dict(result, duplicate=False)


def recent_operations(db: Session, user: User, limit: int = 50) -> list[dict]:
    rows = db.scalars(
        select(TechnicianSyncOperation)
        .where(TechnicianSyncOperation.user_id == user.id)
        .order_by(TechnicianSyncOperation.created_at.desc())
        .limit(min(max(limit, 1), 100))
    ).all()
    return [_verdict(row, duplicate=False) for row in rows]


def offline_assignments(db: Session, user: User) -> dict:
    if user.role_code != "technician":
        raise AppError(403, "forbidden", "Offline assignments are available to technicians.")
    surveys = db.scalars(
        select(Survey)
        .where(
            Survey.assigned_technician_user_id == user.id,
            Survey.status.in_(["assigned", "in_progress"]),
        )
        .order_by(Survey.created_at.desc())
    ).all()
    jobs = db.scalars(
        select(TicketRepairJob)
        .where(
            TicketRepairJob.technician_user_id == user.id,
            TicketRepairJob.status.in_(["assigned", "in_progress"]),
        )
        .order_by(TicketRepairJob.created_at.desc())
    ).all()
    cached_until = utcnow() + timedelta(days=OFFLINE_CACHE_RETENTION_DAYS)
    return {
        "retention_days": OFFLINE_CACHE_RETENTION_DAYS,
        "cached_until": cached_until.isoformat(),
        "surveys": [
            {"survey_id": str(item.id), "reference": item.reference,
             "status": item.status, "field_version": item.field_version,
             "enquiry_id": str(item.enquiry_id)}
            for item in surveys
        ],
        "repair_jobs": [
            {"repair_job_id": str(item.id), "reference": item.reference,
             "status": item.status, "field_version": item.field_version,
             "ticket_id": str(item.ticket_id)}
            for item in jobs
        ],
    }
