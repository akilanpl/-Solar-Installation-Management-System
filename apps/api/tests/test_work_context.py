"""Work context inherits parent authorization and never invents a site or unit."""

import uuid

import pytest
from app.models.phase3 import EquipmentSerial
from app.models.workflow import SalesOrder
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.test_phase3_qa_regression import _job
from tests.test_phase3_warehouse_installation import _customer, _login, _staff, _technician

pytestmark = pytest.mark.database


def test_assigned_technician_and_owner_receive_only_persisted_context(client, application):
    job, order = _job(client, application)
    with Session(application.state.engine) as db:
        survey_id = str(db.get(SalesOrder, uuid.UUID(order["id"])).survey_id)
        expected = {
            unit.serial_number
            for unit in db.scalars(
                select(EquipmentSerial).where(EquipmentSerial.order_id == uuid.UUID(order["id"]))
            )
        }
    _technician(client)
    response = client.get(f"/api/v1/jobs/{job['id']}/site-context")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["contact_name"] == "Leela Nair"
    assert data["order_reference"] == order["reference"]
    assert data["site"]["line1"] == "12 Lake View Road"
    assert data["site"]["city"] == "Hyderabad"
    assert len(expected) == 7
    assert {unit["serial_number"] for unit in data["equipment"]} == expected
    assert all(unit["status"] == "delivered" for unit in data["equipment"])
    assert "password" not in str(data) and "phone" not in data and "email" not in data
    survey = client.get(f"/api/v1/surveys/{survey_id}/site-context")
    assert survey.status_code == 200, survey.text
    assert survey.json()["site"]["id"] == data["site"]["id"]
    _login(client, "customer", "leela@example.com", "Solarops123")
    assert client.get(f"/api/v1/jobs/{job['id']}/site-context").json() == data


def test_foreign_customers_and_technicians_cannot_read_site_context(client, application):
    job, order = _job(client, application)
    with Session(application.state.engine) as db:
        survey_id = str(db.get(SalesOrder, uuid.UUID(order["id"])).survey_id)
    _customer(client, application, "foreign-context@example.com")
    paths = [
        f"/api/v1/jobs/{job['id']}/site-context",
        f"/api/v1/surveys/{survey_id}/site-context",
    ]
    for path in paths:
        assert client.get(path).status_code == 404
    _staff(application, "technician", "context-foreign-tech@example.com", "EMP-TECH-902")
    _login(client, "employee", "EMP-TECH-902", "Staffpass123")
    for path in paths:
        assert client.get(path).status_code == 404
