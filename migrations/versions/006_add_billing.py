"""Add subscription, payment, and credit_transaction tables.

Revision ID: 006
Revises: 005
Create Date: 2026-03-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── subscription ─────────────────────────────────────────────────────────
    op.create_table(
        "subscription",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column(
            "user_id",
            sa.String(26),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan", sa.String(20), nullable=False),   # free | basic | pro
        sa.Column("status", sa.String(20), nullable=False), # active | cancelled | expired | past_due
        sa.Column("credits_total", sa.Integer(), nullable=False),
        sa.Column("credits_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("credits_reset_date", sa.Date(), nullable=True),
        sa.Column("payhere_subscription_id", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscription_user_id", "subscription", ["user_id"])

    # ── payment ──────────────────────────────────────────────────────────────
    op.create_table(
        "payment",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("user_id", sa.String(26), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("subscription_id", sa.String(26), sa.ForeignKey("subscription.id"), nullable=True),
        sa.Column("amount_lkr", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="LKR"),
        sa.Column("status", sa.String(20), nullable=False), # pending | completed | failed | refunded
        sa.Column("payhere_payment_id", sa.String(100), nullable=True),
        sa.Column("payment_method", sa.String(50), nullable=True),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payment_user_id", "payment", ["user_id"])

    # ── credit_transaction ────────────────────────────────────────────────────
    op.create_table(
        "credit_transaction",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("user_id", sa.String(26), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),          # +ve credit, -ve debit
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(30), nullable=False),
        # generation | subscription_credit | daily_free | refund | admin_grant
        sa.Column("reference_id", sa.String(26), nullable=True),    # generation_request.id
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_transaction_user_id", "credit_transaction", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_credit_transaction_user_id", "credit_transaction")
    op.drop_table("credit_transaction")
    op.drop_index("ix_payment_user_id", "payment")
    op.drop_table("payment")
    op.drop_index("ix_subscription_user_id", "subscription")
    op.drop_table("subscription")
