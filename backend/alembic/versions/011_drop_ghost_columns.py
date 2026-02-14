"""Drop unused pipeline/cloud provider ghost columns from agents

Revision ID: 011
Revises: 010
Create Date: 2026-02-14

These 8 columns were added by migrations 007 and 008 for a pipeline
feature that was later abandoned. They exist in the database but are
not mapped in the SQLAlchemy ORM model, causing a model/DB mismatch.
Dropping them keeps the schema clean.
"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None

# Ghost columns to remove (all nullable, no data loss risk)
GHOST_COLUMNS = [
    "pipeline_voice",   # Added by 007
    "stt_provider",     # Added by 008
    "llm_provider",     # Added by 008
    "tts_provider",     # Added by 008
    "stt_model",        # Added by 008
    "llm_model",        # Added by 008
    "tts_model",        # Added by 008
    "tts_voice",        # Added by 008
]


def upgrade() -> None:
    for col in GHOST_COLUMNS:
        op.drop_column("agents", col)


def downgrade() -> None:
    # Re-add columns with original definitions if rollback needed
    op.add_column("agents", sa.Column("pipeline_voice", sa.String(100), nullable=True))
    op.add_column("agents", sa.Column("stt_provider", sa.String(20), nullable=True, server_default="deepgram"))
    op.add_column("agents", sa.Column("llm_provider", sa.String(20), nullable=True, server_default="groq"))
    op.add_column("agents", sa.Column("tts_provider", sa.String(20), nullable=True, server_default="cartesia"))
    op.add_column("agents", sa.Column("stt_model", sa.String(100), nullable=True))
    op.add_column("agents", sa.Column("llm_model", sa.String(100), nullable=True))
    op.add_column("agents", sa.Column("tts_model", sa.String(100), nullable=True))
    op.add_column("agents", sa.Column("tts_voice", sa.String(100), nullable=True))
