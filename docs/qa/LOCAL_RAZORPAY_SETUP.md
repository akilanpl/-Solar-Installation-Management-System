# Local Razorpay test configuration

Razorpay is the provider named by the existing payment screen. This setup
uses test-mode credentials only. The tool verifies authentication by listing
one test order and never prints the response, creates an order, or charges
money. This does not yet enable checkout, settlement or refunds in SolarOps.

From the repository root on Windows:

```powershell
.\apps\api\.venv\Scripts\python.exe apps/api/scripts/configure_local_razorpay.py --init
.\apps\api\.venv\Scripts\python.exe apps/api/scripts/configure_local_razorpay.py --configure
.\apps\api\.venv\Scripts\python.exe apps/api/scripts/configure_local_razorpay.py --check
```

Generate test keys in the provider dashboard, then enter them at the hidden
terminal prompts. Never paste credentials into chat or commit them. The tool
stores verified keys in the ignored, account-restricted `.env.razorpay.local`.
Existing application `.env` and database settings are preserved. Blank keys,
live keys, redirects, authentication failures and outages do not count as
verified provider evidence. No automatic retry creates unknown provider state.

Official API contract: [authentication](https://razorpay.com/docs/api/authentication)
and [orders](https://razorpay.com/docs/api/orders/).

Actual sandbox authentication remains blocked until account-owned test keys
are entered locally. Mock transport tests validate the tool, not the provider.
Full checkout/webhook/reconciliation/refund work remains outstanding.
