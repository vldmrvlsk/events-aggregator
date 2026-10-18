
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from events_aggregator.models import Event, SyncMetadata
from events_aggregator.sync import sync_events


@pytest.mark.asyncio
async def test_sync_events_fetches_from_initial_date():
    session = MagicMock()
    session.get = AsyncMock(return_value=None)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    payload = {
        "results": [],
        "next": None,
    }

    provider = MagicMock()
    provider.events = AsyncMock(return_value=payload)

    with patch(
        "events_aggregator.sync.EventsProviderClient",
        return_value=provider,
    ):
        result = await sync_events(session)

    provider.events.assert_awaited_once_with(
        changed_at="2000-01-01",
        cursor=None,
    )
    assert result["status"] == "success"
    assert result["processed"] == 0
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_events_processes_multiple_pages():
    session = MagicMock()
    session.get = AsyncMock(return_value=None)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    first_page = {
        "results": [
            {
                "id": "event-1",
                "name": "First event",
                "status": "published",
                "changed_at": "2026-10-17T10:00:00Z",
            }
        ],
        "next": "https://provider.test/api/events/?page=2",
    }
    second_page = {
        "results": [
            {
                "id": "event-2",
                "name": "Second event",
                "status": "published",
                "changed_at": "2026-10-18T10:00:00Z",
            }
        ],
        "next": None,
    }

    provider = MagicMock()
    provider.events = AsyncMock(
        side_effect=[first_page, second_page]
    )

    with patch(
        "events_aggregator.sync.EventsProviderClient",
        return_value=provider,
    ):
        result = await sync_events(session)

    assert result["status"] == "success"
    assert result["processed"] == 2
    assert provider.events.await_count == 2

    provider.events.assert_any_await(
        changed_at="2000-01-01",
        cursor=None,
    )
    provider.events.assert_any_await(
        changed_at=None,
        cursor="https://provider.test/api/events/?page=2",
    )

    added_events = [
        call.args[0]
        for call in session.add.call_args_list
        if isinstance(call.args[0], Event)
    ]
    assert [event.id for event in added_events] == [
        "event-1",
        "event-2",
    ]

    assert result["last_changed_at"] == datetime(
        2026, 10, 18, 10, 0, tzinfo=UTC
    ).isoformat()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_events_updates_existing_event():
    existing_event = Event(
        id="event-1",
        name="Old name",
        status="published",
        number_of_visitors=1,
    )

    metadata = SyncMetadata(
        id=1,
        last_changed_at=datetime(2026, 10, 17, tzinfo=UTC),
        sync_status="success",
    )

    session = MagicMock()
    session.get = AsyncMock(
        side_effect=lambda model, item_id: (
            metadata if model is SyncMetadata else existing_event
        )
    )
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    provider = MagicMock()
    provider.events = AsyncMock(
        return_value={
            "results": [
                {
                    "id": "event-1",
                    "name": "Updated name",
                    "status": "published",
                    "number_of_visitors": 5,
                    "changed_at": "2026-10-18T10:00:00Z",
                }
            ],
            "next": None,
        }
    )

    with patch(
        "events_aggregator.sync.EventsProviderClient",
        return_value=provider,
    ):
        result = await sync_events(session)

    assert result["processed"] == 1
    assert existing_event.name == "Updated name"
    assert existing_event.number_of_visitors == 5
    session.add.assert_not_called()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_events_marks_error_when_provider_fails():
    metadata = SyncMetadata(id=1, sync_status="success")

    session = MagicMock()
    session.get = AsyncMock(return_value=metadata)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    provider = MagicMock()
    provider.events = AsyncMock(
        side_effect=RuntimeError("Provider unavailable")
    )

    with patch(
        "events_aggregator.sync.EventsProviderClient",
        return_value=provider,
    ), pytest.raises(RuntimeError, match="Provider unavailable"):
        await sync_events(session)

    session.rollback.assert_awaited_once()
    assert metadata.sync_status == "error"
    session.commit.assert_awaited_once()

