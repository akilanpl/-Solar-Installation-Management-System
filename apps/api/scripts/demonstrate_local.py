"""Read back the isolated multi-role demo through Next.js; never records business events."""
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[3]
STAFF = {
    "sales": ("EMP-SALES-001", "/enquiries"),
    "technician": ("EMP-TECH-001", "/surveys"),
    "warehouse_staff": ("EMP-WH-001", "/stock"),
    "warehouse_manager": ("EMP-WHM-001", "/stock"),
    "support": ("EMP-SUP-001", "/tickets"),
    "admin": ("EMP-ADMIN-001", "/finance/dashboard"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:3063")
    parser.add_argument("--customer-credentials", type=Path, default=ROOT / "var/completion-customer.json")
    args = parser.parse_args()
    target = urlparse(args.url)
    if target.scheme != "http" or target.hostname not in {"127.0.0.1", "localhost"} or target.username or target.password or target.path not in {"", "/"} or target.query or target.fragment:
        parser.error("Use an isolated loopback HTTP candidate")
    if args.customer_credentials.stat().st_mode & 0o077:
        parser.error("Customer credential file must be owner-only")
    customer = json.loads(args.customer_credentials.read_text())
    staff_path = ROOT / "var/dev-seed-password.txt"
    if staff_path.stat().st_mode & 0o077:
        parser.error("Staff credential file must be owner-only")
    password = staff_path.read_text().strip()
    accounts = [("customer", customer["identifier"], customer["password"], "/enquiries")]
    accounts.extend((role, code, password, path) for role, (code, path) in STAFF.items())
    for role, identifier, secret, path in accounts:
        with httpx.Client(base_url=args.url + "/api/v1", timeout=15, headers={"Origin": args.url}) as client:
            def csrf():
                response = client.get("/auth/csrf")
                assert response.status_code == 200, "CSRF token unavailable"
                return {"X-CSRF-Token": response.json()["csrf_token"]}

            login = client.post("/auth/login", json={"account_kind": "customer" if role == "customer" else "employee", "identifier": identifier, "password": secret}, headers=csrf())
            assert login.status_code == 200, f"{role}: sign-in rejected"
            assert client.get("/auth/me").json()["user"]["role"] == role, f"{role}: unexpected role"
            assert client.get(path).status_code == 200, f"{role}: authorized read failed"
            if role == "customer":
                assert client.get("/admin/employees").status_code == 403
                assert client.post("/auth/logout").status_code == 403, "Missing CSRF accepted"
                capability = client.get("/payments/razorpay/capability").json()
                print(f"Payment provider enabled: {capability['enabled']} (test mode only)")
            assert client.post("/auth/logout", headers=csrf()).status_code in {200, 204}, f"{role}: logout failed"
            assert client.get("/auth/me").status_code == 401, "Logout did not revoke session"
            print(f"PASS: {role} authenticated, authorized read, logout revocation")
    print("Read-only demonstration complete. No payment, stock, delivery or installation created.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, httpx.HTTPError, KeyError, ValueError, OSError) as error:
        # Exception classes only: HTTP exceptions can contain sensitive URLs.
        print(f"Demonstration failed: {error}" if isinstance(error, AssertionError) else f"Demonstration failed ({type(error).__name__}); inspect local configuration and server logs.", file=sys.stderr)
        sys.exit(1)
