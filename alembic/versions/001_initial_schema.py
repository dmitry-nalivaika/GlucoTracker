"""Initial schema: all 7 tables.

Revision ID: 001
Revises:
Create Date: 2026-04-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("telegram_user_id"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("open", "completed", "analysed", "expired", name="sessionstatus"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_input_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.telegram_user_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_user_id_status", "sessions", ["user_id", "status"])

    op.create_table(
        "food_entries",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("telegram_file_id", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_food_entries_session_id", "food_entries", ["session_id"])
    op.create_index("ix_food_entries_user_id", "food_entries", ["user_id"])

    op.create_table(
        "cgm_entries",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("telegram_file_id", sa.Text(), nullable=False),
        sa.Column("timing_label", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cgm_entries_session_id", "cgm_entries", ["session_id"])
    op.create_index("ix_cgm_entries_user_id", "cgm_entries", ["user_id"])

    op.create_table(
        "activity_entries",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_entries_session_id", "activity_entries", ["session_id"])
    op.create_index("ix_activity_entries_user_id", "activity_entries", ["user_id"])

    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("nutrition_json", sa.Text(), nullable=False),
        sa.Column("glucose_curve_json", sa.Text(), nullable=False),
        sa.Column("correlation_json", sa.Text(), nullable=False),
        sa.Column("recommendations_json", sa.Text(), nullable=False),
        sa.Column("within_target_notes", sa.Text(), nullable=True),
        sa.Column("raw_response", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_ai_analyses_user_id", "ai_analyses", ["user_id"])

    op.create_table(
        "trend_analyses",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("session_count", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_ids_json", sa.Text(), nullable=False),
        sa.Column("patterns_json", sa.Text(), nullable=False),
        sa.Column("recommendations_json", sa.Text(), nullable=False),
        sa.Column("raw_response", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trend_analyses_user_id", "trend_analyses", ["user_id"])

    op.create_table(
        "miro_cards",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("analysis", "trend", name="mirocardsourcetype"),
            nullable=False,
        ),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("miro_board_id", sa.Text(), nullable=False),
        sa.Column("miro_card_id", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "created", "failed", name="mirocardstatus"),
            nullable=False,
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_miro_cards_user_id", "miro_cards", ["user_id"])
    op.create_index("ix_miro_cards_source_id", "miro_cards", ["source_id"])


def downgrade() -> None:
    op.drop_table("miro_cards")
    op.drop_table("trend_analyses")
    op.drop_table("ai_analyses")
    op.drop_table("activity_entries")
    op.drop_table("cgm_entries")
    op.drop_table("food_entries")
    op.drop_table("sessions")
    op.drop_table("users")
