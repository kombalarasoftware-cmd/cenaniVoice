"""Add role_permissions table

Revision ID: 005_add_role_permissions
Revises: 004_add_is_approved
Create Date: 2025-07-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers
revision = '005_add_role_permissions'
down_revision = '004_add_is_approved'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'role_permissions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('role', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('permissions', JSON, nullable=False, server_default='{}'),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Seed default roles with all permissions enabled
    all_true = '{"dashboard":true,"agents":true,"campaigns":true,"numbers":true,"recordings":true,"call_logs":true,"appointments":true,"leads":true,"surveys":true,"reports":true,"settings":true}'
    op.execute(
        f"INSERT INTO role_permissions (role, permissions, description) VALUES "
        f"('ADMIN', '{all_true}', 'Full access to all pages and features'), "
        f"('OPERATOR', '{all_true}', 'Standard operator access')"
    )


def downgrade() -> None:
    op.drop_table('role_permissions')
