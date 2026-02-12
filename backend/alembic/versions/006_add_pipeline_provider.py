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
    # SQLAlchemy uses enum NAME (not value) when native_enum=True
    # Existing pattern: GPT_REALTIME, GPT_REALTIME_MINI, ULTRAVOX, etc.
    op.execute("ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'PIPELINE_QWEN_7B'")
    op.execute("ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'PIPELINE_LLAMA_8B'")
    op.execute("ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'PIPELINE_MISTRAL_7B'")

    # AIProvider enum type does not exist in PostgreSQL (provider is String(20))
    # No ALTER TYPE needed


def downgrade() -> None:
    # PostgreSQL does not support removing enum values
    # The values will remain but won't cause issues
    pass
