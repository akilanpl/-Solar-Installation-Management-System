"""Phase 4E offline-first technician workflows.

The browser queue lives in IndexedDB (frontend tests); here the server
intake is exercised: idempotent replay, version conflicts, state rejection,
user isolation, forbidden actions and retry-safe evidence upload.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session
from tests.conftest import csrf_headers
from tests.test_phase4a_support import (
    _all_staff,
    _confirmed_order,
    _create_ticket,
    _customer,
    _enquiry,
    _qualify,
    _repair_job,
    _sales,
    _tech_id,
    _technician,
    _triage,
)

pytestmark = pytest.mark.database

JPEG = b"\xff\xd8\xff" + b"\x00" * 200


def _assigned_survey(client, application):
    _all_staff(application)
    customer = _customer(client, application, f"off-{uuid.uuid4().hex[:8]}@example.com")
    enquiry = _enquiry(client, customer)
    _qualify(client, enquiry["id"])
    sales = _sales(client)
    created = client.post(
        "/api/v1/surveys", json={"enquiry_id": enquiry["id"]}, headers=sales)
    assert created.status_code == 201, created.text
    survey = created.json()
    assigned = client.post(
        f"/api/v1/surveys/{survey['id']}/assignment",
        json={"technician_user_id": _tech_id(application, "tech@example.com")},
        headers=sales,
    )
    assert assigned.status_code == 200, assigned.text
    technician = _technician(client)
    started = client.post(f"/api/v1/surveys/{survey['id']}/start", headers=technician)
    assert started.status_code == 200, started.text
    return survey, technician


def _repair_setup(client, application):
    from tests.test_phase4a_support import _login as _login_user

    _all_staff(application)
    email = f"rep-{uuid.uuid4().hex[:8]}@example.com"
    order = _confirmed_order(client, application, email)
    customer = _login_user(client, "customer", email, "Solarops123")
    ticket = _create_ticket(client, customer, order["id"], serial=None)
    _triage(client, ticket["id"])
    job = _repair_job(client, ticket["id"], _tech_id(application, "tech@example.com"))
    technician = _technician(client)
    return ticket, job, technician


def _sync(client, headers, operations):
    response = client.post("/api/v1/offline/sync",
                           json={"operations": operations}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["verdicts"]


def _op(op_type, entity_id, client_id, payload, version=0):
    return {
        "op_type": op_type,
        "entity_type": "survey" if op_type in {"survey_draft", "measurement"} else "repair",
        "entity_id": entity_id,
        "client_operation_id": client_id,
        "base_field_version": version,
        "payload": payload,
    }


def test_offline_survey_draft_applies_and_replay_is_idempotent(client, application):
    survey, technician = _assigned_survey(client, application)
    client_id = f"op-{uuid.uuid4().hex[:16]}"
    verdicts = _sync(client, technician, [_op(
        "survey_draft", survey["id"], client_id,
        {"notes": "North roof shaded after 3pm.", "tilt_deg": 12.5})])
    assert verdicts[0]["status"] == "applied", verdicts
    assert verdicts[0]["result"]["field_version"] == 1
    # Same id, different payload: the stored verdict wins, the row is untouched.
    again = _sync(client, technician, [_op(
        "survey_draft", survey["id"], client_id,
        {"notes": "Tampered replay."})])
    assert again[0]["status"] == "applied"
    assert again[0]["duplicate"] is True
    assert again[0]["result"]["field_version"] == 1
    from app.models.workflow import Survey

    with Session(application.state.engine) as db:
        row = db.get(Survey, uuid.UUID(survey["id"]))
        assert row.notes == "North roof shaded after 3pm."
        assert row.field_version == 1
        assert row.status == "in_progress"


def test_offline_stale_version_conflicts_without_overwrite(client, application):
    survey, technician = _assigned_survey(client, application)
    first = _sync(client, technician, [_op(
        "survey_draft", survey["id"], f"op-{uuid.uuid4().hex[:16]}",
        {"notes": "First write."})])
    assert first[0]["status"] == "applied"
    stale = _sync(client, technician, [_op(
        "survey_draft", survey["id"], f"op-{uuid.uuid4().hex[:16]}",
        {"notes": "Stale write."}, version=0)])
    assert stale[0]["status"] == "conflict", stale
    from app.models.workflow import Survey

    with Session(application.state.engine) as db:
        assert db.get(Survey, uuid.UUID(survey["id"])).notes == "First write."


def test_offline_draft_rejected_once_survey_submitted(client, application):
    survey, technician = _assigned_survey(client, application)
    submitted = client.post(
        f"/api/v1/surveys/{survey['id']}/submission",
        json={"azimuth_deg": "180.00", "tilt_deg": "12.50",
              "shadow_free_area_sqm": "38.25", "cable_distance_m": "25.00",
              "grid_connection": "suitable", "notes": "Online submit."},
        headers=technician,
    )
    assert submitted.status_code == 200, submitted.text
    verdicts = _sync(client, technician, [_op(
        "survey_draft", survey["id"], f"op-{uuid.uuid4().hex[:16]}",
        {"notes": "Too late."})])
    assert verdicts[0]["status"] == "rejected", verdicts


def test_offline_measurement_rejects_non_measurement_fields(client, application):
    survey, technician = _assigned_survey(client, application)
    verdicts = _sync(client, technician, [_op(
        "measurement", survey["id"], f"op-{uuid.uuid4().hex[:16]}",
        {"notes": "Notes are not measurements.", "tilt_deg": 10.0})])
    assert verdicts[0]["status"] == "rejected", verdicts
    good = _sync(client, technician, [_op(
        "measurement", survey["id"], f"op-{uuid.uuid4().hex[:16]}",
        {"tilt_deg": 10.0, "grid_connection": "unknown"})])
    assert good[0]["status"] == "applied", good


def test_offline_repair_diagnostics_work_and_checklist(client, application):
    ticket, job, technician = _repair_setup(client, application)
    diagnostics = _sync(client, technician, [_op(
        "repair_diagnostics", job["id"], f"op-{uuid.uuid4().hex[:16]}",
        {"diagnostics": {"findings": "Isolator pitted.", "root_cause": "Wear"}})])
    assert diagnostics[0]["status"] == "applied", diagnostics
    assert diagnostics[0]["result"]["field_version"] == 1
    now = datetime.now(UTC)
    work = _sync(client, technician, [_op(
        "repair_work", job["id"], f"op-{uuid.uuid4().hex[:16]}",
        {"work_performed": "Replaced isolator.",
         "work_started_at": (now - timedelta(hours=2)).isoformat(),
         "work_finished_at": now.isoformat(),
         "parts_used": [{"component_code": "PANEL-550", "quantity": 1}]},
        version=1)])
    assert work[0]["status"] == "applied", work
    checklist = _sync(client, technician, [_op(
        "repair_checklist", job["id"], f"op-{uuid.uuid4().hex[:16]}",
        {"items": [{"key": "torque", "done": True},
                   {"key": "generation", "done": False, "note": "Cloudy"}]},
        version=2)])
    assert checklist[0]["status"] == "applied", checklist
    assert checklist[0]["result"]["checklist_keys"] == ["generation", "torque"]
    from app.models.support import TicketRepairJob

    with Session(application.state.engine) as db:
        row = db.get(TicketRepairJob, uuid.UUID(job["id"]))
        assert row.field_version == 3
        assert row.diagnostics["checklist"]["torque"]["done"] is True
        assert row.status == "in_progress"


def test_offline_repair_conflict_after_online_change(client, application):
    ticket, job, technician = _repair_setup(client, application)
    online = client.post(
        f"/api/v1/repair-jobs/{job['id']}/diagnostics",
        json={"findings": "Online note.", "root_cause": "X"}, headers=technician)
    assert online.status_code == 200, online.text
    # Online edits bump the shared version, so the stale offline base conflicts.
    verdicts = _sync(client, technician, [_op(
        "repair_diagnostics", job["id"], f"op-{uuid.uuid4().hex[:16]}",
        {"diagnostics": {"findings": "Stale offline note."}}, version=0)])
    assert verdicts[0]["status"] == "conflict", verdicts
    rebased = _sync(client, technician, [_op(
        "repair_diagnostics", job["id"], f"op-{uuid.uuid4().hex[:16]}",
        {"diagnostics": {"findings": "Rebased offline note."}}, version=1)])
    assert rebased[0]["status"] == "applied", rebased
    from app.models.support import TicketRepairJob

    with Session(application.state.engine) as db:
        row = db.get(TicketRepairJob, uuid.UUID(job["id"]))
        assert row.diagnostics["findings"] == "Rebased offline note."
        assert row.field_version == 2


def test_offline_batch_reports_mixed_verdicts(client, application):
    survey, technician = _assigned_survey(client, application)
    first = _sync(client, technician, [_op(
        "survey_draft", survey["id"], f"op-{uuid.uuid4().hex[:16]}",
        {"notes": "v1"})])
    assert first[0]["status"] == "applied"
    verdicts = _sync(client, technician, [
        _op("measurement", survey["id"], f"op-{uuid.uuid4().hex[:16]}",
            {"tilt_deg": 9.0}, version=1),
        _op("survey_draft", survey["id"], f"op-{uuid.uuid4().hex[:16]}",
            {"notes": "stale"}, version=0),
    ])
    assert [item["status"] for item in verdicts] == ["applied", "conflict"], verdicts


def test_offline_forbidden_actions_are_rejected(client, application):
    survey, technician = _assigned_survey(client, application)
    for forbidden in ("invoice_settlement", "ledger_posting", "warranty_decision",
                      "service_invoice", "payroll_settlement", "ticket_closure"):
        verdicts = _sync(client, technician, [{
            "op_type": forbidden, "entity_type": "survey", "entity_id": survey["id"],
            "client_operation_id": f"op-{uuid.uuid4().hex[:16]}",
            "base_field_version": 0, "payload": {},
        }])
        assert verdicts[0]["status"] == "rejected", (forbidden, verdicts)
        assert verdicts[0]["error"]["code"] == "forbidden_offline_action"


def test_offline_user_isolation_and_assignment_scope(client, application):
    from fastapi.testclient import TestClient

    survey, technician = _assigned_survey(client, application)
    from tests.test_phase4a_support import _technician2

    second = TestClient(application)
    other = _technician2(second)
    scope = second.get("/api/v1/offline/assignments", headers=other)
    assert scope.status_code == 200, scope.text
    assert scope.json()["surveys"] == []
    assert scope.json()["retention_days"] == 7
    # The second technician cannot touch the first technician's survey.
    verdicts = _sync(second, other, [_op(
        "survey_draft", survey["id"], f"op-{uuid.uuid4().hex[:16]}",
        {"notes": "Cross-user write."})])
    assert verdicts[0]["status"] == "rejected", verdicts
    mine = client.get("/api/v1/offline/assignments", headers=technician)
    assert len(mine.json()["surveys"]) == 1
    operations = client.get("/api/v1/offline/operations", headers=technician)
    assert operations.status_code == 200
    assert all(item["client_operation_id"] for item in operations.json())


def test_offline_evidence_upload_retries_idempotently(client, application):
    survey, technician = _assigned_survey(client, application)
    client_id = f"ev-{uuid.uuid4().hex[:16]}"
    first = client.post(
        "/api/v1/offline/evidence",
        files={"upload": ("roof.jpg", JPEG, "image/jpeg")},
        data={"client_operation_id": client_id, "target": "survey",
              "entity_id": survey["id"]},
        headers={key: value for key, value in technician.items()
                 if key.lower() != "content-type"},
    )
    assert first.status_code == 201, first.text
    evidence_id = first.json()["result"]["evidence_id"]
    retry = client.post(
        "/api/v1/offline/evidence",
        files={"upload": ("roof.jpg", JPEG, "image/jpeg")},
        data={"client_operation_id": client_id, "target": "survey",
              "entity_id": survey["id"]},
        headers={key: value for key, value in technician.items()
                 if key.lower() != "content-type"},
    )
    assert retry.status_code == 201, retry.text
    assert retry.json()["result"]["evidence_id"] == evidence_id
    assert retry.json()["duplicate"] is True
    from app.models.workflow import SurveyEvidence

    with Session(application.state.engine) as db:
        rows = db.query(SurveyEvidence).filter_by(survey_id=uuid.UUID(survey["id"])).all()
        assert len(rows) == 1


def test_offline_evidence_rejects_tampered_retry(client, application):
    survey, technician = _assigned_survey(client, application)
    client_id = f"ev-{uuid.uuid4().hex[:16]}"
    headers = {key: value for key, value in technician.items()
               if key.lower() != "content-type"}
    first = client.post(
        "/api/v1/offline/evidence",
        files={"upload": ("roof.jpg", JPEG, "image/jpeg")},
        data={"client_operation_id": client_id, "target": "survey",
              "entity_id": survey["id"]},
        headers=headers,
    )
    assert first.status_code == 201, first.text
    tampered = client.post(
        "/api/v1/offline/evidence",
        files={"upload": ("other.jpg", JPEG + b"1", "image/jpeg")},
        data={"client_operation_id": client_id, "target": "survey",
              "entity_id": survey["id"]},
        headers=headers,
    )
    assert tampered.status_code == 409, tampered.text


def test_offline_ticket_evidence_and_unauthenticated_rejected(client, application):
    ticket, job, technician = _repair_setup(client, application)
    uploaded = client.post(
        "/api/v1/offline/evidence",
        files={"upload": ("panel.jpg", JPEG, "image/jpeg")},
        data={"client_operation_id": f"ev-{uuid.uuid4().hex[:16]}",
              "target": "ticket", "entity_id": ticket["id"]},
        headers={key: value for key, value in technician.items()
                 if key.lower() != "content-type"},
    )
    assert uploaded.status_code == 201, uploaded.text
    from fastapi.testclient import TestClient

    anon = TestClient(application)
    assert anon.post("/api/v1/offline/sync", json={"operations": []},
                     headers=csrf_headers(anon)).status_code == 401
    assert anon.get("/api/v1/offline/assignments",
                    headers=csrf_headers(anon)).status_code == 401
