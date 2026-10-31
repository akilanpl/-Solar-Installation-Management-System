"""Executable mandatory release campaign; explicit, maintained behavioral catalog.

Pytest collects the original assertion-bearing tests with their parameterization.
No results are synthesized. These executions repeat existing regressions and
must not be represented as newly authored distinct tests in release totals.
Database marking here retains truncation/isolation because module-level marks
on imported source tests do not transfer automatically.
"""

import pytest
from tests.test_calendar_acceptance import (
    test_concurrent_bookings_serialize_for_same_technician as test_concurrent_bookings_serialize_for_same_technician,
)
from tests.test_installation_hardening import (
    test_simultaneous_otp_consumption_succeeds_once as test_simultaneous_otp_consumption_succeeds_once,
)
from tests.test_location_fulfilment import (
    test_concurrent_location_allocations_cannot_reserve_same_units as test_concurrent_location_allocations_cannot_reserve_same_units,
)
from tests.test_phase2_workflow import (
    test_concurrent_acceptance_and_order_confirmation as test_concurrent_acceptance_and_order_confirmation,
)
from tests.test_phase3_warehouse_installation import (
    test_competing_orders_cannot_pick_the_same_stock as test_competing_orders_cannot_pick_the_same_stock,
)
from tests.test_phase3_warehouse_installation import (
    test_concurrent_picks_serialize_on_component_locks as test_concurrent_picks_serialize_on_component_locks,
)
from tests.test_phase3_warehouse_installation import (
    test_concurrent_validation_has_a_single_winner as test_concurrent_validation_has_a_single_winner,
)
from tests.test_quotation_integrity import (
    test_concurrent_full_payments_cannot_both_verify as test_concurrent_full_payments_cannot_both_verify,
)
from tests.test_quotation_integrity import (
    test_concurrent_quotation_creation_keeps_one as test_concurrent_quotation_creation_keeps_one,
)
from tests.test_shared_limits_and_outage import (
    test_concurrent_workers_accept_only_configured_number as test_concurrent_workers_accept_only_configured_number,
)

pytestmark = pytest.mark.database
