
"""create events and sync metadata tables

Revision ID: 7e973bf693a6
Revises:
Create Date: 2026-10-17 22:30:52.055504
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7e973bf693a6"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "registration_deadline",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "number_of_visitors",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status_changed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "place",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sync_metadata",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("last_sync_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "sync_status",
            sa.String(length=32),
            server_default=sa.text("'never'"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("sync_metadata")
    op.drop_table("events")
