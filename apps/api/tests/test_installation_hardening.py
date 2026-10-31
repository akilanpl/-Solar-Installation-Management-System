"""Security regressions against real disposable PostgreSQL and real uploaded files."""
import hashlib
import threading
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.errors import AppError
from app.models.identity import User
from app.models.phase3 import InstallationEvidence, InstallationJob, InstallationOtp
from app.services.installation_service import verify_customer_otp
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.test_phase3_qa_regression import _job
from tests.test_phase3_warehouse_installation import _login, _png, _technician, _uploaded_photo

pytestmark = pytest.mark.database


def prepared(client, application):
    job, order = _job(client, application)
    code = application.state.email_sender.messages[-1].code
    tech = _technician(client)
    assert client.post(f"/api/v1/jobs/{job['id']}/arrival", headers=tech).status_code == 200
    key = _uploaded_photo(client, job["id"], tech)
    body = {"photo_refs": [key], "installed_capacity_kw": "3", "test_readings": {"voc_v": 612},
            "started_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
            "finished_at": datetime.now(UTC).isoformat()}
    response = client.post(f"/api/v1/jobs/{job['id']}/evidence", json=body, headers=tech)
    assert response.status_code == 200, response.text
    return job, code, key, body


def customer(client):
    return _login(client, "customer", "leela@example.com", "Solarops123")


def test_code_is_not_in_staff_responses_and_is_keyed_and_bound(client, application):
    job, _ = _job(client, application)
    message = application.state.email_sender.messages[-1]
    assert message.recipient == "leela@example.com"
    assert job["customer_code"] is None
    assert message.code not in str(job)
    with Session(application.state.engine) as db:
        challenge = db.scalar(select(InstallationOtp).where(InstallationOtp.job_id == uuid.UUID(job["id"])))
        assert challenge.code_hash != hashlib.sha256(message.code.encode()).hexdigest()
    assert client.get(f"/api/v1/jobs/{job['id']}").json()["customer_code"] is None


def test_rejected_attempt_commits_only_security_state(client, application):
    job, _ = _job(client, application)
    with Session(application.state.engine) as db:
        technician = db.scalar(select(User).where(User.email == "tech@example.com"))
        technician.is_active = False  # unrelated caller mutation must never be committed
        with pytest.raises(AppError, match="Wrong customer code"):
            verify_customer_otp(db, technician, uuid.UUID(job["id"]), "000000")
        db.rollback()
    with Session(application.state.engine) as db:
        assert db.scalar(select(User.is_active).where(User.email == "tech@example.com")) is True
        assert db.scalar(select(InstallationOtp.attempt_count).where(InstallationOtp.job_id == uuid.UUID(job["id"]))) == 1


def test_simultaneous_otp_consumption_succeeds_once(client, application):
    job, _ = _job(client, application)
    code = application.state.email_sender.messages[-1].code
    barrier = threading.Barrier(2)
    results = []
    def verify():
        with Session(application.state.engine) as db:
            tech = db.scalar(select(User).where(User.email == "tech@example.com"))
            barrier.wait(timeout=5)
            try:
                verify_customer_otp(db, tech, uuid.UUID(job["id"]), code)
                db.commit()
                results.append("accepted")
            except AppError as exc:
                db.rollback()
                results.append(exc.code)
    threads = [threading.Thread(target=verify) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
        assert not thread.is_alive()
    assert sorted(results) == ["accepted", "otp_missing"]


@pytest.mark.parametrize("payload", [b"", b"not an image", b"\x89PNG\r\n\x1a\nfake", b"%PDF-1.7 fake"])
def test_invalid_uploads_reject_content_without_metadata(client, application, payload):
    job, _ = _job(client, application)
    response = client.post(f"/api/v1/jobs/{job['id']}/uploads", files={"upload": ("roof.png", payload, "image/png")}, headers=_technician(client))
    assert response.status_code == 422
    with Session(application.state.engine) as db:
        assert db.scalar(select(InstallationEvidence.id)) is None


def test_upload_size_and_customer_authorization(client, application, monkeypatch):
    job, _ = _job(client, application)
    monkeypatch.setattr(application.state.settings, "evidence_max_bytes", 8)
    path = f"/api/v1/jobs/{job['id']}/uploads"
    response = client.post(path, files={"upload": ("roof.png", _png(), "image/png")}, headers=_technician(client))
    assert response.status_code == 413
    response = client.post(path, files={"upload": ("roof.png", _png(), "image/png")}, headers=customer(client))
    assert response.status_code == 403


def test_upload_custody_hash_and_foreign_customer_denial(client, application):
    job, _, key, _ = prepared(client, application)
    with Session(application.state.engine) as db:
        row = db.scalar(select(InstallationEvidence).where(InstallationEvidence.storage_key == key))
        assert str(row.job_id) == job["id"]
        assert row.created_at is not None
        assert row.sha256 == hashlib.sha256(_png()).hexdigest()
    assert client.get(f"/api/v1/jobs/{job['id']}/uploads/{key}").content == _png()
    from tests.test_phase3_warehouse_installation import _customer
    _customer(client, application, "foreign-evidence@example.com")
    assert client.get(f"/api/v1/jobs/{job['id']}/uploads/{key}").status_code == 404
    assert client.get(f"/api/v1/jobs/{job['id']}/work-summary").status_code == 404


def test_arbitrary_photo_reference_rejected(client, application):
    job, _, _, body = prepared(client, application)
    body["photo_refs"] = ["../../fake-photo"]
    response = client.post(f"/api/v1/jobs/{job['id']}/evidence", json=body, headers=_technician(client))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_evidence"


@pytest.mark.parametrize("patch", [
    {"installed_capacity_kw": "0"}, {"test_readings": {}}, {"test_readings": {"voc_v": -1}},
    {"test_readings": {"voc_v": 1501}}, {"finished_at": "2000-01-01T00:00:00Z"},
    {"finished_at": "2099-01-01T00:00:00Z"},
])
def test_invalid_work_measurements_rejected(client, application, patch):
    job, _, _, body = prepared(client, application)
    response = client.post(f"/api/v1/jobs/{job['id']}/evidence", json={**body, **patch}, headers=_technician(client))
    assert response.status_code == 422


def test_technician_cannot_sign_and_customer_cannot_replay_or_change_summary(client, application):
    job, code, _, body = prepared(client, application)
    path = f"/api/v1/jobs/{job['id']}"
    summary = client.get(f"{path}/work-summary").json()
    signature = {"signature_ref": "Leela Nair", "customer_confirmed": True, "summary_hash": summary["summary_hash"]}
    assert client.post(f"{path}/signature", json=signature, headers=_technician(client)).status_code == 403
    owner = customer(client)
    assert client.post(f"{path}/signature", json={**signature, "summary_hash": "0" * 64}, headers=owner).status_code == 409
    signed = client.post(f"{path}/signature", json=signature, headers=owner)
    assert signed.status_code == 200
    assert signed.json()["signature"]["customer_user_id"]
    assert signed.json()["signature"]["payload_hmac"]
    assert client.post(f"{path}/signature", json=signature, headers=owner).status_code == 409
    tech = _technician(client)
    assert client.post(f"{path}/evidence", json=body, headers=tech).status_code == 409
    assert client.post(f"{path}/customer-otp", json={"code": code}, headers=tech).status_code == 200
    assert client.post(f"{path}/completion", headers=tech).json()["status"] == "completed"
    assert client.post(f"{path}/completion", headers=tech).status_code == 409


def test_modified_stored_file_rejected_before_download_and_completion(client, application):
    job, _, key, _ = prepared(client, application)
    target = application.state.settings.evidence_path / key
    target.write_bytes(b"modified")
    response = client.get(f"/api/v1/jobs/{job['id']}/uploads/{key}")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "evidence_modified"
    assert client.get(f"/api/v1/jobs/{job['id']}/work-summary").status_code == 409
    with Session(application.state.engine) as db:
        assert db.get(InstallationJob, uuid.UUID(job["id"])).completed_at is None


def test_email_rejected_attempt_does_not_commit_pending_business_changes(client, application):
    from app.services.auth_service import verify_email
    from tests.conftest import csrf_headers
    response = client.post("/api/v1/auth/signup", json={"full_name": "Release Test", "email": "isolated-email@example.com", "phone": "9845099999", "password": "Solarops123"}, headers=csrf_headers(client))
    assert response.status_code == 201
    wrong_code = "000000" if application.state.email_sender.messages[-1].code != "000000" else "000001"
    with Session(application.state.engine) as db:
        user = db.scalar(select(User).where(User.email == "isolated-email@example.com"))
        user.is_active = False
        with pytest.raises(AppError):
            verify_email(db, application.state.settings, user.email, wrong_code)
        db.rollback()
    with Session(application.state.engine) as db:
        assert db.scalar(select(User.is_active).where(User.email == "isolated-email@example.com")) is True


def test_evidence_cannot_be_reused_on_another_job(client, application):
    from tests.test_phase3_warehouse_installation import _confirmed_order, _sales
    first, _, key, body = prepared(client, application)
    other_order = _confirmed_order(client, application, "other-install@example.com")
    with Session(application.state.engine) as db:
        technician_id = db.scalar(select(User.id).where(User.email == "tech@example.com"))
    second = client.post("/api/v1/jobs", json={"order_id": other_order["id"], "technician_user_id": str(technician_id)}, headers=_sales(client))
    assert second.status_code == 201
    second_id = second.json()["id"]
    response = client.post(f"/api/v1/jobs/{second_id}/evidence", json=body, headers=_technician(client))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_evidence"
    assert client.get(f"/api/v1/jobs/{second_id}/uploads/{key}").status_code == 404
    assert first["id"] != second_id


def test_only_customer_can_reissue_code_and_old_code_is_revoked(client, application):
    job, _ = _job(client, application)
    old_code = application.state.email_sender.messages[-1].code
    path = f"/api/v1/jobs/{job['id']}/verification-code/request"
    assert client.post(path, headers=_technician(client)).status_code == 403
    assert client.post(path, headers=customer(client)).status_code == 429
    with Session(application.state.engine) as db:
        challenge = db.scalar(select(InstallationOtp).where(InstallationOtp.job_id == uuid.UUID(job["id"])))
        challenge.created_at = datetime.now(UTC) - timedelta(minutes=2)
        db.commit()
    response = client.post(path, headers=customer(client))
    assert response.status_code == 200
    new_code = application.state.email_sender.messages[-1].code
    assert new_code not in response.text
    assert "Delivery is not confirmed" in response.json()["message"]
    # Compare stored hashes, avoiding the one-in-a-million random code collision.
    with Session(application.state.engine) as db:
        rows = list(db.scalars(select(InstallationOtp).where(InstallationOtp.job_id == uuid.UUID(job["id"])).order_by(InstallationOtp.created_at)))
        assert len(rows) == 2
        assert rows[0].consumed_at is not None
        assert rows[1].consumed_at is None
    tech = _technician(client)
    if old_code != new_code:
        assert client.post(f"/api/v1/jobs/{job['id']}/customer-otp", json={"code": old_code}, headers=tech).status_code == 400
    assert client.post(f"/api/v1/jobs/{job['id']}/customer-otp", json={"code": new_code}, headers=tech).status_code == 200
