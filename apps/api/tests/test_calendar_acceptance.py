"""Declared availability and concurrent cross-resource booking against PostgreSQL."""

import threading
import uuid

import pytest
from app.api.v1.calendar import AppointmentInput
from app.core.errors import AppError
from app.models.identity import User
from app.models.scheduling import TechnicianAppointment, TechnicianAvailability
from app.services import calendar_service
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.test_phase3_warehouse_installation import _all_staff, _confirmed_order, _sales, _staff

pytestmark = pytest.mark.database


def _setup(client, application, policy=True):
    _all_staff(application)
    orders = [
        _confirmed_order(client, application, email=f"calendar{i}@example.com") for i in range(2)
    ]
    with Session(application.state.engine) as db:
        tech = db.scalar(select(User).where(User.email == "tech@example.com"))
        tech_id = tech.id
        sales = db.scalar(select(User).where(User.email == "sales@example.com"))
        if policy:
            db.add(
                TechnicianAvailability(
                    technician_user_id=tech_id,
                    timezone="UTC",
                    working_hours={str(i): [["09:00", "17:00"]] for i in range(7)},
                    qualifications={"installation": "2031-01-01", "survey": "2031-01-01"},
                    daily_capacity=3,
                    recorded_by_user_id=sales.id,
                )
            )
            db.commit()
    jobs = []
    for order in orders:
        created = client.post(
            "/api/v1/jobs",
            json={"order_id": order["id"], "technician_user_id": str(tech_id)},
            headers=_sales(client),
        )
        assert created.status_code == 201, created.text
        jobs.append(created.json()["id"])
    return str(tech_id), jobs, _sales(client)


def _body(tech, job, start="2030-01-07T09:00:00Z", end="2030-01-07T10:00:00Z"):
    return dict(
        resource_type="installation",
        resource_id=job,
        technician_user_id=tech,
        starts_at=start,
        ends_at=end,
    )


def test_unknown_availability_fails_closed(client, application):
    tech, jobs, sales = _setup(client, application, False)
    result = client.post(
        "/api/v1/scheduling/appointments", json=_body(tech, jobs[0]), headers=sales
    )
    assert result.status_code == 409, result.text
    assert "not been declared" in result.json()["error"]["message"]


def test_overlap_rejected_adjacent_allowed_and_retry_returns_same_record(client, application):
    tech, jobs, sales = _setup(client, application)
    first = client.post("/api/v1/scheduling/appointments", json=_body(tech, jobs[0]), headers=sales)
    assert first.status_code == 200, first.text
    assert (
        client.post(
            "/api/v1/scheduling/appointments", json=_body(tech, jobs[0]), headers=sales
        ).json()["id"]
        == first.json()["id"]
    )
    assert (
        client.post(
            "/api/v1/scheduling/appointments", json=_body(tech, jobs[1]), headers=sales
        ).status_code
        == 409
    )
    second = client.post(
        "/api/v1/scheduling/appointments",
        json=_body(tech, jobs[1], "2030-01-07T10:00:00Z", "2030-01-07T11:00:00Z"),
        headers=sales,
    )
    assert second.status_code == 200, second.text
    blocked_leave = client.post(
        f"/api/v1/scheduling/leave/{tech}",
        json={
            "starts_at": "2030-01-07T09:00:00Z",
            "ends_at": "2030-01-07T10:00:00Z",
            "reason": "Approved leave request",
        },
        headers=sales,
    )
    assert blocked_leave.status_code == 409
    changed = _body(tech, jobs[1], "2030-01-07T11:00:00Z", "2030-01-07T12:00:00Z")
    assert (
        client.post("/api/v1/scheduling/appointments", json=changed, headers=sales).status_code
        == 422
    )
    changed["override_reason"] = "Customer asked to move the visit"
    assert (
        client.post("/api/v1/scheduling/appointments", json=changed, headers=sales).status_code
        == 200
    )


@pytest.mark.parametrize("failure", ["hours", "qualification", "leave", "capacity"])
def test_policy_constraints_are_not_overridden_by_reason(client, application, failure):
    tech, jobs, sales = _setup(client, application)
    with Session(application.state.engine) as db:
        policy = db.get(TechnicianAvailability, uuid.UUID(tech))
        if failure == "qualification":
            policy.qualifications = {"installation": "2029-01-01"}
        if failure == "capacity":
            policy.daily_capacity = 1
        db.commit()
    if failure == "leave":
        response = client.post(
            f"/api/v1/scheduling/leave/{tech}",
            json={
                "starts_at": "2030-01-07T09:00:00Z",
                "ends_at": "2030-01-07T11:00:00Z",
                "reason": "Approved leave fixture",
            },
            headers=sales,
        )
        assert response.status_code == 200, response.text
    if failure == "capacity":
        assert (
            client.post(
                "/api/v1/scheduling/appointments",
                json=_body(tech, jobs[1], "2030-01-07T10:00:00Z", "2030-01-07T11:00:00Z"),
                headers=sales,
            ).status_code
            == 200
        )
    body = (
        _body(tech, jobs[0], "2030-01-07T08:00:00Z", "2030-01-07T09:00:00Z")
        if failure == "hours"
        else _body(tech, jobs[0])
    )
    body["override_reason"] = "Explicit scheduling override request"
    assert (
        client.post("/api/v1/scheduling/appointments", json=body, headers=sales).status_code == 409
    )


def test_concurrent_bookings_serialize_for_same_technician(client, application):
    tech, jobs, _ = _setup(client, application)
    barrier = threading.Barrier(2)
    outcomes = []

    def worker(job):
        with Session(application.state.engine) as db:
            sales = db.scalar(select(User).where(User.email == "sales@example.com"))
            barrier.wait(timeout=10)
            try:
                calendar_service.book(db, sales, AppointmentInput.model_validate(_body(tech, job)))
                db.commit()
                outcomes.append("booked")
            except AppError as exc:
                db.rollback()
                outcomes.append(exc.code)

    threads = [threading.Thread(target=worker, args=(job,)) for job in jobs]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)
    assert all(not thread.is_alive() for thread in threads)
    assert sorted(outcomes) == ["booked", "technician_ineligible"]
    with Session(application.state.engine) as db:
        assert (
            len(
                list(
                    db.scalars(
                        select(TechnicianAppointment).where(
                            TechnicianAppointment.status == "booked"
                        )
                    )
                )
            )
            == 1
        )


def test_only_admin_can_record_qualifications(client, application):
    tech, _, sales = _setup(client, application, False)
    body = {
        "timezone": "Asia/Kolkata",
        "working_hours": {"0": [["09:00", "17:00"]]},
        "qualifications": {"installation": "2031-01-01"},
        "daily_capacity": 2,
    }
    assert (
        client.put("/api/v1/scheduling/availability/" + tech, json=body, headers=sales).status_code
        == 403
    )
    _staff(application, "admin", "calendar-admin@example.com", "EMP-ADMIN-901")
    from tests.test_phase3_warehouse_installation import _login

    admin = _login(client, "employee", "EMP-ADMIN-901", "Staffpass123")
    response = client.put("/api/v1/scheduling/availability/" + tech, json=body, headers=admin)
    assert response.status_code == 200, response.text
    body["working_hours"] = {"0": [["17:00", "09:00"]]}
    assert (
        client.put("/api/v1/scheduling/availability/" + tech, json=body, headers=admin).status_code
        == 422
    )
