from collections.abc import AsyncIterator
from typing import Any

from events_aggregator.provider import EventsProviderClient


class EventsPaginator:
    """Asynchronously iterate over pages returned by the events provider."""

    def __init__(
        self,
        provider: EventsProviderClient,
        changed_at: str | None = None,
    ) -> None:
        self.provider = provider
        self.changed_at = changed_at
        self.cursor: str | None = None
        self.first_page = True
        self.finished = False

    def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self.finished:
            raise StopAsyncIteration

        page = await self.provider.events(
            changed_at=self.changed_at if self.first_page else None,
            cursor=self.cursor,
        )

        self.first_page = False
        self.cursor = page.get("next")

        if not self.cursor:
            self.finished = True

        return page
