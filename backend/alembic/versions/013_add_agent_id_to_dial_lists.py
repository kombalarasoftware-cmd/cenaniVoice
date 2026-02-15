"""Add agent_id to dial_lists for list-agent association

Revision ID: 013
Revises: 012
Create Date: 2026-02-15
"""
from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dial_lists",
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=True),
    )
    op.create_index("idx_dial_lists_agent_id", "dial_lists", ["agent_id"])


def downgrade() -> None:
    op.drop_index("idx_dial_lists_agent_id", table_name="dial_lists")
    op.drop_column("dial_lists", "agent_id")
