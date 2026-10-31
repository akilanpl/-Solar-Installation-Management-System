"""Provider transport is mocked here; no test below is a provider sandbox claim."""

import hashlib
import hmac
import json
import uuid

import httpx
import pytest
from app.models.provider import ProviderEvent, ProviderPaymentOrder
from app.models.workflow import PaymentIntent
from app.services import razorpay_service
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.test_phase3_warehouse_installation import (
    _all_staff,
    _customer,
    _enquiry,
    _login,
    _qualify,
    _quote,
    _survey_to_approved,
)

pytestmark = pytest.mark.database
SECRET = "fixture-secret-never-a-provider-key-0000"


def _setup(client, application, monkeypatch):
    _all_staff(application)
    customer = _customer(client, application)
    enquiry = _enquiry(client, customer)
    _qualify(client, enquiry["id"])
    survey = _survey_to_approved(client, application, enquiry["id"])
    quote = _quote(client, survey["id"])
    settings = application.state.settings
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_fixture")
    monkeypatch.setattr(settings, "razorpay_key_secret", SecretStr(SECRET))
    monkeypatch.setattr(settings, "razorpay_webhook_secret", SecretStr(SECRET))

    def request(settings, method, path, payload=None):
        assert method == "POST" and path == "/orders"
        return {"id": "order_Test001", **payload}

    monkeypatch.setattr(razorpay_service, "provider_request", request)
    headers = _login(client, "customer", "leela@example.com", "Solarops123")
    body = {"quotation_id": quote["id"], "amount_minor": quote["total_minor"]}
    return quote, headers, body


def _order(client, headers, body, key="provider-order-once"):
    result = client.post(
        "/api/v1/payments/razorpay/orders", json=body, headers={**headers, "Idempotency-Key": key}
    )
    assert result.status_code == 200, result.text
    return result.json()


def _event(order, amount=None, currency="INR", refunded=0, status="captured"):
    return {
        "event": "payment.captured" if status == "captured" else "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_Test001",
                    "order_id": order["provider_order_id"],
                    "amount": amount if amount is not None else order["payment"]["amount_minor"],
                    "currency": currency,
                    "status": status,
                    "captured": status == "captured",
                    "amount_refunded": refunded,
                }
            }
        },
    }


def _send(client, payload, event_id="evt_fixture1", valid=True):
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest() if valid else "0" * 64
    return client.post(
        "/api/v1/payments/razorpay/webhook",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
            "X-Razorpay-Event-Id": event_id,
        },
    )


def test_no_credentials_or_live_keys_fail_closed(client, application, monkeypatch):
    _all_staff(application)
    _customer(client, application)
    for key in [None, "rzp_live_forbidden"]:
        monkeypatch.setattr(application.state.settings, "razorpay_key_id", key)
        response = client.get("/api/v1/payments/razorpay/capability")
        assert response.json()["enabled"] is False
        result = client.post(
            "/api/v1/payments/razorpay/orders",
            json={"quotation_id": str(uuid.uuid4()), "amount_minor": 100},
            headers=_login(client, "customer", "leela@example.com", "Solarops123")
            | {"Idempotency-Key": uuid.uuid4().hex},
        )
        assert result.status_code == 503


def test_create_order_is_durable_idempotent_and_unverified(client, application, monkeypatch):
    quote, headers, body = _setup(client, application, monkeypatch)
    order = _order(client, headers, body)
    assert order["payment"]["status"] == "pending"
    assert order["payment"]["is_test_only"] is True
    assert _order(client, headers, body)["payment"]["id"] == order["payment"]["id"]
    assert (
        client.get("/api/v1/quotations/" + quote["id"] + "/payment-requirement").json()[
            "verified_minor"
        ]
        == 0
    )
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(ProviderPaymentOrder)) == 1
        assert db.scalar(select(func.count()).select_from(PaymentIntent)) == 1


def test_timeout_preserves_unknown_intent_and_never_retries_creation(
    client, application, monkeypatch
):
    _, headers, body = _setup(client, application, monkeypatch)
    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise httpx.ReadTimeout("isolated provider timeout")

    monkeypatch.setattr(razorpay_service, "provider_request", fail)
    first = _order(client, headers, body)
    second = _order(client, headers, body)
    assert first["payment"]["status"] == second["payment"]["status"] == "unresolved"
    assert first["provider_order_id"] is None
    assert len(calls) == 1


@pytest.mark.parametrize("failure", ["signature", "amount", "currency", "order"])
def test_webhook_rejects_invalid_provider_facts_without_posting(
    client, application, monkeypatch, failure
):
    _, headers, body = _setup(client, application, monkeypatch)
    order = _order(client, headers, body)
    payload = _event(
        order,
        amount=body["amount_minor"] + 1 if failure == "amount" else None,
        currency="USD" if failure == "currency" else "INR",
    )
    if failure == "order":
        payload["payload"]["payment"]["entity"]["order_id"] = "order_Unknown"
    result = _send(client, payload, valid=failure != "signature")
    assert result.status_code in {400, 409}, result.text
    with Session(application.state.engine) as db:
        assert db.scalar(select(PaymentIntent.status)) == "pending"
        assert db.scalar(select(func.count()).select_from(ProviderEvent)) == 0


def test_signed_capture_replay_refund_and_late_failure_preserve_financial_truth(
    client, application, monkeypatch
):
    quote, headers, body = _setup(client, application, monkeypatch)
    order = _order(client, headers, body)
    captured = _event(order)
    for _ in range(2):
        result = _send(client, captured)
        assert result.status_code == 200, result.text
    assert _send(client, _event(order, refunded=100), "evt_refund_observation").status_code == 200
    assert _send(client, _event(order, status="failed"), "evt_late_failure").status_code == 200
    requirement = client.get("/api/v1/quotations/" + quote["id"] + "/payment-requirement").json()
    assert requirement["verified_minor"] == body["amount_minor"] - 100
    with Session(application.state.engine) as db:
        assert db.scalar(select(PaymentIntent.status)) == "verified"
        assert db.scalar(select(func.count()).select_from(ProviderEvent)) == 3
    conflict = _send(client, _event(order, amount=body["amount_minor"] + 1))
    assert conflict.status_code == 409


def test_browser_callback_needs_signature_and_authenticated_provider_fetch(
    client, application, monkeypatch
):
    _, headers, body = _setup(client, application, monkeypatch)
    order = _order(client, headers, body)
    path = "/api/v1/payments/razorpay/" + order["payment"]["id"] + "/reconcile"
    invalid = client.post(
        path, json={"payment_id": "pay_Test001", "signature": "0" * 64}, headers=headers
    )
    assert invalid.status_code == 400
    signature = hmac.new(
        SECRET.encode(), (order["provider_order_id"] + "|pay_Test001").encode(), hashlib.sha256
    ).hexdigest()
    payload = {"payment_id": "pay_Test001", "signature": signature}

    def fetch(settings, method, path, payload=None):
        assert method == "GET" and path == "/payments/pay_Test001"
        return _event(order)["payload"]["payment"]["entity"]

    monkeypatch.setattr(razorpay_service, "provider_request", fetch)
    verified = client.post(path, json=payload, headers=headers)
    assert verified.status_code == 200, verified.text
    assert verified.json()["status"] == "verified"
    _customer(client, application, "provider-other@example.com")
    other_headers = _login(client, "customer", "provider-other@example.com", "Solarops123")
    assert client.post(path, json=payload, headers=other_headers).status_code == 404
