"""Add activity_json column to ai_analyses.

Revision ID: 002
Revises: 001
Create Date: 2026-04-23
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ai_analyses", sa.Column("activity_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_analyses", "activity_json")
