"""create tickets table

Revision ID: 08164239276c
Revises: 7e973bf693a6
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "08164239276c"
down_revision: str | Sequence[str] | None = "7e973bf693a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("ticket_id", sa.String(length=36), primary_key=True),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("seat", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_tickets_event_id",
        "tickets",
        ["event_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tickets_event_id", table_name="tickets")
    op.drop_table("tickets")