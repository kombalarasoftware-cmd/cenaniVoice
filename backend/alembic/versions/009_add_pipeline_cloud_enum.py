"""Add pipeline-cloud value to realtimemodel enum

Revision ID: 009
Revises: 008
Create Date: 2026-02-12

Adds PIPELINE_CLOUD and pipeline-cloud values to the
realtimemodel PostgreSQL enum type for cloud pipeline support.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'PIPELINE_CLOUD'")
    op.execute("ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'pipeline-cloud'")


def downgrade():
    # PostgreSQL does not support removing values from an enum type.
    # A full enum recreation would be needed, which is not safe in production.
    pass
