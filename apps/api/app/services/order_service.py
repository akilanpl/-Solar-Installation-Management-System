"""Confirmed orders.

Confirmation copies the accepted quotation and creates the warehouse and
scheduling requests before the request transaction commits. A second
confirmation of the same quotation waits on the quotation row lock, then
returns the existing order when the idempotency key matches, or 409 when it
does not. Stock is not changed.
"""

import json
import uuid
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.security import utcnow
from app.models.audit import SolarPackage
from app.models.identity import User
from app.models.workflow import (
    InstallationSchedulingRequest,
    Quotation,
    SalesOrder,
    SalesOrderLine,
    Survey,
    WarehousePreparationLine,
    WarehousePreparationRequest,
)
from app.repositories.queries import add_audit
from app.services.payment_service import requirement_for, verified_payments
from app.services.references import next_reference

SALES = {"sales", "admin"}
WAREHOUSE = {"warehouse_staff", "warehouse_manager", "admin"}
SCHEDULING = {"sales", "admin"}


def _hash(quotation_id: uuid.UUID) -> str:
    raw = json.dumps({"quotation_id": str(quotation_id)}, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def _load(db: Session, order_id: uuid.UUID) -> SalesOrder | None:
    return db.scalar(
        select(SalesOrder)
        .where(SalesOrder.id == order_id)
        .options(selectinload(SalesOrder.lines))
        .execution_options(populate_existing=True)
    )


def confirm_order(
    db: Session, user: User, quotation_id: uuid.UUID, idempotency_key: str
) -> tuple[SalesOrder, bool]:
    if user.role_code not in SALES:
        raise AppError(403, "forbidden", "Only sales can confirm an order.")
    quotation = db.scalar(
        select(Quotation)
        .where(Quotation.id == quotation_id)
        .options(selectinload(Quotation.lines))
        .with_for_update()
    )
    if quotation is None:
        raise AppError(404, "not_found", "Quotation not found.")
    digest = _hash(quotation.id)
    existing = db.scalar(select(SalesOrder).where(SalesOrder.quotation_id == quotation.id))
    if existing is not None:
        if (
            existing.confirmed_by_user_id == user.id
            and existing.idempotency_key == idempotency_key
            and existing.request_hash == digest
        ):
            loaded = _load(db, existing.id)
            if loaded is None:
                raise AppError(500, "order_missing", "The order could not be reloaded.")
            return loaded, True
        raise AppError(
            409,
            "duplicate_order",
            "This accepted quotation already has a confirmed order.",
        )
    keyed = db.scalar(
        select(SalesOrder).where(
            SalesOrder.confirmed_by_user_id == user.id,
            SalesOrder.idempotency_key == idempotency_key,
        )
    )
    if keyed is not None:
        if keyed.request_hash != digest:
            raise AppError(
                409,
                "idempotency_conflict",
                "This Idempotency-Key was already used for a different order.",
            )
        loaded = _load(db, keyed.id)
        if loaded is None:
            raise AppError(500, "order_missing", "The order could not be reloaded.")
        return loaded, True
    if quotation.status != "accepted":
        raise AppError(409, "quotation_not_accepted", "Confirm an order only from an accepted quotation.")
    survey = db.get(Survey, quotation.survey_id)
    if survey is None or survey.status != "approved":
        raise AppError(409, "survey_not_approved", "The survey behind this quotation is not approved.")
    requirement = requirement_for(db, quotation.id)
    payments = verified_payments(db, quotation.id)
    verified = sum(item.amount_minor for item in payments)
    if requirement is None or verified < requirement.minimum_advance_minor:
        raise AppError(
            409,
            "payment_not_verified",
            "The advance is not covered by verified payments.",
        )
    test_only = any(item.is_test_only for item in payments)
    package = db.get(SolarPackage, quotation.package_id)
    if package is None:
        raise AppError(500, "package_missing", "The quoted package is missing.")
    order = SalesOrder(
        reference=next_reference(db, "order", "ORD"),
        quotation_id=quotation.id,
        customer_user_id=quotation.customer_user_id,
        site_id=quotation.site_id,
        enquiry_id=quotation.enquiry_id,
        survey_id=quotation.survey_id,
        template_version_id=quotation.template_version_id,
        package_code=package.code,
        quotation_version=quotation.version_number,
        material_total_minor=quotation.material_total_minor,
        installation_total_minor=quotation.installation_total_minor,
        discount_minor=quotation.discount_minor,
        tax_minor=quotation.tax_minor,
        total_minor=quotation.total_minor,
        currency_code=quotation.currency_code,
        payment_verification_state="test_verified" if test_only else "manually_verified",
        test_only_payment=test_only,
        status="confirmed",
        confirmed_by_user_id=user.id,
        confirmed_at=utcnow(),
        idempotency_key=idempotency_key,
        request_hash=digest,
    )
    db.add(order)
    db.flush()
    for line in quotation.lines:
        db.add(
            SalesOrderLine(
                order_id=order.id,
                component_code=line.component_code,
                description=line.description,
                line_kind=line.line_kind,
                quantity=line.quantity,
                unit=line.unit,
                unit_price_minor=line.unit_price_minor,
                line_total_minor=line.line_total_minor,
                sort_order=line.sort_order,
            )
        )
    warehouse = WarehousePreparationRequest(order_id=order.id, status="pending_preparation")
    db.add(warehouse)
    db.flush()
    for line in quotation.lines:
        if line.line_kind != "material" or line.component_code is None:
            continue
        db.add(
            WarehousePreparationLine(
                request_id=warehouse.id,
                component_code=line.component_code,
                description=line.description,
                quantity=line.quantity,
                unit=line.unit,
                sort_order=line.sort_order,
            )
        )
    scheduling = InstallationSchedulingRequest(
        order_id=order.id,
        customer_user_id=quotation.customer_user_id,
        site_id=quotation.site_id,
        work_summary=f"Install {package.name} ({package.code}), quotation {quotation.reference}.",
        status="unscheduled",
        slot_starts_at=None,
    )
    db.add(scheduling)
    add_audit(
        db,
        actor_user_id=user.id,
        action="order.confirmed",
        entity_type="sales_order",
        entity_id=order.id,
        metadata={
            "quotation_id": str(quotation.id),
            "quotation_version": quotation.version_number,
            "payment_verification_state": order.payment_verification_state,
            "test_only_payment": test_only,
        },
    )
    db.flush()
    loaded = _load(db, order.id)
    if loaded is None:
        raise AppError(500, "order_missing", "The order could not be reloaded.")
    return loaded, False


def handoff_ids(db: Session, order_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    warehouse_id = db.scalar(
        select(WarehousePreparationRequest.id).where(WarehousePreparationRequest.order_id == order_id)
    )
    scheduling_id = db.scalar(
        select(InstallationSchedulingRequest.id).where(
            InstallationSchedulingRequest.order_id == order_id
        )
    )
    if warehouse_id is None or scheduling_id is None:
        raise AppError(500, "handoff_missing", "The order handoff records are missing.")
    return warehouse_id, scheduling_id


def get_order(db: Session, user: User, order_id: uuid.UUID) -> SalesOrder:
    order = _load(db, order_id)
    if order is None:
        raise AppError(404, "not_found", "Order not found.")
    if user.role_code in SALES | WAREHOUSE:
        return order
    if user.role_code == "customer" and order.customer_user_id == user.id:
        return order
    if user.role_code == "customer":
        raise AppError(404, "not_found", "Order not found.")
    raise AppError(403, "forbidden", "You cannot view this order.")


def list_orders(db: Session, user: User, *, page: int, page_size: int) -> tuple[list[SalesOrder], int]:
    query = select(SalesOrder).options(selectinload(SalesOrder.lines))
    count_query = select(func.count()).select_from(SalesOrder)
    if user.role_code == "customer":
        query = query.where(SalesOrder.customer_user_id == user.id)
        count_query = count_query.where(SalesOrder.customer_user_id == user.id)
    elif user.role_code not in SALES | WAREHOUSE:
        raise AppError(403, "forbidden", "You cannot list orders.")
    total = int(db.scalar(count_query) or 0)
    rows = list(
        db.scalars(
            query.order_by(SalesOrder.confirmed_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return rows, total


def list_warehouse(db: Session, user: User) -> list[WarehousePreparationRequest]:
    if user.role_code not in WAREHOUSE | {"sales"}:
        raise AppError(403, "forbidden", "You cannot view the warehouse queue.")
    return list(
        db.scalars(
            select(WarehousePreparationRequest)
            .options(selectinload(WarehousePreparationRequest.lines))
            .order_by(WarehousePreparationRequest.created_at)
        )
    )


def list_scheduling(db: Session, user: User) -> list[InstallationSchedulingRequest]:
    if user.role_code not in SCHEDULING:
        raise AppError(403, "forbidden", "You cannot view the scheduling queue.")
    return list(
        db.scalars(
            select(InstallationSchedulingRequest).order_by(InstallationSchedulingRequest.created_at)
        )
    )


def order_reference(db: Session, order_id: uuid.UUID) -> str:
    reference = db.scalar(select(SalesOrder.reference).where(SalesOrder.id == order_id))
    if reference is None:
        raise AppError(500, "order_missing", "The order could not be reloaded.")
    return reference
