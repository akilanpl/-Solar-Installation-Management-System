"""Coverage derives only from a configured policy bound at order confirmation."""

import calendar

from sqlalchemy import func, select

from app.core.errors import AppError
from app.models.coverage import OrderWarrantyTerm, ProductWarrantyPolicy, SerialWarranty
from app.models.phase3 import Delivery, DeliveryLine, EquipmentSerial
from app.models.workflow import CatalogueComponent
from app.repositories.queries import add_audit


def create_policy(db, user, payload):
    if user.role_code != "admin":
        raise AppError(403, "forbidden", "Only admin records approved product warranty terms.")
    component = db.scalar(
        select(CatalogueComponent)
        .where(CatalogueComponent.code == payload.component_code)
        .with_for_update()
    )
    if component is None:
        raise AppError(404, "not_found", "Component not found.")
    version = (
        int(
            db.scalar(
                select(func.coalesce(func.max(ProductWarrantyPolicy.version), 0)).where(
                    ProductWarrantyPolicy.component_code == component.code
                )
            )
            or 0
        )
        + 1
    )
    row = ProductWarrantyPolicy(**payload.model_dump(), version=version, created_by_user_id=user.id)
    db.add(row)
    db.flush()
    add_audit(
        db,
        actor_user_id=user.id,
        action="warranty.policy_version_created",
        entity_type="product_warranty_policy",
        entity_id=row.id,
        metadata={"version": version, "component_code": component.code},
    )
    return row


def snapshot_terms(db, order):
    for code in sorted(
        {
            line.component_code
            for line in order.lines
            if line.line_kind == "material" and line.component_code
        }
    ):
        # The component lock orders policy creation and binding at confirmation.
        db.scalar(
            select(CatalogueComponent).where(CatalogueComponent.code == code).with_for_update()
        )
        policy = db.scalar(
            select(ProductWarrantyPolicy)
            .where(ProductWarrantyPolicy.component_code == code)
            .order_by(ProductWarrantyPolicy.version.desc())
            .limit(1)
        )
        if policy is not None and db.get(OrderWarrantyTerm, (order.id, code)) is None:
            db.add(OrderWarrantyTerm(order_id=order.id, component_code=code, policy_id=policy.id))
    db.flush()


def add_months(value, months):
    month_index = value.year * 12 + value.month - 1 + months
    year, month = divmod(month_index, 12)
    return value.replace(
        year=year, month=month + 1, day=min(value.day, calendar.monthrange(year, month + 1)[1])
    )


def activate(db, user, order_id, event, when):
    serials = list(
        db.scalars(
            select(EquipmentSerial)
            .where(
                EquipmentSerial.order_id == order_id,
                EquipmentSerial.status.in_(("delivered", "installed")),
            )
            .with_for_update()
        )
    )
    for serial in serials:
        terms = db.get(OrderWarrantyTerm, (order_id, serial.component_code))
        if terms is None:
            continue
        policy = db.get(ProductWarrantyPolicy, terms.policy_id)
        if policy.activation_event != event:
            continue
        if db.scalar(
            select(SerialWarranty.id).where(
                SerialWarranty.order_id == order_id, SerialWarranty.serial_id == serial.id
            )
        ):
            continue
        delivery = db.scalar(
            select(Delivery)
            .join(DeliveryLine, DeliveryLine.delivery_id == Delivery.id)
            .where(
                DeliveryLine.id == serial.delivery_line_id,
                Delivery.order_id == order_id,
                Delivery.status == "confirmed",
            )
        )
        if delivery is None:
            continue
        row = SerialWarranty(
            serial_id=serial.id,
            order_id=order_id,
            policy_id=policy.id,
            delivery_id=delivery.id,
            starts_at=when,
            ends_at=add_months(when, policy.months),
            status="active",
        )
        db.add(row)
        db.flush()
        add_audit(
            db,
            actor_user_id=user.id,
            action="warranty.serial_activated",
            entity_type="serial_warranty",
            entity_id=row.id,
            metadata={
                "serial_id": str(serial.id),
                "policy_id": str(policy.id),
                "delivery_id": str(delivery.id),
                "activation_event": event,
            },
        )


def void_return(db, user, serial_id, return_id):
    for row in db.scalars(
        select(SerialWarranty)
        .where(SerialWarranty.serial_id == serial_id, SerialWarranty.status == "active")
        .with_for_update()
    ):
        row.status = "void"
        row.void_reason = f"Inspected equipment return {return_id}"
        add_audit(
            db,
            actor_user_id=user.id,
            action="warranty.serial_voided",
            entity_type="serial_warranty",
            entity_id=row.id,
            metadata={"return_id": str(return_id)},
        )
