"""Add language_code column to users table.

Revision ID: 003
Revises: 002
Create Date: 2026-04-24
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("language_code", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "language_code")
