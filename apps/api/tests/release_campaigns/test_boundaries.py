"""Executable mandatory release campaign; explicit, maintained behavioral catalog.

Pytest collects the original assertion-bearing tests with their parameterization.
No results are synthesized. These executions repeat existing regressions and
must not be represented as newly authored distinct tests in release totals.
Database marking here retains truncation/isolation because module-level marks
on imported source tests do not transfer automatically.
"""

import pytest
from tests.test_calendar_acceptance import (
    test_overlap_rejected_adjacent_allowed_and_retry_returns_same_record as test_overlap_rejected_adjacent_allowed_and_retry_returns_same_record,
)
from tests.test_calendar_acceptance import (
    test_policy_constraints_are_not_overridden_by_reason as test_policy_constraints_are_not_overridden_by_reason,
)
from tests.test_installation_hardening import (
    test_invalid_uploads_reject_content_without_metadata as test_invalid_uploads_reject_content_without_metadata,
)
from tests.test_installation_hardening import (
    test_invalid_work_measurements_rejected as test_invalid_work_measurements_rejected,
)
from tests.test_installation_hardening import (
    test_upload_size_and_customer_authorization as test_upload_size_and_customer_authorization,
)
from tests.test_inventory_atomicity import (
    test_stock_precision_and_finite_bounds_fail_before_database as test_stock_precision_and_finite_bounds_fail_before_database,
)
from tests.test_phase4c_finance import (
    test_money_validation_strict as test_money_validation_strict,
)
from tests.test_pricing import (
    test_cable_adjustment_is_explicit as test_cable_adjustment_is_explicit,
)
from tests.test_pricing import (
    test_discount_above_ten_percent_is_rejected as test_discount_above_ten_percent_is_rejected,
)
from tests.test_pricing import (
    test_tax_rounds_half_up as test_tax_rounds_half_up,
)

pytestmark = pytest.mark.database
