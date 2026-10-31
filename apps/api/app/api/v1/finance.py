"""Phase 4C isolated routes, retaining inherited session and CSRF protections."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.finance import FinanceEvidence, FinancePeriod
from app.models.identity import User
from app.schemas import finance as s
from app.services import finance_service as f

router = APIRouter(prefix="/finance", tags=["finance"])


@router.post("/evidence", response_model=s.EvidenceResponse, status_code=201)
def upload_evidence(
    file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    row = f.upload(db, user, file.file.read(5_000_001))
    return s.EvidenceResponse(id=row.id, sha256=row.sha256, content_type=row.content_type)


@router.get("/evidence/{evidence_id}")
def download_evidence(
    evidence_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    row = db.get(FinanceEvidence, evidence_id)
    allowed = row is not None and (user.role_code == "admin" or row.owner_id == user.id)
    if row is not None and user.role_code == "sales":
        for doc in f.records(db, "subsidy_document"):
            if doc.payload["evidence_id"] == str(evidence_id):
                case = f.get_record(db, UUID(doc.payload["case_id"]), "subsidy_case")
                if f.subsidy_state(db, case) != "consent_withdrawn":
                    allowed = True
    if not allowed:
        raise AppError(404, "not_found", "Evidence not found.")
    return Response(
        row.content,
        media_type=row.content_type,
        headers={
            "Content-Disposition": 'attachment; filename="evidence"',
            "X-Content-Type-Options": "nosniff",
            "X-Artifact-SHA256": row.sha256,
            "Cache-Control": "no-store",
        },
    )


@router.get("/records", response_model=list[s.RecordResponse])
def list_records(
    kind: str | None = Query(default=None, max_length=40),
    order_id: UUID | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    return f.visible_records(db, user, kind, order_id)


@router.get("/periods", response_model=list[s.PeriodResponse])
def periods(user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    f.require(user, "admin")
    return list(db.scalars(select(FinancePeriod).order_by(FinancePeriod.starts_on)))


@router.post("/periods", response_model=s.PeriodResponse, status_code=201)
def create_period(
    payload: s.PeriodCreate, user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    return f.create_period(db, user, payload)


@router.post("/periods/{period_id}/close", response_model=s.PeriodResponse)
def close_period(
    period_id: UUID,
    payload: s.PeriodClose,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    f.require(user, "admin")
    f.lock(db)
    row = db.get(FinancePeriod, period_id)
    if not row:
        raise AppError(404, "not_found", "Period not found.")
    if row.status == "closed":
        if row.closure_evidence != payload.evidence:
            raise AppError(
                409, "period_closed", "Period is already closed with different evidence."
            )
        return row
    f.record(
        db,
        user,
        "period_close",
        str(period_id),
        {"period_id": str(period_id), "evidence": payload.evidence},
    )
    row.status, row.closure_evidence = "closed", payload.evidence
    db.flush()
    return row


@router.post("/policies", response_model=s.RecordResponse, status_code=201)
def policy(
    payload: s.PolicyCreate, user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    return f.create_policy(db, user, payload)


@router.post("/invoices", response_model=s.RecordResponse, status_code=201)
def invoice(
    payload: s.FinanceInvoiceCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    return f.issue_invoice(db, user, payload)


@router.post("/invoices/{invoice_id}/recognize", response_model=s.RecordResponse, status_code=201)
def recognize(
    invoice_id: UUID,
    payload: s.RecognitionCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    return f.recognize(db, user, invoice_id, payload)


@router.post("/receipts/import", response_model=s.RecordResponse, status_code=201)
def receipt(
    payload: s.PaymentImport, user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    return f.import_payment(db, user, payload)


@router.post("/invoices/{invoice_id}/credits", response_model=s.RecordResponse, status_code=201)
def credit(
    invoice_id: UUID,
    payload: s.CreditCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    return f.credit_invoice(db, user, invoice_id, payload)


@router.get("/journal", response_model=list[s.JournalResponse])
def journal(
    order_id: UUID | None = None, user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    return f.journal_rows(db, user, order_id)


@router.post("/journal/{entry_id}/reverse", response_model=s.RecordResponse, status_code=201)
def reverse(
    entry_id: UUID,
    payload: s.ReverseCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    return f.reverse(db, user, entry_id, payload)


@router.post("/labour-rates", response_model=s.RecordResponse, status_code=201)
def rate(payload: s.RateCreate, user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return f.create_rate(db, user, payload)


@router.post("/timesheets", response_model=s.RecordResponse, status_code=201)
def timesheet(
    payload: s.TimesheetCreate, user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    return f.submit_timesheet(db, user, payload)


@router.post("/timesheets/{sheet_id}/review", response_model=s.RecordResponse, status_code=201)
def review(
    sheet_id: UUID,
    payload: s.TimesheetReview,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    return f.review_timesheet(db, user, sheet_id, payload)


@router.post("/costs", response_model=s.RecordResponse, status_code=201)
def cost(payload: s.CostCreate, user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return f.create_cost(db, user, payload)


@router.post("/payables/{payable_id}/settlements", response_model=s.RecordResponse, status_code=201)
def settle(
    payable_id: UUID,
    payload: s.SettlementCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    return f.settle(db, user, payable_id, payload)


@router.post("/completeness", response_model=s.RecordResponse, status_code=201)
def attest(
    payload: s.CompletenessCreate, user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    return f.attest(db, user, payload)


@router.post("/subsidy-schemes", response_model=s.RecordResponse, status_code=201)
def scheme(
    payload: s.SchemeCreate, user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    return f.create_scheme(db, user, payload)


@router.post("/subsidies", response_model=s.RecordResponse, status_code=201)
def subsidy(
    payload: s.SubsidyCreate, user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    return f.create_subsidy(db, user, payload)


@router.get("/subsidies/{case_id}")
def subsidy_detail(
    case_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    f.lock(db)
    case = f.subsidy_access(db, user, case_id)
    rows = f.visible_records(db, user, order_id=case.order_id)
    return {
        "case": s.RecordResponse.model_validate(case),
        "state": f.subsidy_state(db, case),
        "missing": f.subsidy_missing(db, case),
        "history": [
            s.RecordResponse.model_validate(r)
            for r in rows
            if r.payload.get("case_id") == str(case.id)
        ],
    }


@router.post("/subsidies/{case_id}/documents", response_model=s.RecordResponse, status_code=201)
def subsidy_document(
    case_id: UUID,
    payload: s.SubsidyDocument,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    return f.add_subsidy_document(db, user, case_id, payload)


@router.post("/subsidies/{case_id}/events", response_model=s.RecordResponse, status_code=201)
def subsidy_transition(
    case_id: UUID,
    payload: s.SubsidyTransition,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    return f.transition_subsidy(db, user, case_id, payload)


@router.get("/dashboard", response_model=s.DashboardResponse)
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return f.dashboard(db, user)


@router.get("/reports/profit.csv", response_class=Response)
def report(user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    content, checksum = f.export_report(db, user)
    return Response(
        content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="solarops-profit.csv"',
            "X-Artifact-SHA256": checksum,
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/advances/allocate", response_model=s.RecordResponse, status_code=201)
def allocate(
    payload: s.AdvanceAllocation, user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    return f.allocate_advance(db, user, payload)


@router.post("/payables/{payable_id}/adjustments", response_model=s.RecordResponse, status_code=201)
def adjust(
    payable_id: UUID,
    payload: s.LabourAdjustment,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    return f.adjust_labour(db, user, payable_id, payload)
