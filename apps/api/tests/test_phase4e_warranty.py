"""Phase 4E warranty extensions on the Phase 4B serial policy model.

Extensions lengthen the exact coverage row the 4B engine created; the
extension row snapshots the original end date, so historical decisions keep
pointing at unchanged snapshots. Nothing here settles money: paid extensions
wait in ``pending_payment`` until support records a verified reference.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session
from tests.test_phase4a_support import (
    _all_staff,
    _installed_order,
    _login,
    _support,
)
from tests.test_phase4b_warranty import _admin, _policy

pytestmark = pytest.mark.database

POLICY_CATEGORY = "Inverter systems"


def _totp_code(application, email: str) -> str:
    import pyotp
    from app.models.identity import User
    from app.models.phase4e import MfaFactor
    from app.services.mfa_service import _fernet

    with Session(application.state.engine) as db:
        user = db.query(User).filter_by(email=email).one()
        factor = db.query(MfaFactor).filter_by(user_id=user.id).order_by(
            MfaFactor.created_at.desc()).first()
        assert factor is not None
        secret = _fernet(application.state.settings).decrypt(
            factor.secret_enc.encode("ascii")).decode()
    return pyotp.TOTP(secret).now()


def _admin_grant(application):
    """A dedicated admin client plus step-up grant for sensitive calls.

    The admin gets its own TestClient because the shared client holds a
    single session cookie: any later customer or support login would
    invalidate captured admin CSRF headers.
    """
    from fastapi.testclient import TestClient

    admin_client = TestClient(application)
    headers = _login(admin_client, "employee", "EMP-ADMIN-941", "Staffpass123")
    started = admin_client.post(
        "/api/v1/auth/mfa/totp/enroll/start",
        json={"label": "Admin key", "password": "Staffpass123"}, headers=headers)
    assert started.status_code == 200, started.text
    confirmed = admin_client.post(
        "/api/v1/auth/mfa/totp/enroll/confirm",
        json={"code": _totp_code(application, "admin4b@example.com")},
        headers=headers)
    assert confirmed.status_code == 200, confirmed.text
    step_up = admin_client.post("/api/v1/auth/step-up/start", headers=headers)
    assert step_up.status_code == 200, step_up.text
    grant = admin_client.post(
        "/api/v1/auth/step-up/verify-totp",
        json={"ticket": step_up.json()["ticket"],
              "code": _totp_code(application, "admin4b@example.com")},
        headers=headers)
    assert grant.status_code == 200, grant.text
    strong = dict(headers)
    strong["X-Strong-Auth"] = grant.json()["grant"]
    return admin_client, strong


def _covered_unit(client, application, email, serial="SN-EXT-0001"):
    _all_staff(application)
    admin = _admin(client, application)
    _policy(client, admin)
    order, serial_number = _installed_order(client, application, email, serial)
    activated = client.post(
        f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
        headers=_support(client))
    assert activated.status_code == 201, activated.text
    return order, serial_number, activated.json()[0]


def _customer_session(client, email):
    # The shared test client holds one session cookie: log in again whenever
    # an admin or support login happened since the last customer call.
    return _login(client, "customer", email, "Solarops123")


def _terms(admin_client, strong, policy_id, price_minor=9000, approval=True):
    created = admin_client.post(
        "/api/v1/warranty/extensions/terms",
        json={"policy_id": policy_id, "extension_days": 365,
              "price_minor": price_minor, "currency": "INR", "window_days": 90,
              "eligible_categories": [POLICY_CATEGORY],
              "max_extensions": 1, "requires_approval": approval},
        headers=strong,
    )
    assert created.status_code == 201, created.text
    return created.json()


def _policy_id(client, admin):
    listed = client.get("/api/v1/warranty/policies", headers=admin)
    assert listed.status_code == 200
    return listed.json()[0]["id"]


def _request(client, email, coverage_id):
    response = client.post(
        "/api/v1/warranty/extensions/requests",
        json={"coverage_id": coverage_id,
              "idempotency_key": f"ext-{uuid.uuid4().hex[:16]}"},
        headers=_customer_session(client, email),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_paid_extension_full_lifecycle(client, application):
    email = "ext-paid@example.com"
    order, serial, coverage = _covered_unit(client, application, email)
    admin_client, strong = _admin_grant(application)
    _terms(admin_client, strong, _policy_id(admin_client, strong))
    checked = client.get("/api/v1/warranty/extensions/eligibility",
                         params={"serial_number": serial},
                         headers=_customer_session(client, email))
    assert checked.status_code == 200, checked.text
    body = checked.json()
    assert body["eligible"] is True
    assert body["price_minor"] == 9000
    assert body["payment_required"] is True
    requested = _request(client, email, coverage["coverage_id"])
    assert requested["status"] == "pending_approval"
    original_ends = requested["original_ends_at"]
    approved = admin_client.post(
        f"/api/v1/warranty/extensions/requests/{requested['id']}/approve",
        json={"note": "Documents verified."}, headers=strong)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "pending_payment"
    # Still pending: the coverage end date must not move on approval alone.
    assert approved.json()["new_ends_at"] is None
    activated = admin_client.post(
        f"/api/v1/warranty/extensions/requests/{requested['id']}/activate",
        json={"payment_reference": "UPI-2026-8841"}, headers=strong)
    assert activated.status_code == 200, activated.text
    assert activated.json()["status"] == "active"
    assert activated.json()["payment_reference"] == "UPI-2026-8841"
    assert activated.json()["original_ends_at"] == original_ends
    from datetime import datetime as _dt

    from app.models.warranty import CoverageDecision, SerializedAssetCoverage

    with Session(application.state.engine) as db:
        row = db.get(SerializedAssetCoverage, uuid.UUID(coverage["coverage_id"]))
        assert row.status == "active"
        assert row.ends_at == _dt.fromisoformat(activated.json()["new_ends_at"])
        assert db.query(CoverageDecision).count() == 0
    # A second extension for the same coverage is refused while one is live.
    duplicate = client.post(
        "/api/v1/warranty/extensions/requests",
        json={"coverage_id": coverage["coverage_id"],
              "idempotency_key": f"ext-{uuid.uuid4().hex[:16]}"},
        headers=_customer_session(client, email))
    assert duplicate.status_code == 409, duplicate.text


def test_free_extension_activates_without_approval(client, application):
    email = "ext-free@example.com"
    order, serial, coverage = _covered_unit(client, application, email)
    admin_client, strong = _admin_grant(application)
    _terms(admin_client, strong, _policy_id(admin_client, strong), price_minor=0, approval=False)
    requested = _request(client, email, coverage["coverage_id"])
    assert requested["status"] == "active", requested
    assert requested["new_ends_at"] is not None


def test_duplicate_request_is_idempotent(client, application):
    email = "ext-dupe@example.com"
    order, serial, coverage = _covered_unit(client, application, email)
    admin_client, strong = _admin_grant(application)
    _terms(admin_client, strong, _policy_id(admin_client, strong))
    key = f"ext-{uuid.uuid4().hex[:16]}"
    first = client.post(
        "/api/v1/warranty/extensions/requests",
        json={"coverage_id": coverage["coverage_id"], "idempotency_key": key},
        headers=_customer_session(client, email))
    assert first.status_code == 201, first.text
    second = client.post(
        "/api/v1/warranty/extensions/requests",
        json={"coverage_id": coverage["coverage_id"], "idempotency_key": key},
        headers=_customer_session(client, email))
    assert second.status_code == 201, second.text
    assert second.json()["id"] == first.json()["id"]


def test_ineligible_when_no_terms_category_or_window(client, application):
    email = "ext-inelig@example.com"
    order, serial, coverage = _covered_unit(client, application, email)
    checked = client.get("/api/v1/warranty/extensions/eligibility",
                         params={"serial_number": serial},
                         headers=_customer_session(client, email))
    assert checked.json()["eligible"] is False
    assert "policy" in checked.json()["reason"].lower()
    admin_client, strong = _admin_grant(application)
    created = admin_client.post(
        "/api/v1/warranty/extensions/terms",
        json={"policy_id": _policy_id(admin_client, strong), "extension_days": 365,
              "price_minor": 100, "currency": "INR", "window_days": 90,
              "eligible_categories": ["Panels"], "max_extensions": 1,
              "requires_approval": True},
        headers=strong)
    assert created.status_code == 201
    checked = client.get("/api/v1/warranty/extensions/eligibility",
                         params={"serial_number": serial},
                         headers=_customer_session(client, email))
    assert checked.json()["eligible"] is False
    assert "category" in checked.json()["reason"].lower()
    # Replace with matching-category terms, confirm eligibility, then close
    # the window by backdating the coverage end.
    _terms(admin_client, strong, _policy_id(admin_client, strong), approval=False)
    checked = client.get("/api/v1/warranty/extensions/eligibility",
                         params={"serial_number": serial},
                         headers=_customer_session(client, email))
    assert checked.json()["eligible"] is True, checked.text
    from app.models.warranty import SerializedAssetCoverage

    with Session(application.state.engine) as db:
        row = db.get(SerializedAssetCoverage, uuid.UUID(coverage["coverage_id"]))
        row.ends_at = datetime.now(UTC) - timedelta(days=400)
        db.commit()
    checked = client.get("/api/v1/warranty/extensions/eligibility",
                         params={"serial_number": serial},
                         headers=_customer_session(client, email))
    assert checked.json()["eligible"] is False
    assert "window" in checked.json()["reason"].lower()


def test_other_customer_serial_is_not_visible(client, application):
    email = "ext-owner@example.com"
    order, serial, coverage = _covered_unit(client, application, email)
    from tests.test_phase4a_support import _customer as _make_customer

    other = _make_customer(client, application, "ext-stranger@example.com")
    checked = client.get("/api/v1/warranty/extensions/eligibility",
                         params={"serial_number": serial}, headers=other)
    assert checked.status_code == 404, checked.text
    requested = client.post(
        "/api/v1/warranty/extensions/requests",
        json={"coverage_id": coverage["coverage_id"],
              "idempotency_key": f"ext-{uuid.uuid4().hex[:16]}"},
        headers=other)
    assert requested.status_code == 404, requested.text


def test_approval_needs_grant_rejection_needs_note(client, application):
    email = "ext-guard@example.com"
    order, serial, coverage = _covered_unit(client, application, email)
    admin_client, strong = _admin_grant(application)
    _terms(admin_client, strong, _policy_id(admin_client, strong))
    requested = _request(client, email, coverage["coverage_id"])
    # Customers can never approve.
    assert client.post(
        f"/api/v1/warranty/extensions/requests/{requested['id']}/approve",
        json={"note": "self-approve"},
        headers=_customer_session(client, email)).status_code == 403
    # Support without a fresh step-up grant is refused.
    support = _support(client)
    assert client.post(
        f"/api/v1/warranty/extensions/requests/{requested['id']}/approve",
        json={"note": "no grant"}, headers=support).status_code == 403
    # Rejection without a note is refused even with a grant.
    assert admin_client.post(
        f"/api/v1/warranty/extensions/requests/{requested['id']}/reject",
        json={}, headers=strong).status_code == 422
    rejected = admin_client.post(
        f"/api/v1/warranty/extensions/requests/{requested['id']}/reject",
        json={"note": "Outside the extension window policy."}, headers=strong)
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    cancelled = client.post(
        f"/api/v1/warranty/extensions/requests/{requested['id']}/cancel",
        headers=_customer_session(client, email))
    assert cancelled.status_code == 409, cancelled.text


def test_expired_offer_blocks_activation(client, application):
    email = "ext-stale@example.com"
    order, serial, coverage = _covered_unit(client, application, email)
    admin_client, strong = _admin_grant(application)
    _terms(admin_client, strong, _policy_id(admin_client, strong))
    requested = _request(client, email, coverage["coverage_id"])
    client.post(
        f"/api/v1/warranty/extensions/requests/{requested['id']}/approve",
        json={"note": "ok"}, headers=strong)
    from app.models.phase4e import WarrantyExtensionOffer

    with Session(application.state.engine) as db:
        offer = db.query(WarrantyExtensionOffer).filter_by(
            coverage_id=uuid.UUID(coverage["coverage_id"])).order_by(
            WarrantyExtensionOffer.version.desc()).first()
        offer.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    activated = admin_client.post(
        f"/api/v1/warranty/extensions/requests/{requested['id']}/activate",
        json={"payment_reference": "CASH-1"}, headers=strong)
    assert activated.status_code == 409, activated.text


def test_void_coverage_cannot_be_extended(client, application):
    email = "ext-void@example.com"
    order, serial, coverage = _covered_unit(client, application, email)
    admin_client, strong = _admin_grant(application)
    _terms(admin_client, strong, _policy_id(admin_client, strong))
    voided = client.post(
        f"/api/v1/warranty/coverages/{coverage['coverage_id']}/void",
        json={"reason": "Serial replaced under RMA."}, headers=_support(client))
    assert voided.status_code == 200, voided.text
    checked = client.get("/api/v1/warranty/extensions/eligibility",
                         params={"serial_number": serial},
                         headers=_customer_session(client, email))
    assert checked.json()["eligible"] is False


def test_extension_audit_trail_and_history_preserved(client, application):
    from app.models.audit import AuditEvent
    from app.models.warranty import CoverageDecision

    email = "ext-audit@example.com"
    order, serial, coverage = _covered_unit(client, application, email)
    admin_client, strong = _admin_grant(application)
    _terms(admin_client, strong, _policy_id(admin_client, strong), price_minor=0, approval=True)
    with Session(application.state.engine) as db:
        decisions_before = db.query(CoverageDecision).count()
    requested = _request(client, email, coverage["coverage_id"])
    approved = admin_client.post(
        f"/api/v1/warranty/extensions/requests/{requested['id']}/approve",
        json={"note": "ok"}, headers=strong)
    assert approved.json()["status"] == "active"
    with Session(application.state.engine) as db:
        assert db.query(CoverageDecision).count() == decisions_before
        actions = {row.action for row in db.query(AuditEvent).filter(
            AuditEvent.entity_type == "warranty_extension").all()}
    for expected in ("warranty.extension_requested", "warranty.extension_approved",
                     "warranty.extension_activated"):
        assert expected in actions, actions
