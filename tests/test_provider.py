from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from events_aggregator.provider import EventsProviderClient


@pytest.mark.asyncio
async def test_seats_returns_available_seats():
    response = MagicMock()
    response.json.return_value = {"seats": ["A1", "A3"]}
    response.raise_for_status = MagicMock()

    client_instance = MagicMock()
    client_instance.get = AsyncMock(return_value=response)

    client_context = MagicMock()
    client_context.__aenter__ = AsyncMock(return_value=client_instance)
    client_context.__aexit__ = AsyncMock(return_value=False)

    provider = EventsProviderClient(
        base_url="http://provider.test",
        api_key="test-api-key",
    )

    with patch(
        "events_aggregator.provider.httpx.AsyncClient",
        return_value=client_context,
    ) as mock_client:
        seats = await provider.seats("event-123")

    assert seats == ["A1", "A3"]
    mock_client.assert_called_once_with(timeout=10.0)
    client_instance.get.assert_awaited_once_with(
        "http://provider.test/api/events/event-123/seats/",
        headers={"x-api-key": "test-api-key"},
    )


@pytest.mark.asyncio
async def test_seats_rejects_invalid_response():
    response = MagicMock()
    response.json.return_value = {"seats": "A1"}
    response.raise_for_status = MagicMock()

    client_instance = MagicMock()
    client_instance.get = AsyncMock(return_value=response)

    client_context = MagicMock()
    client_context.__aenter__ = AsyncMock(return_value=client_instance)
    client_context.__aexit__ = AsyncMock(return_value=False)

    provider = EventsProviderClient(
        base_url="http://provider.test",
        api_key="test-api-key",
    )

    with patch(
        "events_aggregator.provider.httpx.AsyncClient",
        return_value=client_context,
    ), pytest.raises(ValueError, match="invalid seats response"):
        await provider.seats("event-123")


@pytest.mark.asyncio
async def test_register_returns_ticket_id():
    response = MagicMock()
    response.json.return_value = {"ticket_id": "ticket-123"}
    response.raise_for_status = MagicMock()

    client_instance = MagicMock()
    client_instance.post = AsyncMock(return_value=response)

    client_context = MagicMock()
    client_context.__aenter__ = AsyncMock(return_value=client_instance)
    client_context.__aexit__ = AsyncMock(return_value=False)

    provider = EventsProviderClient(
        base_url="http://provider.test",
        api_key="test-api-key",
    )

    with patch(
        "events_aggregator.provider.httpx.AsyncClient",
        return_value=client_context,
    ):
        ticket_id = await provider.register(
            event_id="event-123",
            first_name="Ivan",
            last_name="Petrov",
            email="ivan@example.com",
            seat="A1",
        )

    assert ticket_id == "ticket-123"
    client_instance.post.assert_awaited_once_with(
        "http://provider.test/api/events/event-123/register/",
        headers={"x-api-key": "test-api-key"},
        json={
            "first_name": "Ivan",
            "last_name": "Petrov",
            "email": "ivan@example.com",
            "seat": "A1",
        },
    )


@pytest.mark.asyncio
async def test_unregister_returns_success():
    response = MagicMock()
    response.json.return_value = {"success": True}
    response.raise_for_status = MagicMock()

    client_instance = MagicMock()
    client_instance.request = AsyncMock(return_value=response)

    client_context = MagicMock()
    client_context.__aenter__ = AsyncMock(return_value=client_instance)
    client_context.__aexit__ = AsyncMock(return_value=False)

    provider = EventsProviderClient(
        base_url="http://provider.test",
        api_key="test-api-key",
    )

    with patch(
        "events_aggregator.provider.httpx.AsyncClient",
        return_value=client_context,
    ):
        result = await provider.unregister(
            event_id="event-123",
            ticket_id="ticket-123",
        )

    assert result is True
    client_instance.request.assert_awaited_once_with(
        "DELETE",
        "http://provider.test/api/events/event-123/unregister/",
        headers={"x-api-key": "test-api-key"},
        json={"ticket_id": "ticket-123"},
    )



@pytest.mark.asyncio
async def test_events_returns_results_and_next_cursor():
    response = MagicMock()
    response.json.return_value = {
        "results": [{"id": "event-123"}],
        "next": "http://provider.test/api/events/?page=2",
    }
    response.raise_for_status = MagicMock()

    client_instance = MagicMock()
    client_instance.get = AsyncMock(return_value=response)

    client_context = MagicMock()
    client_context.__aenter__ = AsyncMock(return_value=client_instance)
    client_context.__aexit__ = AsyncMock(return_value=False)

    provider = EventsProviderClient(
        base_url="http://provider.test",
        api_key="test-api-key",
    )

    with patch(
        "events_aggregator.provider.httpx.AsyncClient",
        return_value=client_context,
    ):
        payload = await provider.events(changed_at="2000-01-01")

    assert payload["results"] == [{"id": "event-123"}]
    assert payload["next"] == "http://provider.test/api/events/?page=2"

    client_instance.get.assert_awaited_once_with(
        "http://provider.test/api/events/",
        headers={"x-api-key": "test-api-key"},
        params={"changed_at": "2000-01-01"},
    )


@pytest.mark.asyncio
async def test_events_uses_cursor_without_changed_at():
    response = MagicMock()
    response.json.return_value = {
        "results": [{"id": "event-456"}],
        "next": None,
    }
    response.raise_for_status = MagicMock()

    client_instance = MagicMock()
    client_instance.get = AsyncMock(return_value=response)

    client_context = MagicMock()
    client_context.__aenter__ = AsyncMock(return_value=client_instance)
    client_context.__aexit__ = AsyncMock(return_value=False)

    provider = EventsProviderClient(
        base_url="http://provider.test",
        api_key="test-api-key",
    )

    cursor = "http://provider.test/api/events/?page=2"

    with patch(
        "events_aggregator.provider.httpx.AsyncClient",
        return_value=client_context,
    ):
        payload = await provider.events(cursor=cursor)

    assert payload["results"] == [{"id": "event-456"}]

    client_instance.get.assert_awaited_once_with(
        cursor,
        headers={"x-api-key": "test-api-key"},
        params=None,
    )


@pytest.mark.asyncio
async def test_events_rejects_invalid_response():
    response = MagicMock()
    response.json.return_value = {"results": "invalid"}
    response.raise_for_status = MagicMock()

    client_instance = MagicMock()
    client_instance.get = AsyncMock(return_value=response)

    client_context = MagicMock()
    client_context.__aenter__ = AsyncMock(return_value=client_instance)
    client_context.__aexit__ = AsyncMock(return_value=False)

    provider = EventsProviderClient(
        base_url="http://provider.test",
        api_key="test-api-key",
    )

    with patch(
        "events_aggregator.provider.httpx.AsyncClient",
        return_value=client_context,
    ), pytest.raises(TypeError, match="invalid events list"):
        await provider.events()

