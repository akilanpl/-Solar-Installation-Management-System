"""Read-model services preserve ownership and role separation before HTTP serialization."""

import uuid
from unittest.mock import Mock

import pytest
from app.core.errors import AppError
from app.models.identity import User
from app.models.phase3 import Delivery, InstallationJob, Warranty
from app.models.workflow import Quotation, SalesOrder, Survey
from app.services import (
    fulfillment_service,
    installation_service,
    order_service,
    quotation_service,
    survey_service,
)
from sqlalchemy.orm import Session

OWNER = uuid.UUID("00000000-0000-4000-8000-000000000011")
STRANGER = uuid.UUID("00000000-0000-4000-8000-000000000012")
RESOURCE = uuid.UUID("00000000-0000-4000-8000-000000000013")


@pytest.mark.parametrize(
    "role,user_id,expected",
    [
        ("customer", OWNER, None),
        ("customer", STRANGER, 404),
        ("support", STRANGER, 403),
        ("sales", STRANGER, None),
    ],
)
def test_quotation_detail_has_owner_scope_and_staff_read_policy(role, user_id, expected):
    quotation = Quotation(id=RESOURCE, customer_user_id=OWNER)
    user = User(id=user_id, role_code=role)
    if expected:
        with pytest.raises(AppError) as caught:
            quotation_service.visible(user, quotation)
        assert caught.value.status_code == expected
    else:
        assert quotation_service.visible(user, quotation) is quotation


@pytest.mark.parametrize(
    "function,model,extra",
    [
        (survey_service.get_survey, Survey, {"assigned_technician_user_id": OWNER}),
        (order_service.get_order, SalesOrder, {}),
    ],
)
@pytest.mark.parametrize(
    "role,user_id,expected",
    [
        ("customer", OWNER, None),
        ("customer", STRANGER, 404),
        ("support", STRANGER, 403),
    ],
)
def test_survey_and_order_reads_never_disclose_another_customers_record(
    function, model, extra, role, user_id, expected
):
    record = model(id=RESOURCE, customer_user_id=OWNER, **extra)
    db = Mock(spec=Session)
    db.scalar.return_value = record
    user = User(id=user_id, role_code=role)
    if expected:
        with pytest.raises(AppError) as caught:
            function(db, user, RESOURCE)
        assert caught.value.status_code == expected
    else:
        assert function(db, user, RESOURCE) is record
    db.add.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.parametrize(
    "function,model",
    [
        (fulfillment_service.get_delivery, Delivery),
        (fulfillment_service.get_warranty, Warranty),
        (installation_service.get_job, InstallationJob),
    ],
)
@pytest.mark.parametrize(
    "role,user_id,expected",
    [
        ("customer", OWNER, None),
        ("customer", STRANGER, 404),
        ("unrecognized_role", STRANGER, 403),
    ],
)
def test_fulfilment_and_job_reads_use_parent_order_ownership(
    function, model, role, user_id, expected
):
    record = model(id=RESOURCE, order_id=RESOURCE)
    order = SalesOrder(id=RESOURCE, customer_user_id=OWNER)
    db = Mock(spec=Session)
    db.scalar.return_value = record
    db.get.side_effect = lambda cls, identity: record if cls is InstallationJob else order
    user = User(id=user_id, role_code=role)
    if expected:
        with pytest.raises(AppError) as caught:
            function(db, user, RESOURCE)
        assert caught.value.status_code == expected
    else:
        assert function(db, user, RESOURCE) is record
    db.add.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.parametrize("assigned,expected", [(OWNER, None), (STRANGER, 404)])
def test_technician_can_read_only_own_assigned_installation(assigned, expected):
    job = InstallationJob(id=RESOURCE, order_id=RESOURCE, technician_user_id=assigned)
    db = Mock(spec=Session)
    db.get.return_value = job
    user = User(id=OWNER, role_code="technician")
    if expected:
        with pytest.raises(AppError) as caught:
            installation_service.get_job(db, user, RESOURCE)
        assert caught.value.status_code == expected
    else:
        assert installation_service.get_job(db, user, RESOURCE) is job
