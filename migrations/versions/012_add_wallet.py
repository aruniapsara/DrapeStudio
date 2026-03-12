"""Add wallet, wallet_topup, and wallet_transaction tables.

Revision ID: 012
Revises: 011
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Wallet table
    op.create_table(
        "wallet",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("user_id", sa.String(26), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("balance_lkr", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_loaded", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_spent", sa.Integer, nullable=False, server_default="0"),
        sa.Column("trial_images_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("trial_fiton_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("trial_expires_at", sa.DateTime, nullable=True),
        sa.Column("is_premium", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("premium_balance_lkr", sa.Integer, nullable=False, server_default="0"),
        sa.Column("premium_expires_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_wallet_user_id", "wallet", ["user_id"], unique=True)

    # Wallet top-up table
    op.create_table(
        "wallet_topup",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("user_id", sa.String(26), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("package_key", sa.String(20), nullable=False),
        sa.Column("amount_paid_lkr", sa.Integer, nullable=False),
        sa.Column("amount_loaded_lkr", sa.Integer, nullable=False),
        sa.Column("payhere_payment_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_wallet_topup_user_id", "wallet_topup", ["user_id"])

    # Wallet transaction ledger
    op.create_table(
        "wallet_transaction",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("user_id", sa.String(26), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("amount_lkr", sa.Integer, nullable=False),
        sa.Column("balance_after", sa.Integer, nullable=False),
        sa.Column("transaction_type", sa.String(30), nullable=False),
        sa.Column("reference_id", sa.String(26), nullable=True),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_wallet_transaction_user_id", "wallet_transaction", ["user_id"])


def downgrade() -> None:
    op.drop_table("wallet_transaction")
    op.drop_table("wallet_topup")
    op.drop_table("wallet")
