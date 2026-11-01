"""Service entry points enforce roles before I/O; missing records stay missing.

These protect non-HTTP callers as well as routes, and verify that a rejected
command cannot partially write a record or trigger a provider operation.
"""

import uuid
from types import SimpleNamespace

import pytest
from app.core.errors import AppError
from app.models.identity import User
from app.services import (
    fulfillment_service as fulfillment,
)
from app.services import (
    installation_service as installation,
)
from app.services import (
    inventory_service as inventory,
)
from app.services import (
    order_service as orders,
)
from app.services import (
    payment_service as payments,
)
from app.services import (
    quotation_service as quotations,
)
from app.services import (
    survey_service as surveys,
)
from sqlalchemy.orm import Session

MISSING = uuid.UUID("00000000-0000-4000-8000-000000000001")


class NoDatabaseAccess:
    def __getattr__(self, name):
        raise AssertionError(f"Forbidden command attempted database access: {name}")


FORBIDDEN = [
    (
        quotations.create_quotation,
        {"settings": None, "payload": None, "idempotency_key": "access-test"},
    ),
    (
        quotations.revise_quotation,
        {
            "settings": None,
            "quotation_id": MISSING,
            "payload": None,
            "idempotency_key": "access-test",
        },
    ),
    (quotations.withdraw_quotation, {"quotation_id": MISSING}),
    (quotations.accept_quotation, {"quotation_id": MISSING}),
    (quotations.list_quotations, {"page": 1, "page_size": 20}),
    (surveys.list_surveys, {"page": 1, "page_size": 20}),
    (orders.list_orders, {"page": 1, "page_size": 20}),
    (quotations.template_version, {"package_code_value": "PKG-ONG-3", "version_number": None}),
    (inventory.stock_levels, {}),
    (
        inventory.create_operation,
        {
            "operation_type": "receipt",
            "lines": [],
            "note": None,
            "source_order_id": None,
            "idempotency_key": "access-test",
        },
    ),
    (inventory.mark_ready, {"operation_id": MISSING}),
    (inventory.cancel_operation, {"operation_id": MISSING}),
    (inventory.validate_operation, {"operation_id": MISSING}),
    (inventory.get_operation, {"operation_id": MISSING}),
    (inventory.list_reservations, {}),
    (
        inventory.scan_serial,
        {"serial_number": "SERIAL-ACCESS", "component_code": "PANEL-550", "operation_id": None},
    ),
    (
        inventory.request_replenishment,
        {"component_code": "PANEL-550", "location_code": "MAIN", "quantity": 1},
    ),
    (inventory.decide_replenishment, {"request_id": MISSING, "decision": "approved"}),
    (payments.record_cash_receipt, {"payload": None, "idempotency_key": "access-test"}),
    (surveys.create_survey, {"enquiry_id": MISSING}),
    (surveys.assign_survey, {"survey_id": MISSING, "payload": None}),
    (surveys.decide_survey, {"survey_id": MISSING, "payload": None}),
    (surveys.resurvey, {"survey_id": MISSING}),
    (orders.confirm_order, {"quotation_id": MISSING, "idempotency_key": "access-test"}),
    (orders.list_warehouse, {}),
    (orders.list_scheduling, {}),
    (fulfillment.create_delivery, {"order_id": MISSING, "idempotency_key": "access-test"}),
    (fulfillment.assign_serial, {"serial_id": MISSING, "order_id": MISSING}),
    (fulfillment.void_warranty, {"order_id": MISSING}),
    (installation.schedule_slot, {"scheduling_id": MISSING, "slot": None}),
    (installation.recommend_technicians, {"order_id": MISSING}),
    (installation.create_job, {"order_id": MISSING, "technician_user_id": MISSING, "slot": None}),
]


@pytest.mark.parametrize(
    "function,arguments", FORBIDDEN, ids=lambda value: getattr(value, "__name__", None)
)
def test_unrelated_support_role_cannot_invoke_operational_services(function, arguments):
    # Support may void a warranty, but customers may not. Every other command
    # here is denied to support, including reading customer stock/queue data.
    role = "customer" if function is fulfillment.void_warranty else "support"
    user = User(id=MISSING, role_code=role)
    with pytest.raises(AppError) as caught:
        function(db=NoDatabaseAccess(), user=user, **arguments)
    assert (caught.value.status_code, caught.value.code) == (403, "forbidden")


ABSENT = [
    (quotations.get_quotation, {"quotation_id": MISSING}),
    (
        quotations.create_quotation,
        {
            "settings": None,
            "payload": SimpleNamespace(survey_id=MISSING),
            "idempotency_key": "absent-test",
        },
    ),
    (
        quotations.revise_quotation,
        {
            "settings": None,
            "quotation_id": MISSING,
            "payload": None,
            "idempotency_key": "absent-test",
        },
    ),
    (quotations.withdraw_quotation, {"quotation_id": MISSING}),
    (surveys.get_survey, {"survey_id": MISSING}),
    (surveys.create_survey, {"enquiry_id": MISSING}),
    (surveys.assign_survey, {"survey_id": MISSING, "payload": None}),
    (surveys.decide_survey, {"survey_id": MISSING, "payload": None}),
    (surveys.resurvey, {"survey_id": MISSING}),
    (orders.get_order, {"order_id": MISSING}),
    (orders.confirm_order, {"quotation_id": MISSING, "idempotency_key": "absent-test"}),
    (inventory.get_operation, {"operation_id": MISSING}),
    (inventory.mark_ready, {"operation_id": MISSING}),
    (inventory.cancel_operation, {"operation_id": MISSING}),
    (inventory.validate_operation, {"operation_id": MISSING}),
    (inventory.decide_replenishment, {"request_id": MISSING, "decision": "approved"}),
    (payments.get_intent, {"intent_id": MISSING}),
    (payments.get_requirement, {"quotation_id": MISSING}),
    (fulfillment.create_delivery, {"order_id": MISSING, "idempotency_key": "absent-test"}),
    (fulfillment.get_delivery, {"delivery_id": MISSING}),
    (fulfillment.get_warranty, {"order_id": MISSING}),
    (fulfillment.void_warranty, {"order_id": MISSING}),
    (installation.get_job, {"job_id": MISSING}),
    (installation.schedule_slot, {"scheduling_id": MISSING, "slot": None}),
    (installation.recommend_technicians, {"order_id": MISSING}),
    (installation.create_job, {"order_id": MISSING, "technician_user_id": MISSING, "slot": None}),
]


@pytest.mark.database
@pytest.mark.parametrize(
    "function,arguments", ABSENT, ids=lambda value: getattr(value, "__name__", None)
)
def test_authorized_command_for_absent_resource_cannot_create_side_effects(
    application, function, arguments
):
    user = User(id=MISSING, role_code="admin")
    with Session(application.state.engine) as db:
        with pytest.raises(AppError) as caught:
            function(db=db, user=user, **arguments)
        assert (caught.value.status_code, caught.value.code) == (404, "not_found")
        assert not db.new and not db.dirty and not db.deleted
        db.rollback()
