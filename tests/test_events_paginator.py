from unittest.mock import AsyncMock

import pytest

from events_aggregator.events_paginator import EventsPaginator


@pytest.mark.asyncio
async def test_paginator_iterates_over_multiple_pages():
    first_page = {
        "results": [{"id": "event-1"}],
        "next": "https://provider.test/api/events/?page=2",
    }
    second_page = {
        "results": [{"id": "event-2"}],
        "next": None,
    }

    provider = AsyncMock()
    provider.events = AsyncMock(side_effect=[first_page, second_page])

    paginator = EventsPaginator(provider, changed_at="2000-01-01")
    pages = [page async for page in paginator]

    assert pages == [first_page, second_page]
    assert provider.events.await_count == 2
    provider.events.assert_any_await(
        changed_at="2000-01-01",
        cursor=None,
    )
    provider.events.assert_any_await(
        changed_at=None,
        cursor="https://provider.test/api/events/?page=2",
    )


@pytest.mark.asyncio
async def test_paginator_stops_after_empty_final_page():
    final_page = {"results": [], "next": None}

    provider = AsyncMock()
    provider.events = AsyncMock(return_value=final_page)

    paginator = EventsPaginator(provider)
    pages = [page async for page in paginator]

    assert pages == [final_page]
    provider.events.assert_awaited_once_with(
        changed_at=None,
        cursor=None,
    )


@pytest.mark.asyncio
async def test_paginator_does_not_request_more_pages_after_completion():
    provider = AsyncMock()
    provider.events = AsyncMock(
        return_value={"results": [{"id": "event-1"}], "next": None}
    )

    paginator = EventsPaginator(provider)

    first_page = await anext(paginator)
    assert first_page["results"][0]["id"] == "event-1"

    with pytest.raises(StopAsyncIteration):
        await anext(paginator)

    provider.events.assert_awaited_once()
