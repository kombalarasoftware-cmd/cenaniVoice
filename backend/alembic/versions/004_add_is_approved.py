"""Add is_approved to users table

Revision ID: 004_add_is_approved
Revises: 001_initial_schema
Create Date: 2025-07-15
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '004_add_is_approved'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_approved column, default False for new users
    op.add_column('users', sa.Column('is_approved', sa.Boolean(), server_default='false', nullable=False))

    # Mark ALL existing users as approved (they were already using the system)
    op.execute("UPDATE users SET is_approved = true")


def downgrade() -> None:
    op.drop_column('users', 'is_approved')
