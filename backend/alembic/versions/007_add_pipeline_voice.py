"""Add pipeline_voice column to agents

Revision ID: 007_add_pipeline_voice
Revises: 006_add_pipeline_provider
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "007_add_pipeline_voice"
down_revision = "006_add_pipeline_provider"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("agents", sa.Column("pipeline_voice", sa.String(100), nullable=True))


def downgrade():
    op.drop_column("agents", "pipeline_voice")
