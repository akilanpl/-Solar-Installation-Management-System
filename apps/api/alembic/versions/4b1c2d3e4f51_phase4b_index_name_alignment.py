"""Phase 4B index alignment with SQLAlchemy default names.

Revision ID: 4b1c2d3e4f51
Revises: 4b1c2d3e4f50

The 4B migration created shortened index names while the models declare
``index=True`` columns, whose default names are ``ix_<table>_<column>``.
This revision renames those nine indexes so the migrated schema matches
the model metadata exactly.
"""
from alembic import op

revision = "4b1c2d3e4f51"
down_revision = "4b1c2d3e4f50"
branch_labels = None
depends_on = None

RENAMES = (
    ("ix_policy_versions_policy", "ix_warranty_policy_versions_policy_id",
     "warranty_policy_versions", ["policy_id"]),
    ("ix_asset_coverage_customer", "ix_serialized_asset_coverage_customer_user_id",
     "serialized_asset_coverage", ["customer_user_id"]),
    ("ix_coverage_decisions_ticket", "ix_coverage_decisions_ticket_id",
     "coverage_decisions", ["ticket_id"]),
    ("ix_warranty_exceptions_ticket", "ix_warranty_exceptions_ticket_id",
     "warranty_exceptions", ["ticket_id"]),
    ("ix_service_estimates_ticket", "ix_service_estimates_ticket_id",
     "service_estimates", ["ticket_id"]),
    ("ix_estimate_decisions_ticket", "ix_estimate_decisions_ticket_id",
     "estimate_decisions", ["ticket_id"]),
    ("ix_service_invoices_ticket", "ix_service_invoices_ticket_id",
     "service_invoices", ["ticket_id"]),
    ("ix_credit_notes_invoice", "ix_service_credit_notes_invoice_id",
     "service_credit_notes", ["invoice_id"]),
    ("ix_replacements_ticket", "ix_replacement_decisions_ticket_id",
     "replacement_decisions", ["ticket_id"]),
)


def upgrade():
    for short, default, table, columns in RENAMES:
        op.drop_index(short, table_name=table)
        op.create_index(default, table, columns)


def downgrade():
    for short, default, table, columns in reversed(RENAMES):
        op.drop_index(default, table_name=table)
        op.create_index(short, table, columns)
