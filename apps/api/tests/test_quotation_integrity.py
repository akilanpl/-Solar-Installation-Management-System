"""Regression tests for one open quotation, carried payments, and one order."""

import threading
import uuid

import pytest
from app.core.config import get_settings
from app.core.errors import AppError
from app.models.audit import AuditEvent
from app.models.identity import User
from app.models.workflow import (
    InstallationSchedulingRequest,
    PaymentIntent,
    Quotation,
    QuotationLine,
    SalesOrder,
    WarehousePreparationRequest,
)
from app.schemas.workflow import QuotationCreate, SandboxOutcome
from app.services.payment_service import apply_sandbox_outcome
from app.services.quotation_service import create_quotation
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.test_phase2_workflow import (
    _customer,
    _enquiry,
    _login,
    _qualify,
    _quote,
    _sales,
    _staff,
    _survey_to_approved,
)

pytestmark = pytest.mark.database


def _ready(client, application) -> tuple[dict, str]:
    _staff(application, "sales", "sales@example.com", "EMP-SALES-901")
    _staff(application, "technician", "tech@example.com", "EMP-TECH-901")
    customer = _customer(client, application)
    enquiry = _enquiry(client, customer)
    _qualify(client, enquiry["id"])
    survey = _survey_to_approved(client, application, enquiry["id"])
    return customer, survey["id"]


def test_a_second_open_quotation_is_rejected(client, application):
    _ready_customer, survey_id = _ready(client, application)
    first = _quote(client, survey_id)
    sales = _sales(client)
    second = client.post(
        "/api/v1/quotations",
        json={"survey_id": survey_id, "package_code": "PKG-ONG-3", "discount_minor": 0},
        headers={**sales, "Idempotency-Key": "quote-second-open"},
    )
    assert second.status_code == 409, second.text
    assert second.json()["error"]["code"] == "quotation_already_open"
    with Session(application.state.engine) as db:
        issued = db.scalar(
            select(func.count()).select_from(Quotation).where(Quotation.status == "issued")
        )
        assert issued == 1
        assert db.get(Quotation, uuid.UUID(first["id"])).status == "issued"


def test_concurrent_quotation_creation_keeps_one(client, application):
    _ready_customer, survey_id = _ready(client, application)
    with Session(application.state.engine) as db:
        actor = db.scalar(select(User).where(User.email == "sales@example.com"))
        assert actor is not None
        actor_id = actor.id
    barrier = threading.Barrier(2)
    results: list[str] = []

    def issue(key: str) -> None:
        session = application.state.session_factory()
        try:
            user = session.get(User, actor_id)
            assert user is not None
            barrier.wait()
            create_quotation(
                session,
                get_settings(),
                user,
                QuotationCreate(survey_id=uuid.UUID(survey_id), package_code="PKG-ONG-3"),
                key,
            )
            session.commit()
            results.append("ok")
        except AppError as exc:
            session.rollback()
            results.append(exc.code)
        finally:
            session.close()

    threads = [
        threading.Thread(target=issue, args=("quote-race-0001",)),
        threading.Thread(target=issue, args=("quote-race-0002",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == ["ok", "quotation_already_open"]
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Quotation)) == 1


def test_verified_payment_follows_a_revision_without_a_second_charge(client, application):
    customer, survey_id = _ready(client, application)
    first = _quote(client, survey_id)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    intent = client.post(
        "/api/v1/payments/intents",
        json={"quotation_id": first["id"], "amount_minor": first["total_minor"]},
        headers={**customer, "Idempotency-Key": "pay-before-revision"},
    )
    assert intent.status_code == 201, intent.text
    verified = client.post(
        f"/api/v1/payments/intents/{intent.json()['id']}/sandbox-outcome",
        json={"outcome": "succeeded"},
        headers=customer,
    )
    assert verified.status_code == 200, verified.text
    sales = _sales(client)
    revised = client.post(
        f"/api/v1/quotations/{first['id']}/revisions",
        json={"package_code": "PKG-ONG-3", "discount_minor": 100},
        headers={**sales, "Idempotency-Key": "quote-revision-pay"},
    )
    assert revised.status_code == 201, revised.text
    body = revised.json()
    assert body["version_number"] == 2
    assert body["total_minor"] < first["total_minor"]
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    requirement = client.get(
        f"/api/v1/quotations/{body['id']}/payment-requirement",
        headers=customer,
    )
    assert requirement.status_code == 200, requirement.text
    assert requirement.json()["verified_minor"] == first["total_minor"]
    assert requirement.json()["outstanding_minor"] == 0
    extra = client.post(
        "/api/v1/payments/intents",
        json={"quotation_id": body["id"], "amount_minor": body["total_minor"]},
        headers={**customer, "Idempotency-Key": "pay-again-after-revision"},
    )
    assert extra.status_code == 409
    assert extra.json()["error"]["code"] == "amount_exceeds_balance"
    with Session(application.state.engine) as db:
        original_payment = db.get(PaymentIntent, uuid.UUID(intent.json()["id"]))
        original_line = db.scalar(
            select(QuotationLine).where(
                QuotationLine.quotation_id == uuid.UUID(first["id"]),
                QuotationLine.component_code == "PANEL-550",
            )
        )
        original = db.get(Quotation, uuid.UUID(first["id"]))
        assert original_payment is not None
        assert str(original_payment.quotation_id) == first["id"]
        assert original_payment.status == "verified"
        assert original is not None and original.status == "superseded"
        assert original_line is not None
        assert original.material_total_minor == first["material_total_minor"]
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.action == "quotation.issued")
            )
            == 2
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.action == "quotation.superseded")
            )
            == 1
        )
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    accepted = client.post(f"/api/v1/quotations/{body['id']}/acceptance", headers=customer)
    assert accepted.status_code == 200, accepted.text
    sales = _sales(client)
    order = client.post(
        "/api/v1/orders",
        json={"quotation_id": body["id"]},
        headers={**sales, "Idempotency-Key": "order-carried-pay"},
    )
    assert order.status_code == 201, order.text
    assert order.json()["quotation_id"] == body["id"]
    assert order.json()["quotation_version"] == 2
    assert order.json()["test_only_payment"] is True
    replay = client.post(
        "/api/v1/orders",
        json={"quotation_id": body["id"]},
        headers={**sales, "Idempotency-Key": "order-carried-pay"},
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == order.json()["id"]
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(SalesOrder)) == 1
        assert db.scalar(select(func.count()).select_from(WarehousePreparationRequest)) == 1
        assert db.scalar(select(func.count()).select_from(InstallationSchedulingRequest)) == 1
        verified_sum = db.scalar(
            select(func.coalesce(func.sum(PaymentIntent.amount_minor), 0)).where(
                PaymentIntent.status == "verified"
            )
        )
        assert int(verified_sum) == first["total_minor"]


def test_concurrent_full_payments_cannot_both_verify(client, application):
    _ready_customer, survey_id = _ready(client, application)
    quote = _quote(client, survey_id)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    first = client.post(
        "/api/v1/payments/intents",
        json={"quotation_id": quote["id"], "amount_minor": quote["total_minor"]},
        headers={**customer, "Idempotency-Key": "pay-race-0001"},
    )
    second = client.post(
        "/api/v1/payments/intents",
        json={"quotation_id": quote["id"], "amount_minor": quote["total_minor"]},
        headers={**customer, "Idempotency-Key": "pay-race-0002"},
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    with Session(application.state.engine) as db:
        owner = db.scalar(select(User).where(User.email == "leela@example.com"))
        assert owner is not None
        owner_id = owner.id
    barrier = threading.Barrier(2)
    results: list[str] = []

    def verify(intent_id: str) -> None:
        session = application.state.session_factory()
        try:
            user = session.get(User, owner_id)
            assert user is not None
            barrier.wait()
            apply_sandbox_outcome(
                session,
                get_settings(),
                user,
                uuid.UUID(intent_id),
                SandboxOutcome(outcome="succeeded"),
            )
            session.commit()
            results.append("ok")
        except AppError as exc:
            session.rollback()
            results.append(exc.code)
        finally:
            session.close()

    threads = [
        threading.Thread(target=verify, args=(first.json()["id"],)),
        threading.Thread(target=verify, args=(second.json()["id"],)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == ["amount_exceeds_balance", "ok"]
    with Session(application.state.engine) as db:
        verified_sum = db.scalar(
            select(func.coalesce(func.sum(PaymentIntent.amount_minor), 0)).where(
                PaymentIntent.status == "verified"
            )
        )
        assert int(verified_sum) == quote["total_minor"]


def test_withdrawn_quotation_can_be_replaced(client, application):
    _ready_customer, survey_id = _ready(client, application)
    first = _quote(client, survey_id)
    sales = _sales(client)
    withdrawn = client.post(f"/api/v1/quotations/{first['id']}/withdrawal", headers=sales)
    assert withdrawn.status_code == 200, withdrawn.text
    replacement = _quote(client, survey_id)
    assert replacement["id"] != first["id"]
    assert replacement["status"] == "issued"
    with Session(application.state.engine) as db:
        assert (
            db.scalar(
                select(func.count()).select_from(Quotation).where(Quotation.status == "issued")
            )
            == 1
        )
