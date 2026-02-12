"""Add xAI provider and grok-2-realtime model

Revision ID: 002_add_xai
Revises: 001
Create Date: 2025-01-20

Adds 'xai' to aiprovider enum and 'grok-2-realtime' to realtimemodel enum.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '002_add_xai'
down_revision = None  # Will be applied manually via SQL
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'xai' to aiprovider enum
    op.execute("ALTER TYPE aiprovider ADD VALUE IF NOT EXISTS 'xai'")
    # Add 'grok-2-realtime' to realtimemodel enum
    op.execute("ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'grok-2-realtime'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums easily.
    # A full migration would require creating a new type, updating columns,
    # and dropping the old type. Skipping for safety.
    pass
