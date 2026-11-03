"""Local configuration refuses live keys and does not create provider state."""

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from configure_local_razorpay import validate_credentials, verify_credentials  # noqa: E402


@pytest.mark.parametrize("key", ["", "rzp_live_neverAllowed", "rzp_test_", "rzp_test_bad\nkey"])
def test_local_provider_setup_refuses_live_or_invalid_key_before_network(key):
    def no_network(request):
        pytest.fail("Invalid configuration must not contact provider")

    with pytest.raises(ValueError):
        verify_credentials(key, "testSecret", transport=httpx.MockTransport(no_network))


@pytest.mark.parametrize("secret", ["", "bad\nsecret", "x" * 257])
def test_local_provider_configuration_rejects_malformed_secret(secret):
    with pytest.raises(ValueError):
        validate_credentials("rzp_test_example", secret)


@pytest.mark.parametrize(
    "status,payload,verified",
    [
        (200, {"entity": "collection", "items": []}, True),
        (401, {"error": "authentication failed"}, False),
        (500, {"error": "unavailable"}, False),
        (302, {"entity": "collection", "items": []}, False),
        (200, {"entity": "order"}, False),
        (200, [], False),
    ],
)
def test_provider_verification_uses_read_only_fixed_endpoint(status, payload, verified):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == "GET"
        assert str(request.url) == "https://api.razorpay.com/v1/orders?count=1"
        assert request.headers["Authorization"].startswith("Basic ")
        return httpx.Response(status, json=payload)

    assert (
        verify_credentials("rzp_test_example", "testSecret", httpx.MockTransport(handler))
        is verified
    )
    assert len(calls) == 1


def test_provider_network_timeout_is_reported_without_request_or_credential_details():
    def handler(request):
        raise httpx.ReadTimeout("private-provider-details", request=request)

    assert (
        verify_credentials("rzp_test_example", "testSecret", httpx.MockTransport(handler)) is False
    )
