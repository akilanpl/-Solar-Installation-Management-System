"""The development UI cannot enable simulation on a production backend."""
import uuid

import pytest
from tests.conftest import csrf_headers, login, signup_and_verify
from tests.test_phase3_warehouse_installation import _all_staff, _technician

pytestmark = pytest.mark.database


def test_simulation_capability_requires_authentication(client):
    assert client.get('/api/v1/payments/sandbox/capability').status_code == 401


def test_production_capability_and_mutation_fail_closed(client, application, monkeypatch):
    signup_and_verify(client, application)
    assert login(client, kind='customer', identifier='customer@example.com', password='Solarops123').status_code == 200
    assert client.get('/api/v1/payments/sandbox/capability').json()['enabled'] is True
    monkeypatch.setattr(application.state.settings, 'app_env', 'production')
    assert client.get('/api/v1/payments/sandbox/capability').json()['enabled'] is False
    response = client.post('/api/v1/payments/intents', json={'quotation_id': str(uuid.uuid4()), 'amount_minor': 100}, headers={**csrf_headers(client), 'Idempotency-Key': 'production-simulation-denied'})
    assert response.status_code == 403
    assert response.json()['error']['code'] == 'sandbox_disabled'


def test_technician_never_receives_payment_simulation_capability(client, application):
    _all_staff(application)
    _technician(client)
    assert client.get('/api/v1/payments/sandbox/capability').json()['enabled'] is False
