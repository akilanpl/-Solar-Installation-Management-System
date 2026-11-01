"""Prepare and verify a private, test-mode-only Razorpay configuration.

This is a read-only provider credential check, not checkout/settlement support.
It never creates a provider order, payment, refund, webhook, or database row.
"""

import argparse
import getpass
import re
from pathlib import Path

import httpx
from dotenv import dotenv_values

from local_secrets import protect

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / ".env.razorpay.local"
TEMPLATE = (
    "# Private Razorpay TEST credentials. Never commit this file.\n"
    "# Loaded only by the local provider-check tool; checkout remains unavailable.\n"
    "SOLAROPS_RAZORPAY_KEY_ID=\n"
    "SOLAROPS_RAZORPAY_KEY_SECRET=\n"
)


def validate_credentials(key_id: str, key_secret: str) -> None:
    if not re.fullmatch(r"rzp_test_[A-Za-z0-9]+", key_id):
        raise ValueError("A Razorpay test-mode key ID is required; live keys are refused.")
    if not key_secret or len(key_secret) > 256 or not re.fullmatch(r"[A-Za-z0-9_-]+", key_secret):
        raise ValueError("A valid test-mode key secret is required.")


def verify_credentials(key_id: str, key_secret: str, transport=None) -> bool:
    validate_credentials(key_id, key_secret)
    try:
        with httpx.Client(
            auth=(key_id, key_secret),
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=False,
            transport=transport,
        ) as client:
            # Listing one test order verifies Basic Auth without creating a
            # charge/order or displaying customer/order data in the terminal.
            response = client.get("https://api.razorpay.com/v1/orders", params={"count": 1})
        if response.status_code != 200:
            return False
        payload = response.json()
        return (
            isinstance(payload, dict)
            and payload.get("entity") == "collection"
            and isinstance(payload.get("items"), list)
        )
    except (httpx.HTTPError, ValueError):
        return False


def initialize():
    if not CONFIG.exists():
        CONFIG.touch(mode=0o600)
        protect(CONFIG)
        CONFIG.write_text(TEMPLATE, encoding="utf-8")
    else:
        protect(CONFIG)
    print("Private .env.razorpay.local prepared; existing values preserved.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--init", action="store_true")
    action.add_argument("--configure", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.init:
        initialize()
        return 0
    if args.configure:
        key_id = getpass.getpass("Razorpay test key ID (hidden): ").strip()
        key_secret = getpass.getpass("Razorpay test key secret (hidden): ").strip()
    else:
        config = dotenv_values(CONFIG)
        key_id = config.get("SOLAROPS_RAZORPAY_KEY_ID") or ""
        key_secret = config.get("SOLAROPS_RAZORPAY_KEY_SECRET") or ""
    try:
        verified = verify_credentials(key_id, key_secret)
    except ValueError as exc:
        print(str(exc))
        return 1
    if not verified:
        print(
            "Test-provider authentication not verified. Check credentials/network; no details were logged."
        )
        return 1
    if args.configure:
        initialize()
        CONFIG.write_text(
            "# Private test-mode credentials; do not commit.\n"
            f"SOLAROPS_RAZORPAY_KEY_ID={key_id}\n"
            f"SOLAROPS_RAZORPAY_KEY_SECRET={key_secret}\n",
            encoding="utf-8",
        )
    print("Razorpay test credentials verified with a read-only API call. No payment was created.")
    print("Checkout, webhook settlement and refund integration are still unavailable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
