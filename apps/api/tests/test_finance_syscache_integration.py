"""Real PostgreSQL cross-module finance/outbox/cache regression checks."""

import uuid

import pytest
from app.core.errors import AppError
from app.models.finance import FinanceRecord
from app.models.identity import CustomerProfile
from app.models.phase4d import CustomerSnapshotCache, SysCacheOutbox
from app.models.workflow import SalesOrder
from app.services import syscache_service as cache
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.test_phase4a_support import _confirmed_order, _support
from tests.test_phase4c_finance import admin_login, dated, foundation, invoice, post

pytestmark = pytest.mark.database


def _events(db, customer_id):
    return list(db.scalars(select(SysCacheOutbox).where(
        SysCacheOutbox.aggregate_kind == "finance",
        SysCacheOutbox.customer_user_id == customer_id,
    )))


def test_finance_invoice_invalidates_refreshes_and_replays_without_duplicates(client, application):
    _, _, _, policy = foundation(client, application)
    order = _confirmed_order(client, application)
    with Session(application.state.engine) as db:
        customer_id = db.get(SalesOrder, uuid.UUID(order["id"])).customer_user_id
        before = cache.compute_business_version(db, customer_id)
    path = f"/api/v1/customer-snapshots/{customer_id}"
    initial = client.get(path, headers=_support(client))
    assert initial.status_code == 200, initial.text
    assert initial.json()["snapshot"]["billing_activity"]["invoice_count"] == 0

    headers = admin_login(client)
    created = invoice(client, headers, policy, order)
    repeated = invoice(client, headers, policy, order)
    assert repeated["id"] == created["id"]
    with Session(application.state.engine) as db:
        events = _events(db, customer_id)
        assert len(events) == 2  # document creation and balanced journal posting
        assert {row.payload["change"] for row in events} == {"record_created", "entry_posted"}
        assert all(row.aggregate_id == created["id"] for row in events)
        assert all(set(row.payload) == {"change"} for row in events)
        after = cache.compute_business_version(db, customer_id)
        assert after != before
        cache.drain_outbox(db)
        cached = db.scalar(select(CustomerSnapshotCache).where(
            CustomerSnapshotCache.customer_user_id == customer_id))
        assert cached.invalidated_at is not None
        db.commit()
    refreshed = client.get(path, headers=_support(client))
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["business_version"] == after
    summary = refreshed.json()["snapshot"]["billing_activity"]
    assert summary == {
        "invoice_count": 1, "credit_note_count": 0,
        "has_recorded_receipts": False, "details_require_finance_access": True,
    }
    # Snapshot access does not confer access to restricted financial records.
    denied = client.get("/api/v1/finance/records", headers=_support(client))
    assert denied.status_code == 403, denied.text


def test_finance_failed_post_rolls_back_source_and_outbox(client, application):
    headers, evidence_id, period, policy = foundation(client, application)
    order = _confirmed_order(client, application)
    headers = admin_login(client)
    post(client, f"periods/{period['id']}/close",
         {"evidence": "Synthetic test close"}, headers, 200)
    with Session(application.state.engine) as db:
        customer_id = db.get(SalesOrder, uuid.UUID(order["id"])).customer_user_id
        before = cache.compute_business_version(db, customer_id)
        event_ids = {row.event_id for row in _events(db, customer_id)}
    failed = post(client, "costs", {
        **dated(policy), "order_id": order["id"], "kind": "expense",
        "amount_minor": 100, "evidence_id": evidence_id,
        "description": "Synthetic rollback", "key": "cache-rollback-expense",
    }, headers, 409)
    assert failed["error"]["code"] == "period_closed"
    with Session(application.state.engine) as db:
        assert db.scalar(select(FinanceRecord).where(
            FinanceRecord.source_key == "cache-rollback-expense")) is None
        assert {row.event_id for row in _events(db, customer_id)} == event_ids
        assert cache.compute_business_version(db, customer_id) == before


def test_duplicate_outbox_event_preserves_callers_transaction(client, application):
    _, _, _, policy = foundation(client, application)
    order = _confirmed_order(client, application)
    invoice(client, admin_login(client), policy, order)
    with Session(application.state.engine) as db:
        customer_id = db.get(SalesOrder, uuid.UUID(order["id"])).customer_user_id
        event = _events(db, customer_id)[0]
        profile = db.get(CustomerProfile, customer_id)
        profile.full_name = "Synthetic transaction preserved"
        result = cache.emit_invalidation(
            db, event_id=event.event_id, aggregate_kind=event.aggregate_kind,
            aggregate_id=event.aggregate_id, customer_id=customer_id,
            payload=event.payload,
        )
        assert result.id == event.id
        # Reusing an id with another customer's/aggregate's content is rejected.
        with pytest.raises(AppError) as rejected:
            cache.emit_invalidation(
                db, event_id=event.event_id, aggregate_kind="finance",
                aggregate_id="different-source", customer_id=customer_id,
                payload=event.payload,
            )
        assert rejected.value.code == "idempotency_conflict"
        db.commit()
    with Session(application.state.engine) as db:
        assert db.get(CustomerProfile, customer_id).full_name == "Synthetic transaction preserved"
        assert len(_events(db, customer_id)) == 2
