"""Add user and otp_request tables; user_id FK on generation_request.

Revision ID: 005
Revises: 004
Create Date: 2026-03-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── user ────────────────────────────────────────────────────────────────
    op.create_table(
        "user",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("credits_remaining", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone"),
    )
    op.create_index("ix_user_phone", "user", ["phone"])

    # ── otp_request ─────────────────────────────────────────────────────────
    op.create_table(
        "otp_request",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("otp_hash", sa.String(64), nullable=False),   # SHA-256 hex
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_otp_request_phone", "otp_request", ["phone"])

    # ── generation_request: add user_id FK ──────────────────────────────────
    with op.batch_alter_table("generation_request") as batch_op:
        batch_op.add_column(
            sa.Column("user_id", sa.String(26), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_generation_request_user_id",
            "user",
            ["user_id"],
            ["id"],
        )
        batch_op.create_index("ix_generation_request_user_id", ["user_id"])


def downgrade() -> None:
    with op.batch_alter_table("generation_request") as batch_op:
        batch_op.drop_index("ix_generation_request_user_id")
        batch_op.drop_constraint("fk_generation_request_user_id", type_="foreignkey")
        batch_op.drop_column("user_id")

    op.drop_index("ix_otp_request_phone", "otp_request")
    op.drop_table("otp_request")
    op.drop_index("ix_user_phone", "user")
    op.drop_table("user")
