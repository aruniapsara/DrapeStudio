"""Add language_preference to user table.

Revision ID: 007
Revises: 006
Create Date: 2026-03-04
"""

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "language_preference",
            sa.String(5),
            nullable=False,
            server_default="en",
        ),
    )


def downgrade() -> None:
    op.drop_column("user", "language_preference")
