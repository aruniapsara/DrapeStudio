"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # GenerationRequest table
    op.create_table(
        "generation_request",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("garment_image_urls", sa.JSON(), nullable=False),
        sa.Column("model_params", sa.JSON(), nullable=False),
        sa.Column("scene_params", sa.JSON(), nullable=False),
        sa.Column("output_count", sa.Integer(), nullable=False, server_default="3"),
        sa.Column(
            "prompt_template_version",
            sa.String(),
            nullable=False,
            server_default="v0.1",
        ),
        sa.Column("idempotency_key", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        op.f("ix_generation_request_session_id"),
        "generation_request",
        ["session_id"],
        unique=False,
    )

    # GenerationOutput table
    op.create_table(
        "generation_output",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("generation_request_id", sa.String(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=False),
        sa.Column("variation_index", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["generation_request_id"],
            ["generation_request.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # UsageCost table
    op.create_table(
        "usage_cost",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("generation_request_id", sa.String(), nullable=False),
        sa.Column(
            "provider",
            sa.String(),
            nullable=False,
            server_default="google_gemini",
        ),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["generation_request_id"],
            ["generation_request.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("usage_cost")
    op.drop_table("generation_output")
    op.drop_index(
        op.f("ix_generation_request_session_id"),
        table_name="generation_request",
    )
    op.drop_table("generation_request")
