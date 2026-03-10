"""Add push_subscription table and notification prefs to user.

Revision ID: 008
Revises: 007
Create Date: 2026-03-06
"""

import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_subscription",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("user_id", sa.String(26), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint", sa.String(500), nullable=False, unique=True),
        sa.Column("keys_p256dh", sa.String(200), nullable=False),
        sa.Column("keys_auth", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_push_subscription_user_id", "push_subscription", ["user_id"])

    op.add_column(
        "user",
        sa.Column("sms_notifications_enabled", sa.Boolean, nullable=False, server_default="0"),
    )
    op.add_column(
        "user",
        sa.Column("push_notifications_enabled", sa.Boolean, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("user", "push_notifications_enabled")
    op.drop_column("user", "sms_notifications_enabled")
    op.drop_index("ix_push_subscription_user_id", table_name="push_subscription")
    op.drop_table("push_subscription")
