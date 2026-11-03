"""Reject unsafe configuration and malformed identity/pricing inputs."""

from decimal import ROUND_HALF_UP, Decimal

import pytest
from app.core.config import Settings
from app.domain.bom import extra_wire_bundles
from app.domain.pricing import advance_minor, maximum_discount_minor, price_quote, tax_minor
from app.schemas import SignupRequest
from pydantic import ValidationError

SIGNUP = {
    "full_name": "Leela Nair",
    "email": "leela@example.com",
    "phone": "9845099999",
    "password": "Solarops123",
}


@pytest.mark.parametrize(
    "field,value",
    [
        ("full_name", " \t\n"),
        ("full_name", "a" * 81),
        ("phone", "1234567890"),
        ("phone", "984509999"),
        ("phone", "+919845099999"),
        ("password", "Abc123"),
        ("password", "a" * 129 + "1"),
        ("password", "lettersOnly"),
        ("password", "12345678901"),
        ("email", "missing-at-sign"),
        ("role_code", "admin"),
    ],
)
def test_signup_rejects_invalid_identity_or_privilege_fields(field, value):
    with pytest.raises(ValidationError):
        SignupRequest.model_validate({**SIGNUP, field: value})


def test_signup_normalizes_name_and_email_without_changing_password():
    request = SignupRequest.model_validate(
        {**SIGNUP, "full_name": "  Leela \t Nair ", "email": "LEELA@example.com"}
    )
    assert request.full_name == "Leela Nair"
    assert request.email == "leela@example.com"
    assert request.password == SIGNUP["password"]


@pytest.mark.parametrize(
    "options",
    [
        {"app_env": "staging-typo"},
        {"gst_rate_bps": -1},
        {"gst_rate_bps": 2801},
        {"advance_percent": 0},
        {"advance_percent": 101},
        {"app_env": "production", "cookie_secure": False},
        {"app_env": "production", "cookie_secure": True, "trusted_origins": "http://local"},
        {
            "app_env": "production",
            "cookie_secure": True,
            "trusted_origins": "https://*.example.com",
        },
        {"app_env": "production", "cookie_secure": True, "trusted_origins": ""},
        {"app_env": "production", "secret_key": "replace-with-a-random-32-byte-development-secret"},
    ],
)
def test_configuration_rejects_unsafe_or_out_of_range_values(options):
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {
                "database_url": "postgresql+psycopg://invalid/solarops_test",
                "secret_key": "boundary-test-only-configuration-key",
                **options,
            }
        )


@pytest.mark.parametrize("amount,rate", [(-1, 1800), (100, -1), (100, 2801)])
def test_tax_rejects_negative_amounts_and_invalid_rates(amount, rate):
    with pytest.raises(ValueError):
        tax_minor(amount, rate)


def test_tax_rounding_matches_decimal_half_up_at_paise_boundaries():
    for amount in (0, 1, 2, 3, 25, 99, 100, 101, 99999999):
        for rate in (0, 500, 1200, 1800, 2800):
            expected = (Decimal(amount) * Decimal(rate) / Decimal(10000)).quantize(
                Decimal(1), rounding=ROUND_HALF_UP
            )
            assert tax_minor(amount, rate) == int(expected)


@pytest.mark.parametrize("percent", [0, -1, 101])
def test_advance_rejects_invalid_percent(percent):
    with pytest.raises(ValueError):
        advance_minor(10000, percent)


def test_discount_and_wire_distance_reject_negative_values():
    with pytest.raises(ValueError):
        maximum_discount_minor(-1)
    with pytest.raises(ValueError):
        extra_wire_bundles(Decimal("-0.01"))
    with pytest.raises(ValueError):
        price_quote(
            material_cost_minor=700,
            material_total_minor=1000,
            installation_total_minor=200,
            discount_minor=-1,
            tax_rate_bps=1800,
        )


def test_quote_preserves_cost_and_accepts_exact_discount_limit():
    quote = price_quote(
        material_cost_minor=700,
        material_total_minor=1000,
        installation_total_minor=200,
        discount_minor=120,
        tax_rate_bps=1800,
    )
    assert quote.material_cost_minor == 700
    assert quote.discount_minor == 120
    assert quote.tax_minor == 194
    assert quote.total_minor == 1274
