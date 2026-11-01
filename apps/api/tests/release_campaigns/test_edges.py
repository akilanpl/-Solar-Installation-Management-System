"""Executable mandatory release campaign; explicit, maintained behavioral catalog.

Pytest collects the original assertion-bearing tests with their parameterization.
No results are synthesized. These executions repeat existing regressions and
must not be represented as newly authored distinct tests in release totals.
Database marking here retains truncation/isolation because module-level marks
on imported source tests do not transfer automatically.
"""

import pytest
from tests.test_enquiries import (
    test_customer_cannot_read_another_customers_enquiry as test_customer_cannot_read_another_customers_enquiry,
)
from tests.test_enquiries import (
    test_duplicate_submission_is_idempotent as test_duplicate_submission_is_idempotent,
)
from tests.test_enquiries import (
    test_malformed_uuid_and_unknown_route_errors as test_malformed_uuid_and_unknown_route_errors,
)
from tests.test_installation_hardening import (
    test_email_rejected_attempt_does_not_commit_pending_business_changes as test_email_rejected_attempt_does_not_commit_pending_business_changes,
)
from tests.test_installation_hardening import (
    test_evidence_cannot_be_reused_on_another_job as test_evidence_cannot_be_reused_on_another_job,
)
from tests.test_inventory_atomicity import (
    test_cancellation_never_reverses_validated_ledger_or_revives_cancelled_draft as test_cancellation_never_reverses_validated_ledger_or_revives_cancelled_draft,
)
from tests.test_inventory_atomicity import (
    test_duplicate_lines_cannot_overdraw_location as test_duplicate_lines_cannot_overdraw_location,
)
from tests.test_missing_records import (
    test_stale_sales_record_links_fail_without_fabricating_entities as test_stale_sales_record_links_fail_without_fabricating_entities,
)
from tests.test_missing_records import (
    test_stale_technician_job_links_cannot_record_arrival_or_completion as test_stale_technician_job_links_cannot_record_arrival_or_completion,
)
from tests.test_missing_records import (
    test_stale_warehouse_transitions_do_not_create_ledger_or_operation as test_stale_warehouse_transitions_do_not_create_ledger_or_operation,
)
from tests.test_phase3_qa_regression import (
    test_delivery_retry_replays_without_second_pick_and_changed_body_conflicts as test_delivery_retry_replays_without_second_pick_and_changed_body_conflicts,
)
from tests.test_phase3_qa_regression import (
    test_stock_mass_assignment_and_bad_uuid_are_rejected as test_stock_mass_assignment_and_bad_uuid_are_rejected,
)
from tests.test_razorpay_boundary import (
    test_ambiguous_order_cannot_be_retried_under_new_idempotency_key as test_ambiguous_order_cannot_be_retried_under_new_idempotency_key,
)
from tests.test_razorpay_boundary import (
    test_signed_malformed_webhooks_never_create_financial_records as test_signed_malformed_webhooks_never_create_financial_records,
)
from tests.test_razorpay_boundary import (
    test_signed_unknown_events_are_audited_without_financial_mutation as test_signed_unknown_events_are_audited_without_financial_mutation,
)

pytestmark = pytest.mark.database
