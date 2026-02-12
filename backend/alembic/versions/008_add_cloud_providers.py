"""Add cloud provider columns to agents

Revision ID: 008_add_cloud_providers
Revises: 007_add_pipeline_voice
Create Date: 2025-07-24

Adds per-agent cloud provider selection columns:
  - stt_provider: STT provider (deepgram, openai)
  - llm_provider: LLM provider (groq, openai, cerebras)
  - tts_provider: TTS provider (cartesia, openai, deepgram)
  - stt_model: STT model override
  - llm_model: LLM model override
  - tts_model: TTS model override
  - tts_voice: TTS voice identifier
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "008"
down_revision = "007_add_pipeline_voice"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("agents", sa.Column("stt_provider", sa.String(20), nullable=True, server_default="deepgram"))
    op.add_column("agents", sa.Column("llm_provider", sa.String(20), nullable=True, server_default="groq"))
    op.add_column("agents", sa.Column("tts_provider", sa.String(20), nullable=True, server_default="cartesia"))
    op.add_column("agents", sa.Column("stt_model", sa.String(100), nullable=True))
    op.add_column("agents", sa.Column("llm_model", sa.String(100), nullable=True))
    op.add_column("agents", sa.Column("tts_model", sa.String(100), nullable=True))
    op.add_column("agents", sa.Column("tts_voice", sa.String(100), nullable=True))


def downgrade():
    op.drop_column("agents", "tts_voice")
    op.drop_column("agents", "tts_model")
    op.drop_column("agents", "llm_model")
    op.drop_column("agents", "stt_model")
    op.drop_column("agents", "tts_provider")
    op.drop_column("agents", "llm_provider")
    op.drop_column("agents", "stt_provider")
