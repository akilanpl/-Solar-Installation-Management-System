"""Phase 4A support workspace: complaints, triage, repair jobs, resolution."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.identity import User
from app.models.phase3 import EquipmentSerial, Warranty
from app.models.support import (
    ResolutionAcknowledgment,
    ServiceTicket,
    ServiceTicketAttachment,
    TicketRepairJob,
)
from app.schemas import parse_idempotency_key
from app.schemas.support import (
    AttachmentResponse,
    ConfirmationCreate,
    CustomerReply,
    DiagnosticsUpdate,
    EscalationCreate,
    InfoRequest,
    NoteCreate,
    ReasonedAction,
    RepairJobCreate,
    RepairJobResponse,
    RepairSubmit,
    ResolutionReady,
    ResolutionSummaryResponse,
    StaffEntry,
    SupportAssignmentUpdate,
    TicketCreate,
    TicketDetail,
    TicketEventResponse,
    TicketList,
    TicketSummary,
    TriageUpdate,
    WarrantyInfo,
    WorkUpdate,
)
from app.services import ticket_service
from app.services.evidence_store import evidence_file, save_evidence

router = APIRouter(tags=["tickets"])


def _key(value: str | None) -> str:
    try:
        return parse_idempotency_key(value)
    except ValueError as exc:
        raise AppError(400, "idempotency_key_required", str(exc)) from exc


def _job_response(job: TicketRepairJob) -> RepairJobResponse:
    return RepairJobResponse(
        id=job.id,
        reference=job.reference,
        ticket_id=job.ticket_id,
        technician_user_id=job.technician_user_id,
        status=job.status,
        scheduled_starts_at=job.scheduled_starts_at,
        arrival_at=job.arrival_at,
        work_started_at=job.work_started_at,
        work_finished_at=job.work_finished_at,
        diagnostics=job.diagnostics,
        work_performed=job.work_performed,
        parts_used=job.parts_used,
        summary=job.summary,
        summary_version=job.summary_version,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _attachment_response(row: ServiceTicketAttachment) -> AttachmentResponse:
    return AttachmentResponse(
        id=row.id,
        original_filename=row.original_filename,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        uploaded_by_user_id=row.uploaded_by_user_id,
        created_at=row.created_at,
    )


def _detail(db: Session, ticket: ServiceTicket) -> TicketDetail:
    serial_number: str | None = None
    if ticket.serial_id is not None:
        serial = db.get(EquipmentSerial, ticket.serial_id)
        serial_number = serial.serial_number if serial else None
    warranty_row = db.scalar(select(Warranty).where(Warranty.order_id == ticket.order_id))
    warranty = (
        WarrantyInfo(
            status=warranty_row.status,
            starts_at=warranty_row.starts_at,
            ends_at=warranty_row.ends_at,
            coverage_note=warranty_row.coverage_note,
        )
        if warranty_row
        else None
    )
    jobs = (
        db.scalars(
            select(TicketRepairJob)
            .where(TicketRepairJob.ticket_id == ticket.id)
            .order_by(TicketRepairJob.created_at)
        ).all()
    )
    acknowledgments = (
        db.scalars(
            select(ResolutionAcknowledgment)
            .where(ResolutionAcknowledgment.ticket_id == ticket.id)
            .order_by(ResolutionAcknowledgment.created_at)
        ).all()
    )
    return TicketDetail(
        id=ticket.id,
        reference=ticket.reference,
        status=ticket.status,
        customer_user_id=ticket.customer_user_id,
        site_id=ticket.site_id,
        order_id=ticket.order_id,
        serial_number=serial_number,
        fault_code=ticket.fault_code,
        symptoms=ticket.symptoms,
        customer_urgency=ticket.customer_urgency,
        contact_preference=ticket.contact_preference,
        category=ticket.category,
        verified_priority=ticket.verified_priority,
        assigned_support_user_id=ticket.assigned_support_user_id,
        escalated=ticket.escalated,
        resolution_version=ticket.resolution_version,
        resolution_summary=ticket.resolution_summary,
        warranty=warranty,
        repair_jobs=[_job_response(job) for job in jobs],
        acknowledgments=[
            {
                "id": item.id,
                "summary_version": item.summary_version,
                "payload_hash": item.payload_hash,
                "decision": item.decision,
                "customer_user_id": item.customer_user_id,
                "created_at": item.created_at,
            }
            for item in acknowledgments
        ],
        idempotency_key=ticket.idempotency_key,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


def _summary(ticket: ServiceTicket) -> TicketSummary:
    return TicketSummary(
        id=ticket.id,
        reference=ticket.reference,
        status=ticket.status,
        category=ticket.category,
        verified_priority=ticket.verified_priority,
        customer_urgency=ticket.customer_urgency,
        assigned_support_user_id=ticket.assigned_support_user_id,
        order_id=ticket.order_id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.post("/tickets", response_model=TicketDetail, status_code=201)
def create_ticket(
    payload: TicketCreate,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    ticket, created = ticket_service.create_ticket(
        db, user, payload.model_dump(mode="json"), _key(idempotency_key)
    )
    if not created:
        response.status_code = 200
    return _detail(db, ticket)


@router.get("/tickets", response_model=TicketList)
def list_tickets(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    rows, total = ticket_service.list_tickets(db, user, status, page, page_size)
    return TicketList(
        items=[_summary(ticket) for ticket in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/support/staff", response_model=list[StaffEntry])
def assignable_staff(
    role: str = Query(default="technician"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    return [StaffEntry(**entry) for entry in ticket_service.list_assignable_staff(db, user, role)]


@router.get("/tickets/{ticket_id}", response_model=TicketDetail)
def read_ticket(ticket_id: UUID, user: User = Depends(current_user),
                db: Session = Depends(get_db, scope="function")):
    return _detail(db, ticket_service.get_ticket(db, user, ticket_id))


@router.post("/tickets/{ticket_id}/triage", response_model=TicketDetail)
def triage(ticket_id: UUID, payload: TriageUpdate, user: User = Depends(current_user),
           db: Session = Depends(get_db, scope="function")):
    ticket = ticket_service.triage_ticket(
        db, user, ticket_id, payload.category, payload.verified_priority, payload.note
    )
    return _detail(db, ticket)


@router.post("/tickets/{ticket_id}/support-assignment", response_model=TicketDetail)
def assign_owner(ticket_id: UUID, payload: SupportAssignmentUpdate,
                 user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    ticket = ticket_service.assign_support_owner(
        db, user, ticket_id, payload.support_user_id, payload.note
    )
    return _detail(db, ticket)


@router.post("/tickets/{ticket_id}/request-info", response_model=TicketDetail)
def ask_customer(ticket_id: UUID, payload: InfoRequest,
                 user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return _detail(db, ticket_service.request_info(db, user, ticket_id, payload.message))


@router.post("/tickets/{ticket_id}/customer-reply", response_model=TicketDetail)
def reply(ticket_id: UUID, payload: CustomerReply, user: User = Depends(current_user),
          db: Session = Depends(get_db, scope="function")):
    return _detail(db, ticket_service.customer_reply(db, user, ticket_id, payload.message))


@router.post("/tickets/{ticket_id}/notes", response_model=TicketDetail)
def add_note(ticket_id: UUID, payload: NoteCreate, user: User = Depends(current_user),
             db: Session = Depends(get_db, scope="function")):
    return _detail(db, ticket_service.add_note(db, user, ticket_id, payload.note))


@router.post("/tickets/{ticket_id}/escalation", response_model=TicketDetail)
def escalate(ticket_id: UUID, payload: EscalationCreate,
             user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return _detail(
        db, ticket_service.escalate_ticket(
            db, user, ticket_id, payload.reason, payload.verified_priority)
    )


@router.post("/tickets/{ticket_id}/repair-jobs", response_model=RepairJobResponse,
             status_code=201)
def create_repair_job(
    ticket_id: UUID,
    payload: RepairJobCreate,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    job, created = ticket_service.create_repair_job(
        db, user, ticket_id, payload.technician_user_id, payload.scheduled_starts_at,
        payload.note, _key(idempotency_key),
    )
    if not created:
        response.status_code = 200
    return _job_response(job)


@router.get("/repair-jobs", response_model=list[RepairJobResponse])
def list_repair_jobs(
    ticket_id: UUID | None = Query(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    return [_job_response(job) for job in ticket_service.list_repair_jobs(db, user, ticket_id)]


@router.get("/repair-jobs/{job_id}", response_model=RepairJobResponse)
def read_repair_job(job_id: UUID, user: User = Depends(current_user),
                    db: Session = Depends(get_db, scope="function")):
    return _job_response(ticket_service.get_repair_job(db, user, job_id))


@router.post("/repair-jobs/{job_id}/arrival", response_model=RepairJobResponse)
def job_arrival(job_id: UUID, user: User = Depends(current_user),
                db: Session = Depends(get_db, scope="function")):
    return _job_response(ticket_service.record_arrival(db, user, job_id))


@router.post("/repair-jobs/{job_id}/diagnostics", response_model=RepairJobResponse)
def job_diagnostics(job_id: UUID, payload: DiagnosticsUpdate,
                    user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return _job_response(
        ticket_service.record_diagnostics(db, user, job_id, payload.model_dump(mode="json"))
    )


@router.post("/repair-jobs/{job_id}/work", response_model=RepairJobResponse)
def job_work(job_id: UUID, payload: WorkUpdate, user: User = Depends(current_user),
             db: Session = Depends(get_db, scope="function")):
    return _job_response(
        ticket_service.record_work(db, user, job_id, payload.model_dump())
    )


@router.post("/repair-jobs/{job_id}/submit", response_model=RepairJobResponse)
def job_submit(job_id: UUID, payload: RepairSubmit, user: User = Depends(current_user),
               db: Session = Depends(get_db, scope="function")):
    return _job_response(ticket_service.submit_repair_job(db, user, job_id, payload.summary))


@router.post("/tickets/{ticket_id}/attachments", response_model=AttachmentResponse,
             status_code=201)
def upload_attachment(
    ticket_id: UUID,
    request: Request,
    upload: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
    repair_job_id: UUID | None = Query(default=None),
):
    settings = request.app.state.settings
    payload = upload.file.read(settings.evidence_max_bytes + 1)
    if len(payload) > settings.evidence_max_bytes:
        raise AppError(413, "file_too_large", "Ticket evidence must be 5 MB or smaller.")
    key, content_type = save_evidence(settings, payload)
    try:
        row = ticket_service.add_attachment(
            db, user, ticket_id, repair_job_id, key,
            upload.filename or "evidence", content_type, len(payload),
        )
    except Exception:
        evidence_file(settings, key).unlink(missing_ok=True)
        raise
    return _attachment_response(row)


@router.get("/tickets/{ticket_id}/attachments", response_model=list[AttachmentResponse])
def list_attachments(ticket_id: UUID, user: User = Depends(current_user),
                     db: Session = Depends(get_db, scope="function")):
    return [_attachment_response(row)
            for row in ticket_service.ticket_attachments(db, user, ticket_id)]


@router.get("/tickets/{ticket_id}/attachments/{attachment_id}")
def download_attachment(ticket_id: UUID, attachment_id: UUID, request: Request,
                        user: User = Depends(current_user),
                        db: Session = Depends(get_db, scope="function")):
    row = ticket_service.get_attachment(db, user, ticket_id, attachment_id)
    return FileResponse(
        evidence_file(request.app.state.settings, row.storage_key),
        media_type=row.content_type,
        filename=row.original_filename,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/tickets/{ticket_id}/resolution-ready", response_model=TicketDetail)
def resolution_ready(ticket_id: UUID, payload: ResolutionReady,
                     user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return _detail(db, ticket_service.mark_resolution_ready(
        db, user, ticket_id, payload.summary))


@router.get("/tickets/{ticket_id}/resolution-summary",
            response_model=ResolutionSummaryResponse)
def read_resolution_summary(ticket_id: UUID, user: User = Depends(current_user),
                            db: Session = Depends(get_db, scope="function")):
    ticket = ticket_service.get_ticket(db, user, ticket_id)
    payload = ticket_service.resolution_payload(ticket)
    return ResolutionSummaryResponse(
        ticket_id=payload["ticket_id"],
        reference=payload["reference"],
        status=payload["status"],
        summary_version=payload["summary_version"],
        payload_hash=payload["payload_hash"],
        summary=payload["summary"],
        repair_job_id=payload["repair_job_id"],
        technician_user_id=payload["technician_user_id"],
    )


@router.post("/tickets/{ticket_id}/confirmation", response_model=TicketDetail)
def confirm(ticket_id: UUID, payload: ConfirmationCreate,
            user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return _detail(db, ticket_service.confirm_resolution(
        db, user, ticket_id, payload.decision, payload.summary_version, payload.note))


@router.post("/tickets/{ticket_id}/close", response_model=TicketDetail)
def close(ticket_id: UUID, payload: ReasonedAction, user: User = Depends(current_user),
          db: Session = Depends(get_db, scope="function")):
    return _detail(db, ticket_service.close_ticket(db, user, ticket_id, payload.reason))


@router.post("/tickets/{ticket_id}/reopen", response_model=TicketDetail)
def reopen(ticket_id: UUID, payload: ReasonedAction, user: User = Depends(current_user),
           db: Session = Depends(get_db, scope="function")):
    return _detail(db, ticket_service.reopen_ticket(db, user, ticket_id, payload.reason))


@router.post("/tickets/{ticket_id}/cancel", response_model=TicketDetail)
def cancel(ticket_id: UUID, payload: ReasonedAction, user: User = Depends(current_user),
           db: Session = Depends(get_db, scope="function")):
    return _detail(db, ticket_service.cancel_ticket(db, user, ticket_id, payload.reason))


@router.get("/tickets/{ticket_id}/history", response_model=list[TicketEventResponse])
def history(ticket_id: UUID, user: User = Depends(current_user),
            db: Session = Depends(get_db, scope="function")):
    return [
        TicketEventResponse(
            id=event.id,
            from_status=event.from_status,
            to_status=event.to_status,
            actor_user_id=event.actor_user_id,
            action=event.action,
            reason=event.reason,
            created_at=event.created_at,
        )
        for event in ticket_service.ticket_history(db, user, ticket_id)
    ]
