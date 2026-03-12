"""Add admin fields to user table and admin_audit_log table.

Revision ID: 013
Revises: 012
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add admin-related columns to the user table using batch mode for SQLite
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("admin_password_hash", sa.String(128), nullable=True))
        batch_op.add_column(sa.Column("admin_notes", sa.Text, nullable=True))
        batch_op.add_column(sa.Column("is_sponsored", sa.Boolean, nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("sponsored_by", sa.String(200), nullable=True))
        batch_op.add_column(sa.Column("sponsored_until", sa.Date, nullable=True))

    # Admin audit log table
    op.create_table(
        "admin_audit_log",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("admin_user_id", sa.String(26), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("target_user_id", sa.String(26), nullable=True),
        sa.Column("details", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_admin_audit_log_admin_user_id", "admin_audit_log", ["admin_user_id"])
    op.create_index("ix_admin_audit_log_target_user_id", "admin_audit_log", ["target_user_id"])


def downgrade() -> None:
    op.drop_table("admin_audit_log")

    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("sponsored_until")
        batch_op.drop_column("sponsored_by")
        batch_op.drop_column("is_sponsored")
        batch_op.drop_column("admin_notes")
        batch_op.drop_column("admin_password_hash")
