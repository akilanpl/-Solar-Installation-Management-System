"""Guarded LOCAL synthetic-account maintenance proposal; default is read-only.

Execute only after integration-owner review. No production API bypass is added.
Staff already provisioned by scripts/seed_release_preview.py keep their roles,
identity, verification and profiles. Only their local password hashes and sessions
are maintained. Customer creation always uses real signup/email verification.
"""

import argparse
import json
import logging
import os
import secrets
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import quote, urlparse

DATABASE = "solarops_release_demo_61902854"
CUSTOMER_EMAIL = "explorer.preview61902854@solarops.example.com"
STAFF = [
    ("admin", "admin@sunpower.example", "EMP-ADMIN-001"),
    ("sales", "sales@sunpower.example", "EMP-SALES-001"),
    ("technician", "tech@sunpower.example", "EMP-TECH-001"),
    ("warehouse_staff", "warehouse@sunpower.example", "EMP-WH-001"),
    ("warehouse_manager", "whmanager@sunpower.example", "EMP-WHM-001"),
    ("support", "support@sunpower.example", "EMP-SUP-001"),
]


class SafeFailure(Exception):
    pass


def require(condition, message):
    if not condition:
        raise SafeFailure(message)


def private_write(path, document):
    require(not path.is_symlink(), "Refusing credential-file symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / (".accounts-" + uuid.uuid4().hex)
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(document, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--env", type=Path, required=True)
    parser.add_argument("--url", default="http://localhost:3061")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply reviewed isolated-development maintenance",
    )
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    require(
        (checkout / "apps/api/scripts/seed_release_preview.py").is_file(),
        "Expected SolarOps checkout missing",
    )
    target = urlparse(args.url)
    require(
        target.scheme == "http"
        and target.hostname in {"127.0.0.1", "localhost"}
        and target.port == 3061
        and target.path in {"", "/"}
        and not target.username
        and not target.password
        and not target.query
        and not target.fragment,
        "HTTP verification must use isolated loopback preview port3061",
    )
    sys.path.insert(0, str(checkout / "apps/api"))
    from dotenv import dotenv_values
    from sqlalchemy import select
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import Session

    values = dotenv_values(args.env.resolve(), interpolate=False)
    require(
        values.get("SOLAROPS_APP_ENV") == "development",
        "Explicit preview environment must be development",
    )
    connection_url = make_url(values.get("SOLAROPS_DATABASE_URL", ""))
    require(
        connection_url.database == DATABASE
        and connection_url.host in {"localhost", "127.0.0.1"},
        "Refusing any database except isolated local solarops_release_demo_61902854",
    )
    for key, value in values.items():
        if value is not None:
            os.environ[key] = value
    from app.core.config import Settings
    from app.core.security import SESSION_COOKIE, hash_password, hash_secret, utcnow
    from app.db.session import build_engine
    from app.models.identity import (
        CustomerProfile,
        EmployeeProfile,
        User,
    )
    from app.models.identity import (
        Session as LoginSession,
    )
    from app.models.phase4e import MfaFactor, WebauthnCredential
    from app.repositories.queries import add_audit
    from app.services.mfa_service import revoke_all_sessions

    settings = Settings()
    require(
        settings.app_env == "development"
        and make_url(settings.database_url) == connection_url,
        "Resolved application settings differ from guarded preview database",
    )
    require(
        settings.development_mailbox_enabled,
        "Customer signup requires existing development mailbox; no OTP bypass",
    )
    credentials = checkout / "var/LOCAL_PREVIEW_ACCOUNTS.txt"
    require(
        not (checkout / "var").is_symlink(), "Refusing symlinked credential directory"
    )
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "var/LOCAL_PREVIEW_ACCOUNTS.txt"],
        cwd=checkout,
        capture_output=True,
        check=False,
    )
    require(ignored.returncode == 0, "Private credential file must be Git-ignored")
    engine = build_engine(settings.database_url)
    staff_ids = {}
    try:
        with Session(engine) as db:
            for role, email, code in STAFF:
                user = db.scalar(select(User).where(User.email == email))
                require(
                    user is not None
                    and user.role_code == role
                    and user.is_active
                    and user.email_verified_at,
                    "Required synthetic staff identity missing/mismatched; run reviewed preview seed first",
                )
                profile = db.get(EmployeeProfile, user.id)
                require(
                    profile is not None and profile.employee_code == code,
                    "Synthetic employee ID/profile mismatch; no identity or role changes permitted",
                )
                for model in (MfaFactor, WebauthnCredential):
                    enabled = db.scalar(
                        select(model.id).where(
                            model.user_id == user.id, model.revoked_at.is_(None)
                        )
                    )
                    require(
                        enabled is None,
                        "Synthetic staff has an MFA/passkey factor; use its owner enrollment/recovery flow before maintenance",
                    )
                staff_ids[role] = user.id
            customer = db.scalar(select(User).where(User.email == CUSTOMER_EMAIL))
            require(
                customer is None
                or (customer.role_code == "customer" and customer.is_active),
                "Reserved synthetic customer identity is invalid; refusing overwrite",
            )
            if customer is not None:
                for model in (MfaFactor, WebauthnCredential):
                    require(
                        db.scalar(
                            select(model.id).where(
                                model.user_id == customer.id, model.revoked_at.is_(None)
                            )
                        )
                        is None,
                        "Synthetic customer has an MFA/passkey factor; use secure recovery rather than clearing it",
                    )
        if not args.apply:
            print(
                "Read-only guard check passed. Six existing synthetic staff identities match. No DB/file credentials changed."
            )
            print(
                "Reviewed --apply will maintain only these staff passwords and create/verify the reserved synthetic customer through HTTP."
            )
            return 0
        import httpx

        rows = [
            {
                "role": role,
                "email": email,
                "identifier": code,
                "account_kind": "employee",
            }
            for role, email, code in STAFF
        ]
        rows.append(
            {
                "role": "customer",
                "email": CUSTOMER_EMAIL,
                "identifier": CUSTOMER_EMAIL,
                "account_kind": "customer",
            }
        )
        existing_document = None
        if credentials.exists():
            require(
                not credentials.is_symlink()
                and credentials.stat().st_mode & 0o077 == 0,
                "Existing private credentials have unsafe permissions",
            )
            existing_document = json.loads(credentials.read_text())
            require(
                existing_document.get("database") == DATABASE,
                "Existing credential file targets another environment",
            )
        existing_rows = (
            {row["role"]: row for row in existing_document.get("accounts", [])}
            if existing_document
            else {}
        )
        for row in rows:
            previous = existing_rows.get(row["role"])
            if previous:
                require(
                    previous["identifier"] == row["identifier"]
                    and previous["email"] == row["email"],
                    "Existing private credentials contain different synthetic identities",
                )
            row["password"] = (
                previous["password"]
                if previous
                else "SolarPreview9-" + secrets.token_urlsafe(30)
            )
            row["verified"] = False
        require(
            len({row["password"] for row in rows}) == 7
            and all(len(row["password"]) >= 25 for row in rows),
            "Unique strong passwords per role are required",
        )
        require(
            customer is None or "customer" in existing_rows,
            "Customer already exists without private credentials; refusing unsafe password reset or verification bypass",
        )
        document = {
            "database": DATABASE,
            "environment": "development",
            "login_url": args.url.rstrip("/") + "/login",
            "accounts": rows,
            "mfa": "No factors changed. Enroll via /security with private recovery codes after login.",
        }
        # Persist credentials privately before the transaction so a crash cannot
        # strand generated passwords. Only statuses, never secrets, reach stdout.
        private_write(credentials, document)
        with Session(engine) as db:
            for row in rows:
                if row["role"] == "customer":
                    continue
                user = db.get(User, staff_ids[row["role"]])
                user.password_hash = hash_password(row["password"])
                revoke_all_sessions(db, user)
                add_audit(
                    db,
                    actor_user_id=user.id,
                    action="development.preview_password_reset",
                    entity_type="user",
                    entity_id=user.id,
                    metadata={
                        "environment": "development",
                        "reason": "isolated preview login handoff",
                    },
                )
            db.commit()
        base = args.url.rstrip("/")
        with httpx.Client(
            base_url=base, timeout=15, follow_redirects=False, trust_env=False
        ) as signup:

            def post(http, path, payload):
                csrf = http.get("/api/v1/auth/csrf")
                require(
                    csrf.status_code == 200,
                    "Could not obtain actual preview CSRF token",
                )
                return http.post(
                    path,
                    json=payload,
                    headers={"X-CSRF-Token": csrf.json()["csrf_token"], "Origin": base},
                )

            customer_row = rows[-1]
            if customer is None:
                created = post(
                    signup,
                    "/api/v1/auth/signup",
                    {
                        "email": CUSTOMER_EMAIL,
                        "password": customer_row["password"],
                        "full_name": "Preview Explorer",
                        "phone": "9845061954",
                    },
                )
                require(
                    created.status_code == 201,
                    "Actual preview customer signup failed; inspect privately without printing payload",
                )
            with Session(engine) as db:
                current = db.scalar(select(User).where(User.email == CUSTOMER_EMAIL))
                require(
                    current is not None
                    and current.role_code == "customer"
                    and db.get(CustomerProfile, current.id),
                    "HTTP signup did not create expected customer in the guarded preview database",
                )
                verified_email = bool(current.email_verified_at)
            if not verified_email:
                mailbox = signup.get(
                    "/api/v1/dev/mailbox/" + quote(CUSTOMER_EMAIL, safe="")
                )
                require(
                    mailbox.status_code == 200
                    and mailbox.json()["recipient"] == CUSTOMER_EMAIL,
                    "Actual development mailbox verification message unavailable",
                )
                verified = post(
                    signup,
                    "/api/v1/auth/verify-email",
                    {"email": CUSTOMER_EMAIL, "code": mailbox.json()["code"]},
                )
                require(
                    verified.status_code == 200,
                    "Actual preview email verification failed",
                )
        results = []
        for row in rows:
            with httpx.Client(
                base_url=base, timeout=15, follow_redirects=False, trust_env=False
            ) as http:
                login = post(
                    http,
                    "/api/v1/auth/login",
                    {
                        "account_kind": row["account_kind"],
                        "identifier": row["identifier"],
                        "password": row["password"],
                    },
                )
                require(
                    login.status_code == 200,
                    "Role login did not establish a real session; MFA/recovery is never bypassed",
                )
                who = http.get("/api/v1/auth/me")
                require(
                    who.status_code == 200
                    and who.json()["user"]["role"] == row["role"],
                    "Authenticated preview role mismatch",
                )
                user_id = uuid.UUID(who.json()["user"]["id"])
                token = http.cookies.get(SESSION_COOKIE)
                require(bool(token), "Actual login did not provide its session cookie")
                with Session(engine) as db:
                    saved = db.scalar(
                        select(LoginSession).where(
                            LoginSession.token_hash
                            == hash_secret(token, settings.secret_key)
                        )
                    )
                    require(
                        saved is not None
                        and saved.user_id == user_id
                        and saved.revoked_at is None
                        and saved.expires_at > utcnow(),
                        "HTTP session does not belong to guarded preview database",
                    )
                    require(
                        db.get(User, user_id).email == row["email"],
                        "HTTP identity differs from designated synthetic account",
                    )
                row["verified"] = True
                row["verified_at"] = utcnow().isoformat()
                results.append(
                    {
                        key: row[key]
                        for key in ("role", "identifier", "verified", "verified_at")
                    }
                )
                private_write(credentials, document)
                if row["role"] == "customer":
                    # A genuine synthetic enquiry exercises the existing API;
                    # no quotation/order/payment/installation is fabricated.
                    csrf = http.get("/api/v1/auth/csrf")
                    require(
                        csrf.status_code == 200, "Customer enquiry CSRF unavailable"
                    )
                    enquiry = http.post(
                        "/api/v1/enquiries",
                        json={
                            "contact_name": "Preview Explorer",
                            "contact_phone": "9845061954",
                            "contact_email": CUSTOMER_EMAIL,
                            "site": {
                                "line1": "54 Synthetic Preview Lane",
                                "city": "Chennai",
                                "state": "Tamil Nadu",
                                "postal_code": "600042",
                            },
                            "preferred_capacity_w": 3000,
                            "grid_preference": "on_grid",
                            "monthly_bill_minor": 450000,
                            "subsidy_interest": True,
                        },
                        headers={
                            "X-CSRF-Token": csrf.json()["csrf_token"],
                            "Origin": base,
                            "Idempotency-Key": "preview-handoff-enquiry-61902854",
                        },
                    )
                    require(
                        enquiry.status_code in {200, 201},
                        "Supported synthetic enquiry creation failed",
                    )
                    read_back = http.get("/api/v1/enquiries/" + enquiry.json()["id"])
                    require(
                        read_back.status_code == 200
                        and read_back.json()["contact_email"] == CUSTOMER_EMAIL,
                        "Synthetic enquiry did not persist through owner-scoped read API",
                    )
                    document["synthetic_enquiry_reference"] = enquiry.json()[
                        "reference"
                    ]
                    private_write(credentials, document)
                logout = post(http, "/api/v1/auth/logout", {})
                require(logout.status_code == 204, "Verification session logout failed")
        proof = {
            "database": DATABASE,
            "environment": "development",
            "login_url": document["login_url"],
            "accounts": results,
            "source_sha": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=checkout, text=True
            ).strip(),
            "credential_path": str(credentials),
            "credential_mode": "0600",
        }
        private_write(checkout / "var/ROLE_LOGIN_VERIFICATION.json", proof)
        print(
            "Seven synthetic role logins verified through actual HTTP/CSRF/session authentication and guarded database correlation."
        )
        print(
            "Private credentials written with mode0600; no password, factor secret or cookie printed."
        )
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.CRITICAL)
    try:
        raise SystemExit(main())
    except SafeFailure as error:
        print("Preview account maintenance blocked: " + str(error), file=sys.stderr)
        raise SystemExit(1) from None
    except Exception as error:
        print(
            "Preview account maintenance blocked by "
            + type(error).__name__
            + "; diagnostic values suppressed.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
