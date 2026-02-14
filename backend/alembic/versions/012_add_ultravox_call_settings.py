"""Add Ultravox call settings: initial_output_medium, join_timeout, time_exceeded_message

Revision ID: 012
Revises: 011
Create Date: 2026-02-14
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("initial_output_medium", sa.String(50), server_default="unspecified", nullable=False))
    op.add_column("agents", sa.Column("join_timeout", sa.Integer(), server_default="30", nullable=False))
    op.add_column("agents", sa.Column("time_exceeded_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("agents", "time_exceeded_message")
    op.drop_column("agents", "join_timeout")
    op.drop_column("agents", "initial_output_medium")
