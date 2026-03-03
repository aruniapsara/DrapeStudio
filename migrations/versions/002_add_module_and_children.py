"""Add module column and child_params table

Revision ID: 002
Revises: 001
Create Date: 2026-03-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'module' column to generation_request
    # nullable=True / server_default='adult' for backward compatibility
    op.add_column(
        "generation_request",
        sa.Column(
            "module",
            sa.String(20),
            nullable=True,
            server_default="adult",
        ),
    )

    # Create child_params table
    op.create_table(
        "child_params",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column(
            "generation_request_id",
            sa.String(26),
            sa.ForeignKey("generation_request.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("age_group", sa.String(10), nullable=False),
        sa.Column("child_gender", sa.String(10), nullable=False),
        sa.Column("pose_style", sa.String(30), nullable=False),
        sa.Column("background_preset", sa.String(30), nullable=False),
        sa.Column("hair_style", sa.String(30), nullable=True),
        sa.Column("expression", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("child_params")
    op.drop_column("generation_request", "module")
