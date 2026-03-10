"""Add Google OAuth fields to user table.

Revision ID: 010
Revises: 009
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add Google OAuth columns
    op.add_column("user", sa.Column("google_id", sa.String(255), nullable=True))
    op.add_column("user", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("user", sa.Column("avatar_url", sa.String(500), nullable=True))

    # Create unique indexes
    op.create_index("ix_user_google_id", "user", ["google_id"], unique=True)
    op.create_index("ix_user_email", "user", ["email"], unique=True)

    # Make phone nullable — use batch mode for SQLite compatibility
    # (SQLite doesn't support ALTER COLUMN, batch_alter_table recreates the table)
    with op.batch_alter_table("user") as batch_op:
        batch_op.alter_column("phone", existing_type=sa.String(20), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("user") as batch_op:
        batch_op.alter_column("phone", existing_type=sa.String(20), nullable=False)
    op.drop_index("ix_user_email", table_name="user")
    op.drop_index("ix_user_google_id", table_name="user")
    op.drop_column("user", "avatar_url")
    op.drop_column("user", "email")
    op.drop_column("user", "google_id")
