"""Add agent_tariffs table for prefix-based per-second pricing

Revision ID: 002
Revises: 001
Create Date: 2026-02-13
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_tariffs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "agent_id",
            sa.Integer(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("prefix", sa.String(20), nullable=False),
        sa.Column("price_per_second", sa.Float(), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_tariff_agent_prefix",
        "agent_tariffs",
        ["agent_id", "prefix"],
    )


def downgrade() -> None:
    op.drop_index("idx_tariff_agent_prefix", table_name="agent_tariffs")
    op.drop_table("agent_tariffs")
