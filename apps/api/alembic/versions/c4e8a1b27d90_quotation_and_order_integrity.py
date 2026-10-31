"""One open quotation per enquiry and one order per enquiry.

Revision ID: c4e8a1b27d90
Revises: 9b1336c3b2cc
Create Date: 2026-10-31 13:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4e8a1b27d90"
down_revision: Union[str, Sequence[str], None] = "9b1336c3b2cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_quotations_one_active",
        "quotations",
        ["enquiry_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('issued', 'accepted')"),
    )
    op.create_unique_constraint(
        "uq_sales_orders_enquiry",
        "sales_orders",
        ["enquiry_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_sales_orders_enquiry", "sales_orders", type_="unique")
    op.drop_index("uq_quotations_one_active", table_name="quotations")
