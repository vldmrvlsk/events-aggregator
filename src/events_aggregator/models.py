
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
    sync_status: Mapped[str] = mapped_column(
        String(32),
        default="never",
        server_default=text("'never'"),
    )
