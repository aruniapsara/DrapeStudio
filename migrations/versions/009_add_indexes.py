"""Add performance indexes.

Revision ID: 009
Revises: 008
Create Date: 2026-03-06

"""
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # GenerationRequest indexes — most queries filter by user, status, or date
    op.create_index("idx_generation_user",    "generation_request", ["user_id"])
    op.create_index("idx_generation_created", "generation_request", ["created_at"])
    op.create_index("idx_generation_status",  "generation_request", ["status"])
    op.create_index("idx_generation_session", "generation_request", ["session_id"])

    # User indexes
    op.create_index("idx_user_phone",  "user", ["phone"])

    # Billing-related indexes
    op.create_index("idx_subscription_user", "subscription",        ["user_id"])
    op.create_index("idx_payment_user",       "payment",             ["user_id"])
    op.create_index("idx_credit_user",        "credit_transaction",  ["user_id"])

    # FitOn request index
    op.create_index("idx_fiton_generation", "fiton_request", ["generation_request_id"])

    # GenerationOutput index — fetching outputs for a request is the most common query
    op.create_index("idx_output_request", "generation_output", ["generation_request_id"])

    # PushSubscription index — already has index on user_id from ORM, add endpoint lookup
    op.create_index("idx_push_endpoint", "push_subscription", ["endpoint"])


def downgrade() -> None:
    op.drop_index("idx_push_endpoint",      table_name="push_subscription")
    op.drop_index("idx_output_request",     table_name="generation_output")
    op.drop_index("idx_fiton_generation",   table_name="fiton_request")
    op.drop_index("idx_credit_user",        table_name="credit_transaction")
    op.drop_index("idx_payment_user",       table_name="payment")
    op.drop_index("idx_subscription_user",  table_name="subscription")
    op.drop_index("idx_user_phone",         table_name="user")
    op.drop_index("idx_generation_session", table_name="generation_request")
    op.drop_index("idx_generation_status",  table_name="generation_request")
    op.drop_index("idx_generation_created", table_name="generation_request")
    op.drop_index("idx_generation_user",    table_name="generation_request")
