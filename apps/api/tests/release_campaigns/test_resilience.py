"""Release resilience catalog: real app/DB rollback and provider failure contracts.

Imported tests execute their original assertions and preserve parametrization.
Repeated executions are not additional distinct tests. Provider adapters are
stubbed only at the external network boundary; no provider acceptance is claimed.
"""

import pytest
from tests.test_finance_syscache_integration import (
    test_duplicate_outbox_event_preserves_callers_transaction as test_duplicate_outbox_event_preserves_callers_transaction,
)
from tests.test_finance_syscache_integration import (
    test_finance_failed_post_rolls_back_source_and_outbox as test_finance_failed_post_rolls_back_source_and_outbox,
)
from tests.test_razorpay_boundary import (
    test_no_credentials_or_live_keys_fail_closed as test_no_credentials_or_live_keys_fail_closed,
)
from tests.test_razorpay_boundary import (
    test_timeout_preserves_unknown_intent_and_never_retries_creation as test_timeout_preserves_unknown_intent_and_never_retries_creation,
)
from tests.test_shared_limits_and_outage import (
    test_database_connection_outage_returns_503_then_recovers as test_database_connection_outage_returns_503_then_recovers,
)
from tests.test_shared_limits_and_outage import (
    test_two_worker_instances_share_limit_and_survive_recreation as test_two_worker_instances_share_limit_and_survive_recreation,
)

pytestmark = pytest.mark.database
