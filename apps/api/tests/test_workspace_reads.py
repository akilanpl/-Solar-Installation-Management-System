"""Read models retain role boundaries and read actual persisted records."""
import pytest
from app.models.identity import User
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.test_phase3_warehouse_installation import (
    _all_staff,
    _customer,
    _receipt_validate,
    _sales,
    _technician,
    _warehouse,
)

pytestmark = pytest.mark.database
PATHS=["/api/v1/workspace/warehouse-catalogue","/api/v1/stock/operations","/api/v1/replenishment/requests","/api/v1/serials"]

@pytest.mark.parametrize("path",PATHS+["/api/v1/workspace/technicians"])
def test_workspace_reads_reject_anonymous(client,path):
    assert client.get(path).status_code==401

@pytest.mark.parametrize("path",PATHS+["/api/v1/workspace/technicians"])
def test_workspace_reads_reject_customer(client,application,path):
    _customer(client,application)
    assert client.get(path).status_code==403


def test_technician_directory_is_scoped_to_sales_and_omits_inactive_staff(client,application):
    _all_staff(application)
    rows=client.get("/api/v1/workspace/technicians",headers=_sales(client))
    assert rows.status_code==200
    assert len(rows.json())==1
    assert set(rows.json()[0])=={"id","full_name","employee_code"}
    with Session(application.state.engine) as db:
        tech=db.scalar(select(User).where(User.role_code=="technician"))
        tech.is_active=False
        db.commit()
    assert client.get("/api/v1/workspace/technicians").json()==[]


def test_warehouse_read_models_return_real_receipt_and_no_invented_serials(client,application):
    _all_staff(application)
    warehouse=_warehouse(client)
    assert client.get("/api/v1/stock/operations").json()==[]
    catalogue=client.get("/api/v1/workspace/warehouse-catalogue")
    assert catalogue.status_code==200
    assert any(c["code"]=="PANEL-550" for c in catalogue.json()["components"])
    assert any(location["code"]=="MAIN" for location in catalogue.json()["locations"])
    _receipt_validate(client,warehouse,"PANEL-550","3")
    records=client.get("/api/v1/stock/operations").json()
    assert len(records)==1
    assert records[0]["status"]=="done"
    assert records[0]["lines"][0]["component_code"]=="PANEL-550"
    assert client.get("/api/v1/serials").json()==[]
    assert client.get("/api/v1/replenishment/requests").json()==[]
    assert client.get("/api/v1/stock/operations",headers=_technician(client)).status_code==403


def test_exact_serial_query_finds_old_unit_and_normalizes_input(client, application):
    from datetime import timedelta

    from app.core.security import utcnow
    from app.models.phase3 import EquipmentSerial

    _all_staff(application)
    warehouse = _warehouse(client)
    receipt = _receipt_validate(client, warehouse, "PANEL-550", "201")
    with Session(application.state.engine) as db:
        for index in range(201):
            db.add(EquipmentSerial(
                serial_number=f"EXACT-READ-{index:03d}", component_code="PANEL-550",
                status="registered", location_code="MAIN", operation_id=receipt["id"],
                created_at=utcnow() + timedelta(seconds=index),
            ))
        db.commit()
    latest = client.get("/api/v1/serials").json()
    assert len(latest) == 200
    assert all(row["serial_number"] != "EXACT-READ-000" for row in latest)
    exact = client.get("/api/v1/serials", params={"serial_number": " exact-read-000 "})
    assert exact.status_code == 200
    assert [row["serial_number"] for row in exact.json()] == ["EXACT-READ-000"]
    assert client.get("/api/v1/serials", params={"serial_number": "EXACT-READ-MISSING"}).json() == []
    assert client.get("/api/v1/serials", params={"serial_number": " "}).status_code == 422
    _customer(client, application)
    assert client.get("/api/v1/serials", params={"serial_number": "EXACT-READ-000"}).status_code == 403
