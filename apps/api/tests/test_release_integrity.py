"""PostgreSQL release-boundary regressions independent of lifecycle seed helpers."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta

import pytest
from app.core.errors import AppError
from app.core.security import hash_secret
from app.models.finance import (
    FinanceEntry,
    FinanceEvidence,
    FinanceLine,
    FinancePeriod,
    FinanceRecord,
)
from app.models.identity import CustomerProfile, User
from app.models.phase4d import SysCacheOutbox
from app.models.phase4e import MfaTicket, StrongAuthGrant
from app.services import finance_service as finance
from app.services import mfa_service as mfa
from app.services import syscache_service as cache
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

pytestmark = pytest.mark.database
DAY = date(2026, 11, 1)
BALANCED = [("cash", 101, 0), ("customer_advance", 0, 101)]


@pytest.fixture
def actors(application):
    with Session(application.state.engine, expire_on_commit=False) as db:
        rows = [
            User(
                email=f"release-{role}@example.com",
                role_code=role,
                password_hash="unused-test-account",
                is_active=True,
            )
            for role in ("admin", "customer", "support")
        ]
        db.add_all(rows)
        db.flush()
        db.add(
            CustomerProfile(user_id=rows[1].id, full_name="Release customer", phone="9845000000")
        )
        db.commit()
    return rows


def _period(db, admin):
    db.add(FinancePeriod(starts_on=DAY, ends_on=DAY, status="open", actor_id=admin.id))
    db.flush()


def test_concurrent_source_record_and_posting_retries_have_one_durable_effect(application, actors):
    admin = actors[0]
    engine = application.state.engine
    with Session(engine) as db:
        _period(db, admin)
        db.commit()

    def post_once(_):
        with Session(engine) as db:
            source = finance.record(
                db, admin, "release-proof", "concurrent-source", {"amount": 101}
            )
            entry = finance.post(db, admin, source, "concurrent-event", DAY, BALANCED)
            result = (source.id, entry.id)
            db.commit()
            return result

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(post_once, range(4)))
    assert len(set(results)) == 1
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(FinanceRecord)) == 1
        assert db.scalar(select(func.count()).select_from(FinanceEntry)) == 1
        assert list(
            db.execute(
                select(
                    FinanceLine.account, FinanceLine.debit_minor, FinanceLine.credit_minor
                ).order_by(FinanceLine.account)
            )
        ) == sorted(BALANCED)


def test_conflicting_retry_cannot_change_prior_record_or_posting(application, actors):
    admin = actors[0]
    engine = application.state.engine
    with Session(engine) as db:
        _period(db, admin)
        source = finance.record(db, admin, "release-proof", "source", {"amount": 101})
        source_id = source.id
        entry_id = finance.post(db, admin, source, "event", DAY, BALANCED).id
        db.commit()
    with Session(engine) as db:
        with pytest.raises(AppError) as caught:
            finance.record(db, admin, "release-proof", "source", {"amount": 999})
        assert caught.value.code == "idempotency_conflict"
        db.rollback()
        with pytest.raises(AppError) as caught:
            finance.post(
                db,
                admin,
                db.get(FinanceRecord, source_id),
                "event",
                DAY,
                [("cash", 999, 0), ("customer_advance", 0, 999)],
            )
        assert caught.value.code == "idempotency_conflict"
        db.rollback()
        assert finance.entry_for(db, "event").id == entry_id
        assert db.get(FinanceRecord, source_id).payload == {"amount": 101}
        assert db.scalar(select(func.sum(FinanceLine.debit_minor))) == 101


def test_invalid_line_rolls_back_entire_source_and_journal(application, actors):
    admin = actors[0]
    engine = application.state.engine
    with Session(engine) as db:
        _period(db, admin)
        db.commit()
    with Session(engine) as db:
        with pytest.raises(DBAPIError):
            source = finance.record(db, admin, "release-proof", "rollback", {"amount": 101})
            finance.post(
                db,
                admin,
                source,
                "rollback-event",
                DAY,
                [("unknown_account", 101, 0), ("customer_advance", 0, 101)],
            )
            db.commit()
        db.rollback()
        assert db.scalar(select(func.count()).select_from(FinanceRecord)) == 0
        assert db.scalar(select(func.count()).select_from(FinanceEntry)) == 0
        assert db.scalar(select(func.count()).select_from(FinanceLine)) == 0


@pytest.mark.parametrize("lines", [[], [("cash", 0, 0)], [("cash", 101, 0), ("revenue", 0, 100)]])
def test_empty_zero_and_unbalanced_journals_are_rejected_without_posting(
    application, actors, lines
):
    with Session(application.state.engine) as db:
        source = finance.record(db, actors[0], "release-proof", "unbalanced", {})
        with pytest.raises(AppError) as caught:
            finance.post(db, actors[0], source, "unbalanced", DAY, lines)
        assert caught.value.code == "unbalanced"
        assert caught.value.status_code == 422
        assert db.scalar(select(func.count()).select_from(FinanceEntry)) == 0
        db.rollback()


def test_database_independently_rejects_mutation_of_committed_finance_lines(application, actors):
    engine = application.state.engine
    with Session(engine) as db:
        _period(db, actors[0])
        source = finance.record(db, actors[0], "release-proof", "immutable", {})
        finance.post(db, actors[0], source, "immutable", DAY, BALANCED)
        db.commit()
    for statement in (
        "UPDATE finance_lines SET debit_minor=999 WHERE debit_minor>0",
        "DELETE FROM finance_entries",
    ):
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(text(statement))
    with Session(engine) as db:
        assert db.scalar(select(func.sum(FinanceLine.debit_minor))) == 101
        assert db.scalar(select(func.count()).select_from(FinanceEntry)) == 1


def test_outbox_replay_keeps_callers_pending_finance_transaction(application, actors):
    event_id = uuid.uuid4()
    with Session(application.state.engine) as db:
        original = cache.emit_invalidation(
            db, event_id=event_id, aggregate_kind="finance", aggregate_id="source", customer_id=None
        )
        db.commit()
        original_id = original.id
        source = finance.record(db, actors[0], "release-proof", "pending", {"amount": 101})
        replay = cache.emit_invalidation(
            db, event_id=event_id, aggregate_kind="finance", aggregate_id="source", customer_id=None
        )
        assert replay.id == original_id
        source_id = source.id
        db.commit()
    with Session(application.state.engine) as db:
        assert db.get(FinanceRecord, source_id).payload == {"amount": 101}
        assert (
            db.scalar(
                select(func.count())
                .select_from(SysCacheOutbox)
                .where(SysCacheOutbox.event_id == event_id)
            )
            == 1
        )
        with pytest.raises(AppError) as caught:
            cache.emit_invalidation(
                db,
                event_id=event_id,
                aggregate_kind="finance",
                aggregate_id="different-source",
                customer_id=None,
            )
        assert caught.value.code == "idempotency_conflict"
        db.rollback()
        assert (
            db.scalar(
                select(SysCacheOutbox.aggregate_id).where(SysCacheOutbox.event_id == event_id)
            )
            == "source"
        )
        db.execute(delete(SysCacheOutbox).where(SysCacheOutbox.event_id == event_id))
        db.commit()


def test_finance_snapshot_reports_counts_without_disclosing_ledger_payload(application, actors):
    admin, customer, _ = actors
    with Session(application.state.engine) as db:
        db.add(
            FinanceRecord(
                kind="invoice",
                source_key="private",
                customer_id=customer.id,
                actor_id=admin.id,
                payload={"bank_reference": "private-bank", "amount_minor": 123456},
                request_hash="a" * 64,
            )
        )
        db.flush()
        payload = cache.build_snapshot_payload(db, customer.id)
        assert payload["billing_activity"] == {
            "invoice_count": 1,
            "credit_note_count": 0,
            "has_recorded_receipts": False,
            "details_require_finance_access": True,
        }
        assert "private-bank" not in str(payload)
        assert "123456" not in str(payload)
        assert payload["customer"]["user_id"] == str(customer.id)


@pytest.mark.parametrize(
    "content,code",
    [
        (b"", "invalid_file_size"),
        (b"x" * 5_000_001, "invalid_file_size"),
        (b"plain text", "invalid_file_type"),
    ],
)
def test_finance_evidence_rejects_invalid_artifacts(application, actors, content, code):
    with Session(application.state.engine) as db:
        with pytest.raises(AppError) as caught:
            finance.upload(db, actors[1], content)
        assert caught.value.code == code
        assert db.scalar(select(func.count()).select_from(FinanceEvidence)) == 0


def test_finance_evidence_is_owner_scoped_even_with_known_identifier(application, actors):
    admin, customer, support = actors
    with Session(application.state.engine) as db:
        artifact = finance.upload(db, customer, b"%PDF-1.7\nsynthetic release evidence")
        assert finance.evidence(db, customer, artifact.id)["sha256"] == artifact.sha256
        assert finance.evidence(db, admin, artifact.id)["id"] == str(artifact.id)
        with pytest.raises(AppError) as caught:
            finance.evidence(db, support, artifact.id)
        assert caught.value.code == "not_found"
        with pytest.raises(AppError) as caught:
            finance.evidence(db, admin, artifact.id, owner=admin.id)
        assert caught.value.code == "evidence_required"


@pytest.mark.parametrize("failure", ["wrong_owner", "expired", "unknown", "missing"])
def test_strong_auth_grants_are_bound_to_owner_and_expiry(application, actors, failure):
    admin, customer, _ = actors
    settings = application.state.settings
    with Session(application.state.engine) as db:
        grant, raw = mfa.issue_strong_grant(db, settings, admin, "totp")
        if failure == "expired":
            grant.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.flush()
        caller = customer if failure == "wrong_owner" else admin
        attempted = None if failure == "missing" else "unknown" if failure == "unknown" else raw
        with pytest.raises(AppError) as caught:
            mfa.consume_strong_grant(db, settings, caller, attempted, "manage_roles")
        assert caught.value.code == "strong_auth_required"
        assert db.get(StrongAuthGrant, grant.id).used_at is None


@pytest.mark.parametrize(
    "failure,expected",
    [
        ("expired", "mfa_ticket_expired"),
        ("attempts", "rate_limited"),
        ("inactive", "invalid_mfa_ticket"),
        ("no_recovery", "mfa_not_enrolled"),
    ],
)
def test_failed_recovery_challenges_never_issue_session_and_expiry_is_durable(
    application, actors, failure, expected
):
    settings = application.state.settings
    admin = actors[0]
    raw = "release-challenge-" + uuid.uuid4().hex
    with Session(application.state.engine) as db:
        ticket = MfaTicket(
            user_id=admin.id,
            purpose="login",
            ticket_hash=hash_secret(raw, settings.secret_key),
            methods=[] if failure == "no_recovery" else ["recovery_code"],
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
            attempt_count=0,
        )
        if failure == "expired":
            ticket.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        if failure == "attempts":
            ticket.attempt_count = settings.mfa_max_attempts
        if failure == "inactive":
            db.get(User, admin.id).is_active = False
        db.add(ticket)
        db.flush()
        ticket_id = ticket.id
        db.commit()
    with Session(application.state.engine) as db:
        with pytest.raises(AppError) as caught:
            mfa.verify_ticket_recovery(db, settings, raw, "login", "WRONG-CODE")
        assert caught.value.code == expected
    with Session(application.state.engine) as db:
        saved = db.get(MfaTicket, ticket_id)
        assert (saved.consumed_at is not None) == (failure in {"expired", "attempts"})


def test_deferred_database_balance_constraint_rejects_bypass_of_service_validation(
    application, actors
):
    """An out-of-band one-sided insert must fail at commit and leave no journal."""
    with Session(application.state.engine) as db:
        _period(db, actors[0])
        source = finance.record(db, actors[0], "release-proof", "db-balance", {})
        period = db.scalar(select(FinancePeriod))
        entry = FinanceEntry(
            source_event="db-balance",
            record_id=source.id,
            period_id=period.id,
            posting_date=DAY,
            actor_id=actors[0].id,
            request_hash="b" * 64,
        )
        db.add(entry)
        db.flush()
        db.add(FinanceLine(entry_id=entry.id, account="cash", debit_minor=101, credit_minor=0))
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        assert db.scalar(select(func.count()).select_from(FinanceEntry)) == 0
        assert db.scalar(select(func.count()).select_from(FinanceLine)) == 0
        assert db.scalar(select(func.count()).select_from(FinanceRecord)) == 0
