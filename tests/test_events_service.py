from unittest.mock import AsyncMock, MagicMock

import pytest

from events_aggregator.services.events import (
    EventNotFoundError,
    EventsService,
    SeatsProviderError,
)


@pytest.fixture
def dependencies():
    events = MagicMock()
    events.get_by_id = AsyncMock(
        return_value=MagicMock(id="event-1")
    )

    paginator = MagicMock()
    paginator.paginate = AsyncMock(
        return_value={"count": 1, "results": []}
    )

    provider = MagicMock()
    provider.seats = AsyncMock(return_value=["A1", "A2"])

    cache = {}
    service = EventsService(
        events=events,
        paginator=paginator,
        provider=provider,
        seats_cache=cache,
    )
    return service, events, paginator, provider, cache


@pytest.mark.asyncio
async def test_get_event_success(dependencies):
    service, events, _, _, _ = dependencies

    event = await service.get_event("event-1")

    assert event.id == "event-1"
    events.get_by_id.assert_awaited_once_with("event-1")


@pytest.mark.asyncio
async def test_get_event_raises_if_missing(dependencies):
    service, events, _, _, _ = dependencies
    events.get_by_id.return_value = None

    with pytest.raises(EventNotFoundError):
        await service.get_event("missing")

@pytest.mark.asyncio
async def test_list_events_delegates_to_paginator(dependencies):
    service, _, paginator, _, _ = dependencies

    result = await service.list_events(
        page=2,
        page_size=10,
    )

    assert result == {"count": 1, "results": []}
    paginator.paginate.assert_awaited_once_with(
        date_from=None,
        page=2,
        page_size=10,
    )


@pytest.mark.asyncio
async def test_get_seats_caches_provider_result(dependencies):
    service, _, _, provider, cache = dependencies

    first = await service.get_seats("event-1")
    second = await service.get_seats("event-1")

    assert first == ["A1", "A2"]
    assert second == first
    provider.seats.assert_awaited_once_with("event-1")
    assert "event-1" in cache


@pytest.mark.asyncio
async def test_get_seats_raises_if_event_missing(dependencies):
    service, events, _, provider, _ = dependencies
    events.get_by_id.return_value = None

    with pytest.raises(EventNotFoundError):
        await service.get_seats("missing")

    provider.seats.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_seats_wraps_provider_error(dependencies):
    service, _, _, provider, cache = dependencies
    provider.seats.side_effect = RuntimeError("Provider unavailable")

    with pytest.raises(SeatsProviderError):
        await service.get_seats("event-1")

    assert "event-1" not in cache


def test_invalidate_seats_cache(dependencies):
    service, _, _, _, cache = dependencies
    cache["event-1"] = (0.0, ["A1"])

    service.invalidate_seats_cache("event-1")

    assert "event-1" not in cache
