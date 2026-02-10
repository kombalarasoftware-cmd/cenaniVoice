"""Initial ViciDial-style dialing schema

Revision ID: 001
Revises: None
Create Date: 2026-02-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- New table: dial_lists ---
    op.create_table(
        "dial_lists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default="active", nullable=True),
        sa.Column("total_numbers", sa.Integer(), server_default="0", nullable=True),
        sa.Column("active_numbers", sa.Integer(), server_default="0", nullable=True),
        sa.Column("completed_numbers", sa.Integer(), server_default="0", nullable=True),
        sa.Column("invalid_numbers", sa.Integer(), server_default="0", nullable=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- New table: dial_list_entries ---
    op.create_table(
        "dial_list_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("list_id", sa.Integer(), sa.ForeignKey("dial_lists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=True),
        sa.Column("status", sa.String(20), server_default="new", nullable=True),
        sa.Column("call_attempts", sa.Integer(), server_default="0", nullable=True),
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_callback_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dnc_flag", sa.Boolean(), server_default="false", nullable=True),
        sa.Column("custom_fields", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dial_list_entries_phone_number", "dial_list_entries", ["phone_number"])
    op.create_index("idx_entry_list_status", "dial_list_entries", ["list_id", "status"])
    op.create_index("idx_entry_phone", "dial_list_entries", ["phone_number"])
    op.create_index("idx_entry_callback", "dial_list_entries", ["next_callback_at"])

    # --- New table: dial_attempts ---
    op.create_table(
        "dial_attempts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entry_id", sa.Integer(), sa.ForeignKey("dial_list_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("call_log_id", sa.Integer(), sa.ForeignKey("call_logs.id"), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("sip_code", sa.Integer(), nullable=True),
        sa.Column("hangup_cause", sa.String(100), nullable=True),
        sa.Column("duration", sa.Integer(), server_default="0", nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_attempt_campaign", "dial_attempts", ["campaign_id", "result"])
    op.create_index("idx_attempt_entry", "dial_attempts", ["entry_id", "attempt_number"])

    # --- New table: dnc_list ---
    op.create_table(
        "dnc_list",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("added_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone_number"),
    )
    op.create_index("ix_dnc_list_phone_number", "dnc_list", ["phone_number"])

    # --- New table: campaign_lists ---
    op.create_table(
        "campaign_lists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("list_id", sa.Integer(), sa.ForeignKey("dial_lists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "list_id", name="uq_campaign_list"),
    )

    # --- New table: dial_hopper ---
    op.create_table(
        "dial_hopper",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_id", sa.Integer(), sa.ForeignKey("dial_list_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=True),
        sa.Column("status", sa.String(20), server_default="waiting", nullable=True),
        sa.Column("inserted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dial_hopper_campaign_id", "dial_hopper", ["campaign_id"])
    op.create_index("idx_hopper_campaign_status", "dial_hopper", ["campaign_id", "status", "priority"])

    # --- New table: campaign_dispositions ---
    op.create_table(
        "campaign_dispositions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("next_action", sa.String(50), nullable=True),
        sa.Column("retry_delay_minutes", sa.Integer(), server_default="60", nullable=True),
        sa.Column("is_final", sa.Boolean(), server_default="false", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Add new columns to existing tables ---

    # CallLog: add dial_attempt_id FK
    op.add_column(
        "call_logs",
        sa.Column("dial_attempt_id", sa.Integer(), sa.ForeignKey("dial_attempts.id"), nullable=True),
    )

    # Campaign: add dialing_mode
    op.add_column(
        "campaigns",
        sa.Column("dialing_mode", sa.String(20), server_default="power", nullable=True),
    )

    # PhoneNumber: add timezone field
    op.add_column(
        "phone_numbers",
        sa.Column("timezone", sa.String(50), nullable=True),
    )

    # PhoneNumber: add lead_id FK
    op.add_column(
        "phone_numbers",
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id"), nullable=True),
    )


def downgrade() -> None:
    # Remove columns from existing tables
    op.drop_column("phone_numbers", "lead_id")
    op.drop_column("phone_numbers", "timezone")
    op.drop_column("campaigns", "dialing_mode")
    op.drop_column("call_logs", "dial_attempt_id")

    # Drop new tables in reverse order (respecting FK dependencies)
    op.drop_table("campaign_dispositions")
    op.drop_table("dial_hopper")
    op.drop_table("campaign_lists")
    op.drop_table("dnc_list")
    op.drop_table("dial_attempts")
    op.drop_table("dial_list_entries")
    op.drop_table("dial_lists")
