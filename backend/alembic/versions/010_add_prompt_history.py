"""Add prompt_history table for Prompt Maker feature

Revision ID: 010
Revises: 009
Create Date: 2026-02-13
"""
from alembic import op
import sqlalchemy as sa

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'prompt_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('agent_type', sa.String(50), nullable=True),
        sa.Column('tone', sa.String(50), nullable=True),
        sa.Column('language', sa.String(10), server_default='en'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('generated_prompt', sa.Text(), nullable=False),
        sa.Column('applied_to_agent_id', sa.Integer(), sa.ForeignKey('agents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_prompt_history_owner_id', 'prompt_history', ['owner_id'])
    op.create_index('ix_prompt_history_provider', 'prompt_history', ['provider'])


def downgrade() -> None:
    op.drop_index('ix_prompt_history_provider', table_name='prompt_history')
    op.drop_index('ix_prompt_history_owner_id', table_name='prompt_history')
    op.drop_table('prompt_history')
