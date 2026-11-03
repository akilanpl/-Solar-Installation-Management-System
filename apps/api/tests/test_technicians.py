"""Sales need a technician directory that does not expose contact details."""

from app.core.security import hash_password, utcnow
from app.models.identity import EmployeeProfile, User
from sqlalchemy.orm import Session
from tests.conftest import csrf_headers, login, signup_and_verify


def _person(application, role: str, email: str, code: str) -> None:
    with Session(application.state.engine) as db:
        user = User(
            email=email,
            password_hash=hash_password("Staffpass123"),
            role_code=role,
            email_verified_at=utcnow(),
            is_active=True,
        )
        db.add(user)
        db.flush()
        db.add(
            EmployeeProfile(
                user_id=user.id,
                employee_code=code,
                full_name=f"{role} person",
                phone="9845000099",
            )
        )
        db.commit()


def test_sales_lists_active_technicians_without_contact_details(client, application):
    _person(application, "sales", "sales@example.com", "EMP-SALES-901")
    _person(application, "technician", "tech@example.com", "EMP-TECH-901")
    _person(application, "warehouse_staff", "wh@example.com", "EMP-WH-901")
    signed = login(client, kind="employee", identifier="EMP-SALES-901", password="Staffpass123")
    assert signed.status_code == 200
    listed = client.get("/api/v1/technicians", headers=csrf_headers(client))
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert len(body) == 1
    assert body[0]["employee_code"] == "EMP-TECH-901"
    assert "email" not in body[0]
    assert "phone" not in body[0]


def test_customer_cannot_list_technicians(client, application):
    signup_and_verify(client, application, "leela@example.com")
    signed = login(client, kind="customer", identifier="leela@example.com", password="Solarops123")
    assert signed.status_code == 200
    listed = client.get("/api/v1/technicians", headers=csrf_headers(client))
    assert listed.status_code == 403
