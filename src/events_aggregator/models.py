
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from events_aggregator.statuses import SyncStatus, TicketStatus


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    registration_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    number_of_visitors: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
    )
    changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    status_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    place: Mapped[dict | None] = mapped_column(JSONB)


class SyncMetadata(Base):
    __tablename__ = "sync_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    last_sync_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    sync_status: Mapped[SyncStatus] = mapped_column(
        Enum(
            SyncStatus,
            name="sync_status_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [
                item.value for item in enum_cls
            ],
            length=32,
        ),
        default=SyncStatus.NEVER,
        server_default=text("'never'"),
    )


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_event_id", "event_id"),
    )
    ticket_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    seat: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    status: Mapped[TicketStatus] = mapped_column(
        Enum(
            TicketStatus,
            name="ticket_status_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [
                item.value for item in enum_cls
            ],
            length=20,
        ),
        nullable=False,
        default=TicketStatus.ACTIVE,
        server_default=text("'active'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
