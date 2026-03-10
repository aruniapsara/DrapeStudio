"""Add fiton_request table

Revision ID: 004
Revises: 003
Create Date: 2026-03-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fiton_request",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column(
            "generation_request_id",
            sa.String(26),
            sa.ForeignKey("generation_request.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("customer_photo_url", sa.String(500), nullable=False),
        sa.Column("customer_measurements", sa.JSON, nullable=False),
        # {bust_cm, waist_cm, hips_cm, height_cm, shoulder_width_cm}
        sa.Column("garment_measurements", sa.JSON, nullable=True),
        # {bust_cm, waist_cm, hips_cm, length_cm, shoulder_width_cm}
        sa.Column("garment_size_label", sa.String(10), nullable=True),
        # XS, S, M, L, XL, XXL, 3XL
        sa.Column("fit_preference", sa.String(10), nullable=True),
        # loose | regular | slim
        sa.Column("recommended_size", sa.String(10), nullable=True),
        sa.Column("fit_confidence", sa.Float, nullable=True),
        # 0-100%
        sa.Column("fit_details", sa.JSON, nullable=True),
        # {bust: "good", waist: "tight", hips: "perfect", length: "-2cm short"}
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("fiton_request")
