from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from events_aggregator.models import Event


class EventRepository:
    """Database operations for events."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, event_id: str) -> Event | None:
        return await self.session.get(Event, event_id)

    async def count(self, *, date_from: date | None = None) -> int:
        query = select(func.count()).select_from(Event)

        if date_from is not None:
            query = query.where(Event.event_time >= date_from)

        return await self.session.scalar(query) or 0

    async def list_page(
        self,
        *,
        date_from: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Event]:
        query = select(Event)

        if date_from is not None:
            query = query.where(Event.event_time >= date_from)

        result = await self.session.scalars(
            query.order_by(Event.event_time, Event.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.all())

    async def upsert(
        self,
        event_id: str,
        event_data: dict[str, object],
    ) -> Event:
        event = await self.get_by_id(event_id)

        if event is None:
            event = Event(id=event_id, **event_data)
            await self.add(event)
        else:
            for field, value in event_data.items():
                setattr(event, field, value)

        return event

    async def add(self, event: Event) -> None:
        self.session.add(event)

    async def save(self) -> None:
        await self.session.commit()
