"""Quotations are issued, not drafted.

The selected template version and the calculated lines are stored on the
quotation. Later catalogue edits do not change them. A revision is a new row.
The previous row is marked superseded and its lines are left as inserted.
"""

import json
import uuid
from datetime import timedelta
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import utcnow
from app.domain.bom import BomLine, apply_cable_adjustment
from app.domain.pricing import advance_minor, price_quote
from app.models.audit import SolarPackage
from app.models.enquiry import Enquiry
from app.models.identity import User
from app.models.workflow import (
    CatalogueComponent,
    PackageTemplateLine,
    PackageTemplateVersion,
    PaymentRequirement,
    Quotation,
    QuotationAcceptance,
    QuotationLine,
    QuotationRevisionRequest,
    Survey,
)
from app.repositories.queries import add_audit
from app.schemas.workflow import QuotationCreate, QuotationRevisionCreate, RevisionRequestCreate
from app.services.references import next_reference

SALES = {"sales", "admin"}


def _lock_enquiry(db: Session, enquiry_id: uuid.UUID) -> None:
    locked = db.scalar(select(Enquiry.id).where(Enquiry.id == enquiry_id).with_for_update())
    if locked is None:
        raise AppError(404, "not_found", "Enquiry not found.")


def _hash(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(raw.encode("utf-8")).hexdigest()


def _load(db: Session, quotation_id: uuid.UUID) -> Quotation | None:
    return db.scalar(
        select(Quotation)
        .where(Quotation.id == quotation_id)
        .options(selectinload(Quotation.lines))
        .execution_options(populate_existing=True)
    )


def visible(user: User, quotation: Quotation) -> Quotation:
    if user.role_code in SALES:
        return quotation
    if user.role_code == "customer" and quotation.customer_user_id == user.id:
        return quotation
    if user.role_code == "customer":
        raise AppError(404, "not_found", "Quotation not found.")
    raise AppError(403, "forbidden", "You cannot view this quotation.")


def get_quotation(db: Session, user: User, quotation_id: uuid.UUID) -> Quotation:
    quotation = _load(db, quotation_id)
    if quotation is None:
        raise AppError(404, "not_found", "Quotation not found.")
    return visible(user, quotation)


def list_quotations(
    db: Session, user: User, *, page: int, page_size: int
) -> tuple[list[Quotation], int]:
    query = select(Quotation).options(selectinload(Quotation.lines))
    count_query = select(func.count()).select_from(Quotation)
    if user.role_code == "customer":
        query = query.where(Quotation.customer_user_id == user.id)
        count_query = count_query.where(Quotation.customer_user_id == user.id)
    elif user.role_code not in SALES:
        raise AppError(403, "forbidden", "You cannot list quotations.")
    total = int(db.scalar(count_query) or 0)
    rows = list(
        db.scalars(
            query.order_by(Quotation.issued_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return rows, total


def package_code(db: Session, quotation: Quotation) -> str:
    package = db.get(SolarPackage, quotation.package_id)
    if package is None:
        raise AppError(500, "package_missing", "The quoted package is missing.")
    return package.code


def create_quotation(
    db: Session,
    settings: Settings,
    user: User,
    payload: QuotationCreate,
    idempotency_key: str,
) -> tuple[Quotation, bool]:
    if user.role_code not in SALES:
        raise AppError(403, "forbidden", "Only sales can issue a quotation.")
    survey = db.get(Survey, payload.survey_id)
    if survey is None:
        raise AppError(404, "not_found", "Survey not found.")
    digest = _hash(
        {
            "survey_id": str(payload.survey_id),
            "package_code": payload.package_code,
            "discount_minor": payload.discount_minor,
            "kind": "issue",
        }
    )
    existing = db.scalar(
        select(Quotation).where(
            Quotation.customer_user_id == survey.customer_user_id,
            Quotation.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.request_hash != digest:
            raise AppError(
                409,
                "idempotency_conflict",
                "This Idempotency-Key was already used for a different quotation.",
            )
        loaded = _load(db, existing.id)
        if loaded is None:
            raise AppError(500, "quotation_missing", "The quotation could not be reloaded.")
        return loaded, True
    quotation = _issue(
        db,
        settings,
        user,
        survey,
        payload.package_code,
        payload.discount_minor,
        idempotency_key,
        digest,
        supersedes=None,
    )
    return quotation, False


def revise_quotation(
    db: Session,
    settings: Settings,
    user: User,
    quotation_id: uuid.UUID,
    payload: QuotationRevisionCreate,
    idempotency_key: str,
) -> tuple[Quotation, bool]:
    if user.role_code not in SALES:
        raise AppError(403, "forbidden", "Only sales can revise a quotation.")
    probe = db.get(Quotation, quotation_id)
    if probe is None:
        raise AppError(404, "not_found", "Quotation not found.")
    _lock_enquiry(db, probe.enquiry_id)
    current = db.scalar(select(Quotation).where(Quotation.id == quotation_id).with_for_update())
    if current is None:
        raise AppError(404, "not_found", "Quotation not found.")
    digest = _hash(
        {
            "supersedes": str(quotation_id),
            "package_code": payload.package_code,
            "discount_minor": payload.discount_minor,
            "revision_request_id": str(payload.revision_request_id),
            "kind": "revision",
        }
    )
    existing = db.scalar(
        select(Quotation).where(
            Quotation.customer_user_id == current.customer_user_id,
            Quotation.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.request_hash != digest:
            raise AppError(
                409,
                "idempotency_conflict",
                "This Idempotency-Key was already used for a different quotation.",
            )
        loaded = _load(db, existing.id)
        if loaded is None:
            raise AppError(500, "quotation_missing", "The quotation could not be reloaded.")
        return loaded, True
    if current.status != "issued":
        raise AppError(409, "invalid_transition", "Only an issued quotation can be revised.")
    survey = db.get(Survey, current.survey_id)
    if survey is None or survey.status != "approved":
        raise AppError(409, "survey_not_approved", "The survey is no longer approved.")
    # Supersede before the new insert so the one-active-quotation index
    # allows the replacement in this transaction. A failure rolls both back.
    current.status = "superseded"
    db.flush()
    created = _issue(
        db,
        settings,
        user,
        survey,
        payload.package_code,
        payload.discount_minor,
        idempotency_key,
        digest,
        supersedes=current,
    )
    if payload.revision_request_id is not None:
        request = db.get(QuotationRevisionRequest, payload.revision_request_id)
        if request is None or request.quotation_id != current.id:
            raise AppError(404, "not_found", "Revision request not found.")
        request.status = "addressed"
    add_audit(
        db,
        actor_user_id=user.id,
        action="quotation.superseded",
        entity_type="quotation",
        entity_id=current.id,
        metadata={"replacement_id": str(created.id)},
    )
    db.flush()
    return created, False


def _issue(
    db: Session,
    settings: Settings,
    user: User,
    survey: Survey,
    package_code_value: str,
    discount: int,
    idempotency_key: str,
    digest: str,
    supersedes: Quotation | None,
) -> Quotation:
    if survey.status != "approved":
        raise AppError(409, "survey_not_approved", "A quotation requires an approved survey.")
    enquiry = db.scalar(select(Enquiry).where(Enquiry.id == survey.enquiry_id).with_for_update())
    if enquiry is None:
        raise AppError(404, "not_found", "Enquiry not found.")
    if enquiry.status != "qualified":
        raise AppError(
            409,
            "enquiry_not_qualified",
            "The enquiry must still be qualified before a quotation is issued.",
        )
    if survey.cable_distance_m is None:
        raise AppError(409, "survey_incomplete", "The approved survey has no cable distance.")
    open_quotation_id = db.scalar(
        select(Quotation.id).where(
            Quotation.enquiry_id == enquiry.id,
            Quotation.status.in_(("issued", "accepted")),
        )
    )
    if open_quotation_id is not None:
        raise AppError(
            409,
            "quotation_already_open",
            "This enquiry already has an open quotation. Revise that quotation instead of issuing another.",
        )
    package = db.scalar(select(SolarPackage).where(SolarPackage.code == package_code_value))
    if (
        package is None
        or not package.is_active
        or package.category != "package"
        or package.capacity_w != enquiry.preferred_capacity_w
        or package.grid_type != enquiry.grid_preference
    ):
        raise AppError(
            422,
            "validation_error",
            "Choose the active package that matches the enquiry capacity and grid preference.",
        )
    version = db.scalar(
        select(PackageTemplateVersion)
        .where(
            PackageTemplateVersion.package_id == package.id,
            PackageTemplateVersion.is_current.is_(True),
        )
        .options(selectinload(PackageTemplateVersion.lines))
    )
    if version is None:
        raise AppError(409, "template_missing", "This package has no current template version.")
    names = {component.code: component for component in db.scalars(select(CatalogueComponent))}
    drafted = [
        BomLine(
            component_code=line.component_code,
            description=names[line.component_code].name,
            line_kind=line.line_kind,
            quantity=line.quantity,
            unit=names[line.component_code].unit,
            unit_cost_minor=line.unit_cost_minor,
            unit_price_minor=line.unit_price_minor,
            sort_order=line.sort_order,
        )
        for line in version.lines
    ]
    bom = apply_cable_adjustment(drafted, survey.cable_distance_m)
    material_cost = sum(
        line.quantity * line.unit_cost_minor for line in bom if line.line_kind == "material"
    )
    material_total = sum(
        line.quantity * line.unit_price_minor for line in bom if line.line_kind == "material"
    )
    installation_total = sum(
        line.quantity * line.unit_price_minor for line in bom if line.line_kind == "installation"
    )
    try:
        priced = price_quote(
            material_cost_minor=material_cost,
            material_total_minor=material_total,
            installation_total_minor=installation_total,
            discount_minor=discount,
            tax_rate_bps=settings.gst_rate_bps,
        )
    except ValueError as exc:
        raise AppError(422, "validation_error", str(exc)) from exc
    version_number = (
        int(
            db.scalar(
                select(func.max(Quotation.version_number)).where(Quotation.enquiry_id == enquiry.id)
            )
            or 0
        )
        + 1
    )
    issued_at = utcnow()
    quotation = Quotation(
        reference=next_reference(db, "quotation", "QTN"),
        enquiry_id=enquiry.id,
        survey_id=survey.id,
        customer_user_id=enquiry.customer_user_id,
        site_id=enquiry.site_id,
        package_id=package.id,
        template_version_id=version.id,
        version_number=version_number,
        supersedes_quotation_id=None if supersedes is None else supersedes.id,
        status="issued",
        material_cost_minor=priced.material_cost_minor,
        material_total_minor=priced.material_total_minor,
        installation_total_minor=priced.installation_total_minor,
        discount_minor=priced.discount_minor,
        tax_minor=priced.tax_minor,
        tax_rate_bps=priced.tax_rate_bps,
        total_minor=priced.total_minor,
        currency_code="INR",
        expires_at=issued_at + timedelta(days=settings.quotation_validity_days),
        issued_by_user_id=user.id,
        issued_at=issued_at,
        idempotency_key=idempotency_key,
        request_hash=digest,
    )
    db.add(quotation)
    db.flush()
    _insert_lines(db, quotation, bom, priced.tax_minor, priced.discount_minor, priced.tax_rate_bps)
    db.add(
        PaymentRequirement(
            quotation_id=quotation.id,
            currency_code="INR",
            minimum_advance_minor=advance_minor(priced.total_minor, settings.advance_percent),
            full_amount_minor=priced.total_minor,
            advance_percent=settings.advance_percent,
        )
    )
    add_audit(
        db,
        actor_user_id=user.id,
        action="quotation.issued",
        entity_type="quotation",
        entity_id=quotation.id,
        metadata={
            "template_version_id": str(version.id),
            "total_minor": priced.total_minor,
            "tax_rate_bps": priced.tax_rate_bps,
        },
    )
    db.flush()
    loaded = _load(db, quotation.id)
    if loaded is None:
        raise AppError(500, "quotation_missing", "The quotation could not be reloaded.")
    return loaded


def _insert_lines(
    db: Session,
    quotation: Quotation,
    bom: list[BomLine],
    tax: int,
    discount: int,
    tax_rate_bps: int,
) -> None:
    for line in bom:
        db.add(
            QuotationLine(
                quotation_id=quotation.id,
                component_code=line.component_code,
                description=line.description,
                line_kind=line.line_kind,
                quantity=line.quantity,
                unit=line.unit,
                unit_cost_minor=line.unit_cost_minor,
                unit_price_minor=line.unit_price_minor,
                line_total_minor=line.quantity * line.unit_price_minor,
                sort_order=line.sort_order,
            )
        )
    next_sort = len(bom)
    if discount:
        db.add(
            QuotationLine(
                quotation_id=quotation.id,
                component_code=None,
                description="Authorised discount",
                line_kind="discount",
                quantity=1,
                unit="each",
                unit_cost_minor=0,
                unit_price_minor=discount,
                line_total_minor=discount,
                sort_order=next_sort,
            )
        )
        next_sort += 1
    db.add(
        QuotationLine(
            quotation_id=quotation.id,
            component_code=None,
            description=f"Demonstration tax at {tax_rate_bps} basis points",
            line_kind="tax",
            quantity=1,
            unit="each",
            unit_cost_minor=0,
            unit_price_minor=tax,
            line_total_minor=tax,
            sort_order=next_sort,
        )
    )


def request_revision(
    db: Session, user: User, quotation_id: uuid.UUID, payload: RevisionRequestCreate
) -> QuotationRevisionRequest:
    quotation = _load(db, quotation_id)
    if quotation is None or quotation.customer_user_id != user.id or user.role_code != "customer":
        if quotation is None or user.role_code == "customer":
            raise AppError(404, "not_found", "Quotation not found.")
        raise AppError(403, "forbidden", "Only the customer can request a revision.")
    if quotation.status != "issued":
        raise AppError(409, "invalid_transition", "This quotation is not open for changes.")
    row = QuotationRevisionRequest(
        quotation_id=quotation.id,
        customer_user_id=user.id,
        category=payload.category,
        request_text=payload.request_text,
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    add_audit(
        db,
        actor_user_id=user.id,
        action="quotation.revision_requested",
        entity_type="quotation",
        entity_id=quotation.id,
        metadata={"category": payload.category},
    )
    db.flush()
    return row


def list_revision_requests(
    db: Session, user: User, quotation_id: uuid.UUID
) -> list[QuotationRevisionRequest]:
    quotation = get_quotation(db, user, quotation_id)
    return list(
        db.scalars(
            select(QuotationRevisionRequest)
            .where(QuotationRevisionRequest.quotation_id == quotation.id)
            .order_by(QuotationRevisionRequest.created_at)
        )
    )


def accept_quotation(db: Session, user: User, quotation_id: uuid.UUID) -> Quotation:
    if user.role_code != "customer":
        raise AppError(403, "forbidden", "Only the customer can accept a quotation.")
    quotation = db.scalar(select(Quotation).where(Quotation.id == quotation_id).with_for_update())
    if quotation is None or quotation.customer_user_id != user.id:
        raise AppError(404, "not_found", "Quotation not found.")
    if quotation.status == "accepted":
        raise AppError(409, "already_accepted", "This quotation revision is already accepted.")
    if quotation.status != "issued":
        raise AppError(409, "invalid_transition", "This quotation revision cannot be accepted.")
    if quotation.expires_at is not None and quotation.expires_at <= utcnow():
        raise AppError(409, "quotation_expired", "This quotation has expired.")
    survey = db.get(Survey, quotation.survey_id)
    if survey is None or survey.status != "approved":
        raise AppError(
            409, "survey_not_approved", "The survey behind this quotation is not approved."
        )
    db.add(
        QuotationAcceptance(
            quotation_id=quotation.id,
            customer_user_id=user.id,
            accepted_at=utcnow(),
        )
    )
    quotation.status = "accepted"
    add_audit(
        db,
        actor_user_id=user.id,
        action="quotation.accepted",
        entity_type="quotation",
        entity_id=quotation.id,
        metadata={"version_number": quotation.version_number},
    )
    db.flush()
    loaded = _load(db, quotation.id)
    if loaded is None:
        raise AppError(500, "quotation_missing", "The quotation could not be reloaded.")
    return loaded


def withdraw_quotation(db: Session, user: User, quotation_id: uuid.UUID) -> Quotation:
    if user.role_code not in SALES:
        raise AppError(403, "forbidden", "Only sales can withdraw a quotation.")
    quotation = db.scalar(select(Quotation).where(Quotation.id == quotation_id).with_for_update())
    if quotation is None:
        raise AppError(404, "not_found", "Quotation not found.")
    if quotation.status != "issued":
        raise AppError(409, "invalid_transition", "Only an issued quotation can be withdrawn.")
    quotation.status = "withdrawn"
    add_audit(
        db,
        actor_user_id=user.id,
        action="quotation.withdrawn",
        entity_type="quotation",
        entity_id=quotation.id,
        metadata={},
    )
    db.flush()
    loaded = _load(db, quotation.id)
    if loaded is None:
        raise AppError(500, "quotation_missing", "The quotation could not be reloaded.")
    return loaded


def template_version(db: Session, user: User, package_code_value: str, version_number: int | None):
    if user.role_code not in SALES | {
        "customer",
        "technician",
        "warehouse_staff",
        "warehouse_manager",
    }:
        raise AppError(403, "forbidden", "You cannot view package templates.")
    package = db.scalar(select(SolarPackage).where(SolarPackage.code == package_code_value))
    if package is None:
        raise AppError(404, "not_found", "Package not found.")
    query = select(PackageTemplateVersion).where(PackageTemplateVersion.package_id == package.id)
    if version_number is None:
        query = query.where(PackageTemplateVersion.is_current.is_(True))
    else:
        query = query.where(PackageTemplateVersion.version_number == version_number)
    version = db.scalar(query.options(selectinload(PackageTemplateVersion.lines)))
    if version is None:
        raise AppError(404, "not_found", "Template version not found.")
    return package, version


def component_map(db: Session) -> dict[str, CatalogueComponent]:
    return {row.code: row for row in db.scalars(select(CatalogueComponent))}


def line_rows(version: PackageTemplateVersion) -> list[PackageTemplateLine]:
    return list(version.lines)
