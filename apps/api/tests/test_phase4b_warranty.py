"""Phase 4B serial-level warranty intelligence.

Builds on the real Phase 3 pipeline (order, receipt, serial assignment,
confirmed delivery) through the Phase 4A complaint flow. Example durations
(two-year inverters, twenty-year panels) are entered as policy versions here,
never hardcoded in the service.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session
from tests.test_phase4a_support import (
    _all_staff,
    _confirmed_order,
    _create_ticket,
    _customer,
    _installed_order,
    _login,
    _support,
    _triage,
)

pytestmark = pytest.mark.database

ADMIN_HEADERS = None


def _admin(client, application):
    from tests.test_phase4a_support import _staff

    _staff(application, "admin", "admin4b@example.com", "EMP-ADMIN-941")
    return _login(client, "employee", "EMP-ADMIN-941", "Staffpass123")


def _policy(client, headers, code="INV-STD", duration=730, covered=("inverter",),
            exclusions=None, **extra):
    created = client.post(
        "/api/v1/warranty/policies",
        json={"code": code, "issuer": "SunPower works", "category": "Inverter systems",
              "description": "Standard manufacturer-backed inverter cover for tests."},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    policy = created.json()
    version_payload = {
        "duration_days": duration,
        "applicable_components": [],
        "covered_fault_categories": list(covered),
        "covered_components": ["*"],
        "covered_repair_types": ["repair", "replacement"],
        "exclusions": exclusions or {"fault_categories": [], "components": []},
        "labour_covered": True,
        "replacement_allowed": True,
        "replacement_continuation": "remainder",
        "effective_from": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
    }
    version_payload.update(extra)
    versioned = client.post(
        f"/api/v1/warranty/policies/{policy['id']}/versions",
        json=version_payload, headers=headers,
    )
    assert versioned.status_code == 201, versioned.text
    return policy, versioned.json()


def _decide(client, support, ticket_id, serial, category=None, at=None):
    body = {"ticket_id": ticket_id, "serial_number": serial}
    if category is not None:
        body["fault_category"] = category
    if at is not None:
        body["evaluated_at"] = at
    return client.post(
        "/api/v1/warranty/coverage-decisions", json=body,
        headers={**support, "Idempotency-Key": uuid.uuid4().hex},
    )


def test_policy_versioning_and_guards(client, application):
    _all_staff(application)
    admin = _admin(client, application)
    policy, first = _policy(client, admin)
    assert first["version_number"] == 1
    second = client.post(
        f"/api/v1/warranty/policies/{policy['id']}/versions",
        json={"duration_days": 730, "covered_fault_categories": ["inverter"],
              "effective_from": (datetime.now(UTC) - timedelta(days=30)).isoformat()},
        headers=admin,
    )
    assert second.status_code == 201, second.text
    assert second.json()["version_number"] == 2
    dup = client.post(
        "/api/v1/warranty/policies",
        json={"code": "inv-std", "issuer": "Someone", "category": "Inverters",
              "description": "Duplicate code in other case."},
        headers=admin,
    )
    assert dup.status_code == 409, dup.text
    bad = client.post(
        f"/api/v1/warranty/policies/{policy['id']}/versions",
        json={"duration_days": 0, "covered_fault_categories": ["inverter"],
              "effective_from": datetime.now(UTC).isoformat()},
        headers=admin,
    )
    assert bad.status_code == 422, bad.text
    customer = _customer(client, application, "policy-cust@example.com")
    assert client.post(
        "/api/v1/warranty/policies",
        json={"code": "NOPE-1", "issuer": "Someone", "category": "Inverters",
              "description": "Customers cannot write policies."},
        headers=customer,
    ).status_code == 403


def test_activation_needs_confirmed_delivery(client, application):
    _all_staff(application)
    admin = _admin(client, application)
    _policy(client, admin)
    order = _confirmed_order(client, application)
    support = _support(client)
    blocked = client.post(f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
                          headers=support)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["error"]["code"] == "no_confirmed_delivery"


def test_activation_and_covered_decision(client, application):
    _all_staff(application)
    admin = _admin(client, application)
    _policy(client, admin)
    order, serial = _installed_order(client, application)
    support = _support(client)
    activated = client.post(f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
                            headers=support)
    assert activated.status_code == 201, activated.text
    from app.models.phase3 import EquipmentSerial

    with Session(application.state.engine) as db:
        expected_serials = {row.serial_number for row in db.query(EquipmentSerial).filter_by(
            order_id=uuid.UUID(order["id"]), status="installed").all()}
    assert {row["serial_number"] for row in activated.json()} == expected_serials
    coverage = next(row for row in activated.json() if row["serial_number"] == serial.upper())
    assert coverage["serial_number"] == serial.upper()
    assert coverage["policy_version"] == 1
    assert coverage["status"] == "active"
    repeat = client.post(f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
                         headers=support)
    assert repeat.json() == []
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"], serial)
    _triage(client, ticket["id"])
    decided = _decide(client, _support(client), ticket["id"], serial)
    assert decided.status_code == 201, decided.text
    body = decided.json()
    assert body["verdict"] == "covered", body
    assert body["policy_version"] == 1
    again = _decide(client, _support(client), ticket["id"], serial)
    assert again.status_code == 200, again.text
    assert again.json()["id"] == body["id"]


def test_pending_without_classification(client, application):
    _all_staff(application)
    admin = _admin(client, application)
    _policy(client, admin)
    order, serial = _installed_order(client, application)
    support = _support(client)
    assert client.post(f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
                       headers=support).status_code == 201
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"], serial)
    decided = _decide(client, _support(client), ticket["id"], serial)
    assert decided.json()["verdict"] == "pending_verification", decided.text


def test_exclusion_and_unlisted_fault_not_covered(client, application):
    _all_staff(application)
    admin = _admin(client, application)
    _policy(client, admin, covered=("inverter", "panel"),
            exclusions={"fault_categories": ["panel"], "components": []})
    order, serial = _installed_order(client, application)
    support = _support(client)
    assert client.post(f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
                       headers=support).status_code == 201
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"], serial)
    excluded = _decide(client, _support(client), ticket["id"], serial, category="panel")
    assert excluded.json()["verdict"] == "not_covered", excluded.text
    assert "excluded" in excluded.json()["reason"]
    unlisted = _decide(client, _support(client), ticket["id"], serial, category="wiring")
    assert unlisted.json()["verdict"] == "not_covered", unlisted.text


def test_expiration_boundary_and_policy_snapshot_preserved(client, application):
    _all_staff(application)
    admin = _admin(client, application)
    _policy(client, admin, duration=365)
    order, serial = _installed_order(client, application)
    support = _support(client)
    activated = client.post(f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
                            headers=support)
    ends_at = next(row for row in activated.json()
                   if row["serial_number"] == serial.upper())["ends_at"]
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"], serial)
    _triage(client, ticket["id"])
    support = _support(client)
    boundary = _decide(client, support, ticket["id"], serial, at=ends_at)
    assert boundary.json()["verdict"] == "covered", boundary.text
    first_id = boundary.json()["id"]
    after = datetime.fromisoformat(ends_at) + timedelta(days=1)
    expired = _decide(client, _support(client), ticket["id"], serial, at=after.isoformat())
    assert expired.json()["verdict"] == "not_covered", expired.text
    assert expired.json()["id"] != first_id
    admin = _login(client, "employee", "EMP-ADMIN-941", "Staffpass123")
    policy_id = [p for p in client.get("/api/v1/warranty/policies", headers=admin).json()
                 if p["code"] == "INV-STD"][0]["id"]
    revised = client.post(
        f"/api/v1/warranty/policies/{policy_id}/versions",
        json={"duration_days": 30, "covered_fault_categories": ["inverter"],
              "effective_from": (datetime.now(UTC) - timedelta(days=30)).isoformat()},
        headers=admin,
    )
    assert revised.json()["version_number"] == 2
    from app.models.warranty import CoverageDecision
    with Session(application.state.engine) as db:
        old = db.get(CoverageDecision, uuid.UUID(first_id))
        assert old is not None
        assert old.policy_snapshot["version_number"] == 1
        assert old.policy_snapshot["duration_days"] == 365


def test_exception_override_and_void(client, application):
    _all_staff(application)
    admin = _admin(client, application)
    _policy(client, admin)
    order, serial = _installed_order(client, application)
    support = _support(client)
    activated = client.post(f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
                            headers=support)
    coverage_id = next(row for row in activated.json()
                       if row["serial_number"] == serial.upper())["coverage_id"]
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"], serial)
    _triage(client, ticket["id"])
    voided = client.post(
        f"/api/v1/warranty/coverages/{coverage_id}/void",
        json={"reason": "Policy was issued against the wrong product line."},
        headers=_support(client),
    )
    assert voided.status_code == 200, voided.text
    assert voided.json()["status"] == "void"
    decided = _decide(client, _support(client), ticket["id"], serial)
    assert decided.json()["verdict"] == "not_covered", decided.text
    support_try = client.post(
        "/api/v1/warranty/exceptions",
        json={"ticket_id": ticket["id"], "serial_number": serial, "decision": "covered",
              "reason": "Goodwill after the void error was confirmed by the manager."},
        headers=_support(client),
    )
    assert support_try.status_code == 403, support_try.text
    admin = _login(client, "employee", "EMP-ADMIN-941", "Staffpass123")
    exception = client.post(
        "/api/v1/warranty/exceptions",
        json={"ticket_id": ticket["id"], "serial_number": serial, "decision": "covered",
              "reason": "Goodwill after the void error was confirmed by the manager."},
        headers=admin,
    )
    assert exception.status_code == 201, exception.text
    overridden = _decide(client, _support(client), ticket["id"], serial)
    assert overridden.json()["verdict"] == "covered", overridden.text
    assert "exception" in overridden.json()["reason"]
    admin = _login(client, "employee", "EMP-ADMIN-941", "Staffpass123")
    duplicate = client.post(
        "/api/v1/warranty/exceptions",
        json={"ticket_id": ticket["id"], "serial_number": serial, "decision": "covered",
              "reason": "Trying to record a second override for the same unit."},
        headers=admin,
    )
    assert duplicate.status_code == 409, duplicate.text
    short = client.post(
        f"/api/v1/warranty/coverages/{coverage_id}/void",
        json={"reason": "x"},
        headers=_support(client),
    )
    assert short.status_code == 422, short.text


def test_warranty_visibility_and_lookup(client, application):
    _all_staff(application)
    admin = _admin(client, application)
    _policy(client, admin)
    order, serial = _installed_order(client, application)
    support = _support(client)
    assert client.post(f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
                       headers=support).status_code == 201
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    mine = client.get("/api/v1/warranty/serials/mine", headers=customer)
    assert mine.status_code == 200, mine.text
    from app.models.phase3 import EquipmentSerial

    with Session(application.state.engine) as db:
        expected_serials = {row.serial_number for row in db.query(EquipmentSerial).filter_by(
            order_id=uuid.UUID(order["id"]), status="installed").all()}
    assert {row["serial_number"] for row in mine.json()} == expected_serials
    assert serial.upper() in expected_serials
    stranger = _customer(client, application, "warranty-stranger@example.com")
    assert client.get("/api/v1/warranty/serials/mine", headers=stranger).json() == []
    assert client.get("/api/v1/warranty/serials/lookup?serial_number=x", headers=customer).status_code == 403
    found = client.get(f"/api/v1/warranty/serials/lookup?serial_number={serial}",
                       headers=_support(client))
    assert found.status_code == 200, found.text
    assert found.json()["coverage"]["status"] == "active"
    assert client.get("/api/v1/warranty/serials/lookup?serial_number=SN-NOPE-1",
                      headers=_support(client)).status_code == 404


def test_same_day_expiry_and_void_invalidate_cached_coverage(client, application):
    """A prior verdict cannot survive crossing its exact boundary or voiding."""
    _all_staff(application)
    _policy(client, _admin(client, application))
    order, serial = _installed_order(client, application)
    support = _support(client)
    response = client.post(f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
                           headers=support)
    assert response.status_code == 201, response.text
    coverage = next(row for row in response.json() if row["serial_number"] == serial.upper())
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"], serial)
    _triage(client, ticket["id"])
    support = _support(client)
    boundary = datetime.fromisoformat(coverage["ends_at"])
    first = _decide(client, support, ticket["id"], serial, at=boundary.isoformat())
    assert first.status_code == 201 and first.json()["verdict"] == "covered", first.text
    after = _decide(client, support, ticket["id"], serial,
                    at=(boundary + timedelta(seconds=1)).isoformat())
    assert after.status_code == 201 and after.json()["verdict"] == "not_covered", after.text
    assert after.json()["id"] != first.json()["id"]
    current = _decide(client, support, ticket["id"], serial)
    assert current.json()["verdict"] == "covered", current.text
    voided = client.post(f"/api/v1/warranty/coverages/{coverage['coverage_id']}/void",
                         json={"reason": "Coverage voided after verified custody review."},
                         headers=support)
    assert voided.status_code == 200, voided.text
    changed = _decide(client, support, ticket["id"], serial)
    assert changed.status_code == 201 and changed.json()["verdict"] == "not_covered", changed.text
    assert changed.json()["id"] != current.json()["id"]


def test_warranty_evaluation_normalizes_non_utc_offset():
    from datetime import timezone

    from app.services.warranty_service import _as_utc

    local = datetime(2026, 11, 1, 1, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    normalized = _as_utc(local)
    assert normalized == datetime(2026, 10, 31, 19, 30, tzinfo=UTC)
    assert normalized.tzinfo == UTC
