"""Add pipeline provider enum values

Revision ID: 006
Revises: 005
Create Date: 2026-02-11

Adds 'pipeline' to AIProvider enum and pipeline model values to RealtimeModel enum.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'pipeline' to AIProvider enum (agents.provider column is VARCHAR, not enum type)
    # No schema change needed — provider column is String(20), accepts any value

    # Add pipeline model values to RealtimeModel enum
    # The enum is stored as a PostgreSQL ENUM type, so we need to add new values
    op.execute("ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'pipeline-qwen-7b'")
    op.execute("ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'pipeline-llama-8b'")
    op.execute("ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'pipeline-mistral-7b'")

    # Add 'pipeline' to AIProvider enum type
    op.execute("ALTER TYPE aiprovider ADD VALUE IF NOT EXISTS 'pipeline'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values
    # The values will remain but won't cause issues
    pass
