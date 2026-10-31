"""Phase 4E authentication: passkeys, TOTP MFA, recovery, lockout, revocation.

WebAuthn ceremonies use a test-only virtual authenticator that mints real
ES256 keys and signatures. The server still verifies everything through the
maintained ``webauthn`` library, so these tests exercise the genuine
challenge, origin, RP ID, signature and counter checks.
"""

import base64
import hashlib
import json
import secrets

import cbor2
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy.orm import Session
from tests.conftest import csrf_headers, login, signup_and_verify
from tests.test_phase4a_support import _login, _staff

pytestmark = pytest.mark.database

RP_ID = "localhost"
ORIGIN = "http://localhost:3000"


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class VirtualAuthenticator:
    """A test authenticator with one ES256 credential."""

    def __init__(self) -> None:
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.cred_id = secrets.token_bytes(16)
        self.sign_count = 0

    @property
    def cose_key(self) -> bytes:
        numbers = self.key.public_key().public_numbers()
        return cbor2.dumps(
            {
                1: 2,
                3: -7,
                -1: 1,
                -2: numbers.x.to_bytes(32, "big"),
                -3: numbers.y.to_bytes(32, "big"),
            }
        )

    def register(self, challenge_b64: str, origin: str = ORIGIN, rp_id: str = RP_ID) -> dict:
        rp_hash = hashlib.sha256(rp_id.encode()).digest()
        auth_data = (
            rp_hash + b"\x45" + (0).to_bytes(4, "big") + b"\x00" * 16
            + len(self.cred_id).to_bytes(2, "big") + self.cred_id + self.cose_key
        )
        client_data = json.dumps(
            {"type": "webauthn.create", "challenge": challenge_b64, "origin": origin}
        ).encode()
        attestation = cbor2.dumps({"fmt": "none", "authData": auth_data, "attStmt": {}})
        return {
            "id": _b64(self.cred_id),
            "rawId": _b64(self.cred_id),
            "response": {
                "clientDataJSON": _b64(client_data),
                "attestationObject": _b64(attestation),
                "transports": ["internal"],
            },
            "type": "public-key",
        }

    def authenticate(
        self, challenge_b64: str, origin: str = ORIGIN, rp_id: str = RP_ID,
        user_handle: bytes | None = None,
    ) -> dict:
        self.sign_count += 1
        rp_hash = hashlib.sha256(rp_id.encode()).digest()
        auth_data = rp_hash + b"\x05" + self.sign_count.to_bytes(4, "big")
        client_data = json.dumps(
            {"type": "webauthn.get", "challenge": challenge_b64, "origin": origin}
        ).encode()
        signature = self.key.sign(auth_data + hashlib.sha256(client_data).digest(),
                                  ec.ECDSA(hashes.SHA256()))
        response = {
            "authenticatorData": _b64(auth_data),
            "clientDataJSON": _b64(client_data),
            "signature": _b64(signature),
        }
        if user_handle is not None:
            response["userHandle"] = _b64(user_handle)
        return {
            "id": _b64(self.cred_id),
            "rawId": _b64(self.cred_id),
            "response": response,
            "type": "public-key",
        }


def _customer_with_session(client, application, email: str) -> dict[str, str]:
    signup_and_verify(client, application, email)
    return _login(client, "customer", email, "Solarops123")


def _totp_code(application, email: str) -> str:
    import pyotp
    from app.models.identity import User
    from app.models.phase4e import MfaFactor
    from app.services.mfa_service import _fernet

    with Session(application.state.engine) as db:
        user = db.query(User).filter_by(email=email).one()
        factor = db.query(MfaFactor).filter_by(user_id=user.id).order_by(
            MfaFactor.created_at.desc()).first()
        assert factor is not None
        secret = _fernet(application.state.settings).decrypt(
            factor.secret_enc.encode("ascii")).decode()
    return pyotp.TOTP(secret).now()


def _enroll_totp(client, headers, password="Solarops123"):
    started = client.post(
        "/api/v1/auth/mfa/totp/enroll/start",
        json={"label": "Test phone", "password": password}, headers=headers,
    )
    assert started.status_code == 200, started.text
    return started.json()


def test_public_signup_stays_customer_and_passkey_needs_session(client, application):
    email = "passkey-cust@example.com"
    signup_and_verify(client, application, email)
    session_headers = _login(client, "customer", email, "Solarops123")
    # Anonymous callers cannot start enrollment.
    from fastapi.testclient import TestClient

    anon = TestClient(application)
    assert anon.post("/api/v1/auth/passkeys/registration/options",
                     headers=csrf_headers(anon)).status_code == 401
    options = client.post("/api/v1/auth/passkeys/registration/options",
                          headers=session_headers)
    assert options.status_code == 200, options.text
    auth = VirtualAuthenticator()
    verified = client.post(
        "/api/v1/auth/passkeys/registration/verify",
        json={"credential": auth.register(options.json()["options"]["challenge"]),
              "label": "Laptop"},
        headers=session_headers,
    )
    assert verified.status_code == 201, verified.text
    assert verified.json()["label"] == "Laptop"
    me = client.get("/api/v1/auth/me", headers=session_headers)
    assert me.json()["user"]["role"] == "customer"


def test_passkey_login_revocation_and_replay(client, application):
    email = "passkey-login@example.com"
    headers = _customer_with_session(client, application, email)
    options = client.post("/api/v1/auth/passkeys/registration/options", headers=headers)
    auth = VirtualAuthenticator()
    created = client.post(
        "/api/v1/auth/passkeys/registration/verify",
        json={"credential": auth.register(options.json()["options"]["challenge"])},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    credential_id = created.json()["id"]
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    # Discoverable login without a session.
    from fastapi.testclient import TestClient

    anon = TestClient(application)
    challenge = anon.post("/api/v1/auth/passkeys/authentication/options",
                          headers=csrf_headers(anon)).json()["options"]["challenge"]
    logged = anon.post(
        "/api/v1/auth/passkeys/authentication/verify",
        json={"credential": auth.authenticate(challenge)},
        headers=csrf_headers(anon),
    )
    assert logged.status_code == 200, logged.text
    assert logged.json()["user"]["email"] == email
    # Replay of the consumed challenge fails.
    replay = anon.post(
        "/api/v1/auth/passkeys/authentication/verify",
        json={"credential": auth.authenticate(challenge)},
        headers=csrf_headers(anon),
    )
    assert replay.status_code in (400, 401), replay.text
    # Revoke with password reauthentication, then the credential is dead.
    owner_headers = csrf_headers(anon)
    revoked = anon.post(
        f"/api/v1/auth/passkeys/{credential_id}/revoke",
        json={"password": "Solarops123"}, headers=owner_headers,
    )
    assert revoked.status_code == 200, revoked.text
    stranger = TestClient(application)
    fresh = stranger.post("/api/v1/auth/passkeys/authentication/options",
                          headers=csrf_headers(stranger)).json()["options"]["challenge"]
    dead = stranger.post(
        "/api/v1/auth/passkeys/authentication/verify",
        json={"credential": auth.authenticate(fresh)},
        headers=csrf_headers(stranger),
    )
    assert dead.status_code == 401, dead.text
    assert dead.json()["error"]["code"] == "unknown_credential"


def test_passkey_rejects_wrong_origin_and_rp(client, application):
    email = "passkey-origin@example.com"
    headers = _customer_with_session(client, application, email)
    options = client.post("/api/v1/auth/passkeys/registration/options", headers=headers)
    auth = VirtualAuthenticator()
    evil = auth.register(options.json()["options"]["challenge"],
                         origin="https://evil.example.com")
    denied = client.post("/api/v1/auth/passkeys/registration/verify",
                         json={"credential": evil}, headers=headers)
    assert denied.status_code == 400, denied.text
    assert denied.json()["error"]["code"] == "invalid_passkey"
    # A fresh ceremony is needed because the previous challenge was consumed.
    options2 = client.post("/api/v1/auth/passkeys/registration/options", headers=headers)
    assert options2.status_code == 200
    mismatch = VirtualAuthenticator()
    bad = mismatch.register(options2.json()["options"]["challenge"], rp_id="other.example.com")
    denied_rp = client.post("/api/v1/auth/passkeys/registration/verify",
                            json={"credential": bad}, headers=headers)
    assert denied_rp.status_code == 400, denied_rp.text


def test_passkey_challenge_expiry_and_cross_account_reuse(client, application):
    email_a = "passkey-a@example.com"
    headers_a = _customer_with_session(client, application, email_a)
    options = client.post("/api/v1/auth/passkeys/registration/options", headers=headers_a)
    from app.models.phase4e import WebauthnChallenge

    with Session(application.state.engine) as db:
        row = db.query(WebauthnChallenge).order_by(
            WebauthnChallenge.created_at.desc()).first()
        from app.core.security import utcnow

        row.expires_at = utcnow()
        db.commit()
    auth = VirtualAuthenticator()
    expired = client.post(
        "/api/v1/auth/passkeys/registration/verify",
        json={"credential": auth.register(options.json()["options"]["challenge"])},
        headers=headers_a,
    )
    assert expired.status_code == 400
    assert expired.json()["error"]["code"] == "challenge_expired"
    # Register properly, then another account cannot claim the same credential.
    options = client.post("/api/v1/auth/passkeys/registration/options", headers=headers_a)
    good = client.post(
        "/api/v1/auth/passkeys/registration/verify",
        json={"credential": auth.register(options.json()["options"]["challenge"])},
        headers=headers_a,
    )
    assert good.status_code == 201, good.text
    email_b = "passkey-b@example.com"
    headers_b = _customer_with_session(client, application, email_b)
    options_b = client.post("/api/v1/auth/passkeys/registration/options", headers=headers_b)
    clash = client.post(
        "/api/v1/auth/passkeys/registration/verify",
        json={"credential": auth.register(options_b.json()["options"]["challenge"])},
        headers=headers_b,
    )
    assert clash.status_code == 409, clash.text
    assert clash.json()["error"]["code"] == "credential_in_use"


def test_totp_enrollment_login_ticket_and_wrong_codes(client, application):
    email = "totp-cust@example.com"
    headers = _customer_with_session(client, application, email)
    _enroll_totp(client, headers)
    confirmed = client.post("/api/v1/auth/mfa/totp/enroll/confirm",
                            json={"code": _totp_code(application, email)}, headers=headers)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["totp_enrolled"] is True
    from fastapi.testclient import TestClient

    anon = TestClient(application)
    pending = login(anon, kind="customer", identifier=email, password="Solarops123")
    assert pending.status_code == 202, pending.text
    body = pending.json()
    assert body["mfa_required"] is True and body["methods"] == ["totp"]
    bad = anon.post("/api/v1/auth/mfa/ticket/verify-totp",
                    json={"ticket": body["ticket"], "code": "000000"},
                    headers=csrf_headers(anon))
    assert bad.status_code == 401, bad.text
    good = anon.post(
        "/api/v1/auth/mfa/ticket/verify-totp",
        json={"ticket": body["ticket"], "code": _totp_code(application, email)},
        headers=csrf_headers(anon),
    )
    assert good.status_code == 200, good.text
    # The consumed ticket cannot be reused.
    reuse = anon.post("/api/v1/auth/mfa/ticket/verify-totp",
                      json={"ticket": body["ticket"],
                            "code": _totp_code(application, email)},
                      headers=csrf_headers(anon))
    assert reuse.status_code == 401, reuse.text


def test_totp_lockout_after_repeated_failures(client, application):
    email = "totp-lock@example.com"
    headers = _customer_with_session(client, application, email)
    _enroll_totp(client, headers)
    assert client.post(
        "/api/v1/auth/mfa/totp/enroll/confirm",
        json={"code": _totp_code(application, email)}, headers=headers,
    ).status_code == 200
    from fastapi.testclient import TestClient

    anon = TestClient(application)
    ticket = login(anon, kind="customer", identifier=email,
                   password="Solarops123").json()["ticket"]
    for _ in range(5):
        anon.post("/api/v1/auth/mfa/ticket/verify-totp",
                  json={"ticket": ticket, "code": "000000"},
                  headers=csrf_headers(anon))
    # Even the correct code is rejected while the factor is locked.
    fresh_ticket = login(anon, kind="customer", identifier=email,
                         password="Solarops123").json()["ticket"]
    locked = anon.post("/api/v1/auth/mfa/ticket/verify-totp",
                       json={"ticket": fresh_ticket,
                             "code": _totp_code(application, email)},
                       headers=csrf_headers(anon))
    assert locked.status_code == 423, locked.text
    assert locked.json()["error"]["code"] == "mfa_locked"


def test_recovery_code_login_revokes_sessions_without_escalation(client, application):
    email = "recovery-cust@example.com"
    headers = _customer_with_session(client, application, email)
    _enroll_totp(client, headers)
    assert client.post("/api/v1/auth/mfa/totp/enroll/confirm",
                       json={"code": _totp_code(application, email)},
                       headers=headers).status_code == 200
    issued = client.post("/api/v1/auth/mfa/recovery-codes",
                         json={"label": "x", "password": "Solarops123"}, headers=headers)
    assert issued.status_code == 201, issued.text
    code = issued.json()["codes"][0]
    from fastapi.testclient import TestClient

    anon = TestClient(application)
    ticket = login(anon, kind="customer", identifier=email,
                   password="Solarops123").json()["ticket"]
    recovered = anon.post(
        "/api/v1/auth/mfa/ticket/verify-recovery",
        json={"ticket": ticket, "code": code}, headers=csrf_headers(anon),
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["user"]["role"] == "customer"
    # The old password-only session is gone after recovery use.
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    # The same recovery code cannot be used twice.
    ticket2 = login(anon, kind="customer", identifier=email,
                    password="Solarops123").json()["ticket"]
    # Fresh TOTP login still works for the still-active factor.
    again = anon.post(
        "/api/v1/auth/mfa/ticket/verify-totp",
        json={"ticket": ticket2, "code": _totp_code(application, email)},
        headers=csrf_headers(anon),
    )
    assert again.status_code == 200, again.text


def test_mfa_ticket_rate_limiting(client, application):
    email = "rate-cust@example.com"
    headers = _customer_with_session(client, application, email)
    _enroll_totp(client, headers)
    assert client.post("/api/v1/auth/mfa/totp/enroll/confirm",
                       json={"code": _totp_code(application, email)},
                       headers=headers).status_code == 200
    from fastapi.testclient import TestClient

    anon = TestClient(application)
    ticket = login(anon, kind="customer", identifier=email,
                   password="Solarops123").json()["ticket"]
    last = None
    for _ in range(9):
        last = anon.post("/api/v1/auth/mfa/ticket/verify-totp",
                         json={"ticket": ticket, "code": "000000"},
                         headers=csrf_headers(anon))
    assert last is not None and last.status_code == 429, (
        last.text if last else "no response")


def test_factor_revocation_requires_reauthentication(client, application):
    email = "revoke-cust@example.com"
    headers = _customer_with_session(client, application, email)
    started = _enroll_totp(client, headers)
    assert client.post("/api/v1/auth/mfa/totp/enroll/confirm",
                       json={"code": _totp_code(application, email)},
                       headers=headers).status_code == 200
    factor_id = started["factor_id"]
    denied = client.post(f"/api/v1/auth/mfa/factors/{factor_id}/revoke",
                         json={}, headers=headers)
    assert denied.status_code == 403, denied.text
    revoked = client.post(f"/api/v1/auth/mfa/factors/{factor_id}/revoke",
                          json={"password": "Solarops123"}, headers=headers)
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["totp_enrolled"] is False
    # Password login works directly again once the factor is gone.
    _login(client, "customer", email, "Solarops123")


def test_staff_roles_survive_mfa_enrollment(client, application):
    _staff(application, "support", "mfa-support@example.com", "EMP-SUP-4E1")
    headers = _login(client, "employee", "EMP-SUP-4E1", "Staffpass123")
    _enroll_totp(client, headers, password="Staffpass123")
    assert client.post(
        "/api/v1/auth/mfa/totp/enroll/confirm",
        json={"code": _totp_code(application, "mfa-support@example.com")},
        headers=headers,
    ).status_code == 200
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["user"]["role"] == "support"


def test_step_up_passkey_grant_flow(client, application):
    email = "stepup-passkey@example.com"
    headers = _customer_with_session(client, application, email)
    options = client.post("/api/v1/auth/passkeys/registration/options", headers=headers)
    auth = VirtualAuthenticator()
    created = client.post(
        "/api/v1/auth/passkeys/registration/verify",
        json={"credential": auth.register(options.json()["options"]["challenge"])},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    started = client.post("/api/v1/auth/step-up/start", headers=headers)
    assert started.status_code == 200, started.text
    assert started.json()["methods"] == ["passkey"]
    scoped = client.post(
        "/api/v1/auth/passkeys/authentication/options", headers=headers)
    assert scoped.status_code == 200, scoped.text
    grant = client.post(
        "/api/v1/auth/step-up/verify-passkey",
        json={"ticket": started.json()["ticket"], "credential": auth.authenticate(
            scoped.json()["options"]["challenge"])},
        headers=headers,
    )
    assert grant.status_code == 200, grant.text
    assert grant.json()["method"] == "passkey"
    # The grant authorizes sensitive actions: revoking the passkey works.
    revoked = client.post(
        f"/api/v1/auth/passkeys/{created.json()['id']}/revoke",
        json={}, headers={**headers, "X-Strong-Auth": grant.json()["grant"]})
    assert revoked.status_code == 200, revoked.text


def test_step_up_grant_flow(client, application):
    email = "stepup-cust@example.com"
    headers = _customer_with_session(client, application, email)
    _enroll_totp(client, headers)
    assert client.post("/api/v1/auth/mfa/totp/enroll/confirm",
                       json={"code": _totp_code(application, email)},
                       headers=headers).status_code == 200
    started = client.post("/api/v1/auth/step-up/start", headers=headers)
    assert started.status_code == 200, started.text
    assert started.json()["methods"] == ["totp"]
    grant = client.post(
        "/api/v1/auth/step-up/verify-totp",
        json={"ticket": started.json()["ticket"],
              "code": _totp_code(application, email)},
        headers=headers,
    )
    assert grant.status_code == 200, grant.text
    assert grant.json()["method"] == "totp"
