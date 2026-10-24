
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from events_aggregator.models import Event
from events_aggregator.paginator import DatabasePaginator


@pytest.fixture
def event():
    return Event(
        id="event-001",
        name="Test event",
        event_time=datetime(2026, 12, 1, tzinfo=UTC),
        registration_deadline=datetime(2026, 11, 30, tzinfo=UTC),
        status="published",
        number_of_visitors=0,
        place={"name": "Test venue", "seats_pattern": "A1-3"},
        changed_at=None,
        created_at=None,
        status_changed_at=None,
    )


@pytest.mark.asyncio
async def test_paginate_returns_count_and_results(event):
    session = MagicMock()
    session.scalar = AsyncMock(return_value=3)

    scalars_result = MagicMock()
    scalars_result.all.return_value = [event]
    session.scalars = AsyncMock(return_value=scalars_result)

    paginator = DatabasePaginator(session)

    result = await paginator.paginate(page=1, page_size=2)

    assert result["count"] == 3
    assert result["results"] == [event]
    assert result["next_page"] == 2
    assert result["previous_page"] is None
    session.scalar.assert_awaited_once()
    session.scalars.assert_awaited_once()


@pytest.mark.asyncio
async def test_paginate_applies_date_filter(event):
    session = MagicMock()
    session.scalar = AsyncMock(return_value=1)

    scalars_result = MagicMock()
    scalars_result.all.return_value = [event]
    session.scalars = AsyncMock(return_value=scalars_result)

    paginator = DatabasePaginator(session)

    result = await paginator.paginate(
        date_from=date(2026, 12, 1),
        page=1,
        page_size=20,
    )

    assert result["count"] == 1
    assert result["results"] == [event]

    query = session.scalars.await_args.args[0]
    assert "event_time" in str(query)


@pytest.mark.asyncio
async def test_paginate_calculates_previous_and_next_pages(event):
    session = MagicMock()
    session.scalar = AsyncMock(return_value=5)

    scalars_result = MagicMock()
    scalars_result.all.return_value = [event]
    session.scalars = AsyncMock(return_value=scalars_result)

    paginator = DatabasePaginator(session)

    result = await paginator.paginate(page=2, page_size=2)

    assert result["previous_page"] == 1
    assert result["next_page"] == 3


@pytest.mark.asyncio
async def test_paginate_last_page_has_no_next_page(event):
    session = MagicMock()
    session.scalar = AsyncMock(return_value=5)

    scalars_result = MagicMock()
    scalars_result.all.return_value = [event]
    session.scalars = AsyncMock(return_value=scalars_result)

    paginator = DatabasePaginator(session)

    result = await paginator.paginate(page=3, page_size=2)

    assert result["previous_page"] == 2
    assert result["next_page"] is None


@pytest.mark.asyncio
async def test_paginate_empty_result(event):
    session = MagicMock()
    session.scalar = AsyncMock(return_value=0)

    scalars_result = MagicMock()
    scalars_result.all.return_value = []
    session.scalars = AsyncMock(return_value=scalars_result)

    paginator = DatabasePaginator(session)

    result = await paginator.paginate(page=1, page_size=20)

    assert result["count"] == 0
    assert result["results"] == []
    assert result["next_page"] is None
    assert result["previous_page"] is None
