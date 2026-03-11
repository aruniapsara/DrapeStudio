"""Add source_image table for tracking uploaded images.

Revision ID: 011
Revises: 010
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_image",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("user_id", sa.String(26), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=False, unique=True),
        sa.Column("image_type", sa.String(20), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_source_image_user_id", "source_image", ["user_id"])
    op.create_index("ix_source_image_session_id", "source_image", ["session_id"])
    op.create_index("ix_source_image_created_at", "source_image", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_source_image_created_at")
    op.drop_index("ix_source_image_session_id")
    op.drop_index("ix_source_image_user_id")
    op.drop_table("source_image")
