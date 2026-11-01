# Page-by-page UI acceptance

67 source-discovered pages; desktop1280,tablet768,mobile390 each require actual screenshots. 0 screenshots captured, 0 corrected-source browserpasses. All scenarios remain BLOCKED, not skipped/passed. Chromium fails macOS bootstrap; pinned Firefox alternative starts headless then SIGABRT; CUA explicitly reports browserdisabled even after Mac unlock/reset. No security settings were bypassed.

| Route | Permitted roles | Desktop | Tablet | Mobile |
|---|---|---|---|---|
| /admin | admin | BLOCKED | BLOCKED | BLOCKED |
| /admin/pricing | admin | BLOCKED | BLOCKED | BLOCKED |
| /admin/reports | admin | BLOCKED | BLOCKED | BLOCKED |
| /customer/bills/[id] | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/bills | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/complaints/[id] | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/complaints | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/enquiries/[id] | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/enquiries/new | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/equipment | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/estimates/[id] | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/estimates | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/generation | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/installations | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/orders/[id] | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/orders | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/payments | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/payments/razorpay | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/quotations/[id] | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/quotations | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/replacements | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/store | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/subsidies | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/support | customer | BLOCKED | BLOCKED | BLOCKED |
| /customer/warranty-extensions | customer | BLOCKED | BLOCKED | BLOCKED |
| /login | public | BLOCKED | BLOCKED | BLOCKED |
| / | public | BLOCKED | BLOCKED | BLOCKED |
| /sales/enquiries/[id] | sales,admin | BLOCKED | BLOCKED | BLOCKED |
| /sales/installations | sales,admin | BLOCKED | BLOCKED | BLOCKED |
| /sales/orders/[id] | sales,admin | BLOCKED | BLOCKED | BLOCKED |
| /sales/orders | sales,admin | BLOCKED | BLOCKED | BLOCKED |
| /sales | sales,admin | BLOCKED | BLOCKED | BLOCKED |
| /sales/quotations/[id] | sales,admin | BLOCKED | BLOCKED | BLOCKED |
| /sales/quotations | sales,admin | BLOCKED | BLOCKED | BLOCKED |
| /sales/scheduling | sales,admin | BLOCKED | BLOCKED | BLOCKED |
| /sales/subsidies | sales,admin | BLOCKED | BLOCKED | BLOCKED |
| /sales/surveys/[id] | sales,admin | BLOCKED | BLOCKED | BLOCKED |
| /sales/surveys | sales,admin | BLOCKED | BLOCKED | BLOCKED |
| /security | all authenticated | BLOCKED | BLOCKED | BLOCKED |
| /signup | public | BLOCKED | BLOCKED | BLOCKED |
| /support/billing | support,admin | BLOCKED | BLOCKED | BLOCKED |
| /support/estimates/[id] | support,admin | BLOCKED | BLOCKED | BLOCKED |
| /support/estimates | support,admin | BLOCKED | BLOCKED | BLOCKED |
| /support/extensions | support,admin | BLOCKED | BLOCKED | BLOCKED |
| /support/intelligence | support,admin | BLOCKED | BLOCKED | BLOCKED |
| /support/lookup | support,admin | BLOCKED | BLOCKED | BLOCKED |
| /support | support,admin | BLOCKED | BLOCKED | BLOCKED |
| /support/replacements/[id] | support,admin | BLOCKED | BLOCKED | BLOCKED |
| /support/replacements | support,admin | BLOCKED | BLOCKED | BLOCKED |
| /support/tickets/[id] | support,admin | BLOCKED | BLOCKED | BLOCKED |
| /support/warranty | support,admin | BLOCKED | BLOCKED | BLOCKED |
| /support/weather | support,admin | BLOCKED | BLOCKED | BLOCKED |
| /technician/install | technician | BLOCKED | BLOCKED | BLOCKED |
| /technician/labour | technician | BLOCKED | BLOCKED | BLOCKED |
| /technician/offline | technician | BLOCKED | BLOCKED | BLOCKED |
| /technician | technician | BLOCKED | BLOCKED | BLOCKED |
| /technician/repairs/[id] | technician | BLOCKED | BLOCKED | BLOCKED |
| /technician/repairs | technician | BLOCKED | BLOCKED | BLOCKED |
| /technician/surveys/[id] | technician | BLOCKED | BLOCKED | BLOCKED |
| /technician/surveys | technician | BLOCKED | BLOCKED | BLOCKED |
| /verify-email | public | BLOCKED | BLOCKED | BLOCKED |
| /warehouse/approvals | warehouse_staff,warehouse_manager,admin | BLOCKED | BLOCKED | BLOCKED |
| /warehouse | warehouse_staff,warehouse_manager,admin | BLOCKED | BLOCKED | BLOCKED |
| /warehouse/picking | warehouse_staff,warehouse_manager,admin | BLOCKED | BLOCKED | BLOCKED |
| /warehouse/replacements/[id] | warehouse_staff,warehouse_manager,admin | BLOCKED | BLOCKED | BLOCKED |
| /warehouse/replacements | warehouse_staff,warehouse_manager,admin | BLOCKED | BLOCKED | BLOCKED |

Every page still needs navigation/controls/API/persistence/refresh/loading/error/focus/overflow/console/network comparisons. Dynamic record scenarios require actual authorized fixtures; a missingrecord does not pass. Role/API smoke is separately recorded; it is not browseracceptance.
