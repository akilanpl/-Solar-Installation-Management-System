# Page-by-page browser acceptance

Verdict: BLOCKED. Source discovery lists every shipped page. An observed render is not20-point functional acceptance. Prior browser observations were on an intermediate production bundle; latest fixes/new routes still need final-source browser rechecks. Playwright Chromium bootstrap failed with macOS MachPort permission denial. Local browser tools currently still report disabled even after the user enabled the setting and the tool runtime was reset.

113 saved browser observations cover role pages,52 cross-role denial observations,8 missing-record states, and4 transient loading captures. Missing-record detail pages are not passed populated workflows. No unexpected console exceptions were reported by the agent; these observations do not certify all forms/network/retry paths. Mobile390 showed no horizontal overflow. Desktop long navigation and duplicate form IDs were reproduced and fixed, but await final visual recheck.

The executable release suite discovers routes directly from src/app, requires real fixture IDs for every dynamic page, uses independent role logins, reload checks,390/768/1280 viewports, keyboard focus and axe rules. Chromium functional suite and Firefox/WebKit compatibility are configured.718 executable browser cases list successfully; none are credited passed from collection. Run playwright.release.config.ts against an isolated seeded preview; missing fixtures and unavailable browsers fail visibly.

| Page | Source | Observed result |
|---|---|---|
| `/admin` | `apps/web/src/app/admin/page.tsx` | render observed on intermediate build |
| `/admin/pricing` | `apps/web/src/app/admin/pricing/page.tsx` | render observed on intermediate build |
| `/admin/reports` | `apps/web/src/app/admin/reports/page.tsx` | render observed on intermediate build |
| `/customer/bills/[id]` | `apps/web/src/app/customer/bills/[id]/page.tsx` | missing populated fixture |
| `/customer/bills` | `apps/web/src/app/customer/bills/page.tsx` | render observed on intermediate build |
| `/customer/complaints/[id]` | `apps/web/src/app/customer/complaints/[id]/page.tsx` | missing populated fixture |
| `/customer/complaints` | `apps/web/src/app/customer/complaints/page.tsx` | render observed on intermediate build |
| `/customer/enquiries/[id]` | `apps/web/src/app/customer/enquiries/[id]/page.tsx` | render observed on intermediate build |
| `/customer/enquiries/new` | `apps/web/src/app/customer/enquiries/new/page.tsx` | render observed on intermediate build |
| `/customer/equipment` | `apps/web/src/app/customer/equipment/page.tsx` | render observed on intermediate build |
| `/customer/estimates/[id]` | `apps/web/src/app/customer/estimates/[id]/page.tsx` | missing populated fixture |
| `/customer/estimates` | `apps/web/src/app/customer/estimates/page.tsx` | render observed on intermediate build |
| `/customer/generation` | `apps/web/src/app/customer/generation/page.tsx` | render observed on intermediate build |
| `/customer/installations` | `apps/web/src/app/customer/installations/page.tsx` | render observed on intermediate build |
| `/customer/orders/[id]` | `apps/web/src/app/customer/orders/[id]/page.tsx` | not run after route restoration |
| `/customer/orders` | `apps/web/src/app/customer/orders/page.tsx` | render observed on intermediate build |
| `/customer` | `apps/web/src/app/customer/page.tsx` | loading state observed only |
| `/customer/payments` | `apps/web/src/app/customer/payments/page.tsx` | render observed on intermediate build |
| `/customer/payments/razorpay` | `apps/web/src/app/customer/payments/razorpay/page.tsx` | render observed on intermediate build |
| `/customer/quotations/[id]` | `apps/web/src/app/customer/quotations/[id]/page.tsx` | not run after route restoration |
| `/customer/quotations` | `apps/web/src/app/customer/quotations/page.tsx` | render observed on intermediate build |
| `/customer/replacements` | `apps/web/src/app/customer/replacements/page.tsx` | render observed on intermediate build |
| `/customer/subsidies` | `apps/web/src/app/customer/subsidies/page.tsx` | render observed on intermediate build |
| `/customer/support` | `apps/web/src/app/customer/support/page.tsx` | render observed on intermediate build |
| `/customer/warranty-extensions` | `apps/web/src/app/customer/warranty-extensions/page.tsx` | render observed on intermediate build |
| `/login` | `apps/web/src/app/login/page.tsx` | render observed on intermediate build |
| `/` | `apps/web/src/app/page.tsx` | render observed on intermediate build |
| `/sales/enquiries/[id]` | `apps/web/src/app/sales/enquiries/[id]/page.tsx` | render observed on intermediate build |
| `/sales/installations` | `apps/web/src/app/sales/installations/page.tsx` | render observed on intermediate build |
| `/sales/orders/[id]` | `apps/web/src/app/sales/orders/[id]/page.tsx` | not run after route restoration |
| `/sales/orders` | `apps/web/src/app/sales/orders/page.tsx` | not run after route restoration |
| `/sales` | `apps/web/src/app/sales/page.tsx` | render observed on intermediate build |
| `/sales/quotations/[id]` | `apps/web/src/app/sales/quotations/[id]/page.tsx` | not run after route restoration |
| `/sales/quotations` | `apps/web/src/app/sales/quotations/page.tsx` | render observed on intermediate build |
| `/sales/scheduling` | `apps/web/src/app/sales/scheduling/page.tsx` | not run after route restoration |
| `/sales/subsidies` | `apps/web/src/app/sales/subsidies/page.tsx` | render observed on intermediate build |
| `/sales/surveys/[id]` | `apps/web/src/app/sales/surveys/[id]/page.tsx` | not run after route restoration |
| `/sales/surveys` | `apps/web/src/app/sales/surveys/page.tsx` | render observed on intermediate build |
| `/security` | `apps/web/src/app/security/page.tsx` | render observed on intermediate build |
| `/signup` | `apps/web/src/app/signup/page.tsx` | render observed on intermediate build |
| `/support/billing` | `apps/web/src/app/support/billing/page.tsx` | render observed on intermediate build |
| `/support/estimates/[id]` | `apps/web/src/app/support/estimates/[id]/page.tsx` | missing populated fixture |
| `/support/estimates` | `apps/web/src/app/support/estimates/page.tsx` | render observed on intermediate build |
| `/support/extensions` | `apps/web/src/app/support/extensions/page.tsx` | render observed on intermediate build |
| `/support/intelligence` | `apps/web/src/app/support/intelligence/page.tsx` | render observed on intermediate build |
| `/support/lookup` | `apps/web/src/app/support/lookup/page.tsx` | render observed on intermediate build |
| `/support` | `apps/web/src/app/support/page.tsx` | render observed on intermediate build |
| `/support/replacements/[id]` | `apps/web/src/app/support/replacements/[id]/page.tsx` | missing populated fixture |
| `/support/replacements` | `apps/web/src/app/support/replacements/page.tsx` | render observed on intermediate build |
| `/support/tickets/[id]` | `apps/web/src/app/support/tickets/[id]/page.tsx` | missing populated fixture |
| `/support/warranty` | `apps/web/src/app/support/warranty/page.tsx` | render observed on intermediate build |
| `/support/weather` | `apps/web/src/app/support/weather/page.tsx` | render observed on intermediate build |
| `/technician/install` | `apps/web/src/app/technician/install/page.tsx` | render observed on intermediate build |
| `/technician/labour` | `apps/web/src/app/technician/labour/page.tsx` | render observed on intermediate build |
| `/technician/offline` | `apps/web/src/app/technician/offline/page.tsx` | render observed on intermediate build |
| `/technician` | `apps/web/src/app/technician/page.tsx` | render observed on intermediate build |
| `/technician/repairs/[id]` | `apps/web/src/app/technician/repairs/[id]/page.tsx` | missing populated fixture |
| `/technician/repairs` | `apps/web/src/app/technician/repairs/page.tsx` | render observed on intermediate build |
| `/technician/surveys/[id]` | `apps/web/src/app/technician/surveys/[id]/page.tsx` | not run after route restoration |
| `/technician/surveys` | `apps/web/src/app/technician/surveys/page.tsx` | render observed on intermediate build |
| `/verify-email` | `apps/web/src/app/verify-email/page.tsx` | render observed on intermediate build |
| `/warehouse/approvals` | `apps/web/src/app/warehouse/approvals/page.tsx` | render observed on intermediate build |
| `/warehouse` | `apps/web/src/app/warehouse/page.tsx` | render observed on intermediate build |
| `/warehouse/picking` | `apps/web/src/app/warehouse/picking/page.tsx` | render observed on intermediate build |
| `/warehouse/replacements/[id]` | `apps/web/src/app/warehouse/replacements/[id]/page.tsx` | missing populated fixture |
| `/warehouse/replacements` | `apps/web/src/app/warehouse/replacements/page.tsx` | render observed on intermediate build |

Total discovered pages: 66. Every page remains pending full required acceptance on the final exact SHA.
