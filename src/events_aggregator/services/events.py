import time
from datetime import date
from typing import Any

from events_aggregator.models import Event
from events_aggregator.paginator import DatabasePaginator
from events_aggregator.provider import EventsProviderClient
from events_aggregator.repositories.events import EventRepository


class EventNotFoundError(Exception):
    """Raised when an event does not exist."""


class SeatsProviderError(Exception):
    """Raised when the provider cannot return available seats."""


class EventsService:
    """Business operations for events and available seats."""

    SEATS_CACHE_TTL = 30

    def __init__(
        self,
        events: EventRepository,
        paginator: DatabasePaginator,
        provider: EventsProviderClient,
        seats_cache: dict[str, tuple[float, list[str]]],
    ) -> None:
        self.events = events
        self.paginator = paginator
        self.provider = provider
        self.seats_cache = seats_cache

    async def get_event(self, event_id: str) -> Event:
        event = await self.events.get_by_id(event_id)
        if event is None:
            raise EventNotFoundError("Event not found")
        return event

    async def list_events(
        self,
        *,
        date_from: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return await self.paginator.paginate(
            date_from=date_from,
            page=page,
            page_size=page_size,
        )


    async def get_seats(
        self,
        event_id: str,
        *,
        check_event: bool = True,
    ) -> list[str]:
        if check_event:
            await self.get_event(event_id)

        cached = self.seats_cache.get(event_id)
        now = time.monotonic()

        if cached is not None:
            cached_at, cached_seats = cached
            if now - cached_at < self.SEATS_CACHE_TTL:
                return cached_seats

        try:
            available_seats = await self.provider.seats(event_id)
        except Exception as exc:
            raise SeatsProviderError(
                "Failed to retrieve available seats from provider"
            ) from exc

        self.seats_cache[event_id] = (
            time.monotonic(),
            available_seats,
        )
        return available_seats

    def invalidate_seats_cache(self, event_id: str) -> None:
        self.seats_cache.pop(event_id, None)
