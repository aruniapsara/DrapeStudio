"""Add accessory_params table

Revision ID: 003
Revises: 002
Create Date: 2026-03-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accessory_params",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column(
            "generation_request_id",
            sa.String(26),
            sa.ForeignKey("generation_request.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("accessory_category", sa.String(30), nullable=False),
        sa.Column("display_mode", sa.String(20), nullable=False),
        sa.Column("context_scene", sa.String(30), nullable=True),
        sa.Column("model_skin_tone", sa.String(20), nullable=True),
        sa.Column("background_surface", sa.String(30), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("accessory_params")
