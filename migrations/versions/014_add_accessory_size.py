"""Add accessory_size column to accessory_params table.

Revision ID: 014
Revises: 013
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("accessory_params", schema=None) as batch_op:
        batch_op.add_column(sa.Column("accessory_size", sa.String(30), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("accessory_params", schema=None) as batch_op:
        batch_op.drop_column("accessory_size")
