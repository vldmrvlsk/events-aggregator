
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from events_aggregator.models import Event


class EventsPaginator:
    """Filter, sort, and paginate events stored in the database."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def paginate(
        self,
        *,
        date_from: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        query = select(Event)

        if date_from is not None:
            query = query.where(Event.event_time >= date_from)

        count_query = select(func.count()).select_from(query.subquery())
        count = await self.session.scalar(count_query) or 0

        result = await self.session.scalars(
            query.order_by(Event.event_time, Event.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        events = result.all()

        next_page = (
            page + 1
            if page * page_size < count
            else None
        )
        previous_page = page - 1 if page > 1 else None

        return {
            "count": count,
            "next_page": next_page,
            "previous_page": previous_page,
            "results": events,
        }
