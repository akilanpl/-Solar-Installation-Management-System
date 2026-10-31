"""Unknown records, whitespace-only reasons and missing role authority fail closed."""

import uuid

import pytest
from tests.test_phase3_warehouse_installation import (
    _all_staff,
    _customer,
    _manager,
    _sales,
    _warehouse,
)

pytestmark = pytest.mark.database


@pytest.mark.parametrize(
    "path,body,role",
    [
        (
            "/stock/allocations",
            {
                "order_id": str(uuid.UUID(int=1)),
                "lines": [{"component_code": "PANEL-550", "location_code": "SITE", "quantity": 1}],
            },
            "warehouse",
        ),
        (
            "/stock/returns",
            {
                "delivery_line_id": str(uuid.UUID(int=1)),
                "quantity": 1,
                "reason": "Isolated unknown line",
            },
            "warehouse",
        ),
        (
            "/stock/returns/" + str(uuid.UUID(int=1)) + "/inspection",
            {"disposition": "restock", "note": "Isolated inspected item"},
            "manager",
        ),
        (
            "/procurement/orders",
            {
                "replenishment_request_id": str(uuid.UUID(int=1)),
                "supplier_name": "Isolated supplier",
                "supplier_reference": "TEST-UNKNOWN",
            },
            "manager",
        ),
        (
            "/procurement/orders/" + str(uuid.UUID(int=1)) + "/receipt",
            {"operation_id": str(uuid.UUID(int=1))},
            "warehouse",
        ),
        (
            "/scheduling/appointments",
            {
                "resource_type": "installation",
                "resource_id": str(uuid.UUID(int=1)),
                "technician_user_id": str(uuid.UUID(int=1)),
                "starts_at": "2030-01-07T09:00:00Z",
                "ends_at": "2030-01-07T10:00:00Z",
            },
            "sales",
        ),
    ],
)
def test_unknown_operational_records_are_not_fabricated(client, application, path, body, role):
    _all_staff(application)
    headers = {"warehouse": _warehouse, "manager": _manager, "sales": _sales}[role](client)
    result = client.post(
        "/api/v1" + path, json=body, headers={**headers, "Idempotency-Key": uuid.uuid4().hex}
    )
    assert result.status_code == 404, result.text


@pytest.mark.parametrize(
    "path,body",
    [
        (
            "/stock/returns",
            {"delivery_line_id": str(uuid.UUID(int=1)), "quantity": 1, "reason": "     "},
        ),
        (
            "/stock/returns/" + str(uuid.UUID(int=1)) + "/inspection",
            {"disposition": "damaged", "note": "     "},
        ),
        (
            "/procurement/orders",
            {
                "replenishment_request_id": str(uuid.UUID(int=1)),
                "supplier_name": "  ",
                "supplier_reference": "REFERENCE",
            },
        ),
        (
            "/scheduling/appointments",
            {
                "resource_type": "survey",
                "resource_id": str(uuid.UUID(int=1)),
                "technician_user_id": str(uuid.UUID(int=1)),
                "starts_at": "2030-01-07T09:00:00Z",
                "ends_at": "2030-01-07T10:00:00Z",
                "override_reason": "     ",
            },
        ),
    ],
)
def test_whitespace_cannot_be_used_as_a_business_reason(client, application, path, body):
    _all_staff(application)
    result = client.post(
        "/api/v1" + path,
        json=body,
        headers={**_manager(client), "Idempotency-Key": uuid.uuid4().hex},
    )
    assert result.status_code == 422, result.text


@pytest.mark.parametrize(
    "path",
    ["/scheduling/appointments", "/warranty-policies", "/stock/returns", "/procurement/orders"],
)
def test_customer_cannot_enumerate_operational_or_policy_records(client, application, path):
    _customer(client, application)
    assert client.get("/api/v1" + path).status_code == 403
