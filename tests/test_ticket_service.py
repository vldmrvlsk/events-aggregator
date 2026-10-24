from unittest.mock import AsyncMock, MagicMock

import pytest

from events_aggregator.models import Event
from events_aggregator.schemas import TicketCreate
from events_aggregator.services.tickets import (
    EventNotFoundError,
    ProviderOperationError,
    TicketService,
)


@pytest.fixture
def dependencies():
    events = MagicMock()
    events.get_by_id = AsyncMock(return_value=Event(
        id="event-1",
        name="Test event",
        status="published",
        number_of_visitors=0,
    ))

    tickets = MagicMock()
    tickets.add = AsyncMock()
    tickets.save = AsyncMock()

    provider = MagicMock()
    provider.register = AsyncMock(return_value="ticket-1")
    provider.unregister = AsyncMock(return_value=True)

    invalidate_cache = MagicMock()

    service = TicketService(
        events=events,
        tickets=tickets,
        provider=provider,
        invalidate_seats_cache=invalidate_cache,
    )
    return service, events, tickets, provider, invalidate_cache


@pytest.mark.asyncio
async def test_create_ticket_success(dependencies):
    service, _, tickets, provider, invalidate_cache = dependencies
    data = TicketCreate(
        event_id="event-1",
        first_name="Ivan",
        last_name="Petrov",
        email="ivan@example.com",
        seat="A1",
    )

    ticket_id = await service.create(data)

    assert ticket_id == "ticket-1"
    provider.register.assert_awaited_once()
    tickets.add.assert_awaited_once()
    tickets.save.assert_awaited_once()
    invalidate_cache.assert_called_once_with("event-1")


@pytest.mark.asyncio
async def test_create_ticket_fails_if_event_missing(dependencies):
    service, events, tickets, provider, invalidate_cache = dependencies
    events.get_by_id.return_value = None
    data = TicketCreate(
        event_id="missing",
        first_name="Ivan",
        last_name="Petrov",
        email="ivan@example.com",
        seat="A1",
    )

    with pytest.raises(EventNotFoundError):
        await service.create(data)

    provider.register.assert_not_awaited()
    tickets.add.assert_not_awaited()
    invalidate_cache.assert_not_called()


@pytest.mark.asyncio
async def test_create_ticket_fails_if_provider_fails(dependencies):
    service, _, tickets, provider, invalidate_cache = dependencies
    provider.register.side_effect = RuntimeError("Provider unavailable")
    data = TicketCreate(
        event_id="event-1",
        first_name="Ivan",
        last_name="Petrov",
        email="ivan@example.com",
        seat="A1",
    )

    with pytest.raises(ProviderOperationError):
        await service.create(data)

    tickets.add.assert_not_awaited()
    invalidate_cache.assert_not_called()

@pytest.mark.asyncio
async def test_cancel_ticket_success(dependencies):
    service, _, tickets, provider, invalidate_cache = dependencies
    ticket = MagicMock()
    ticket.ticket_id = "ticket-1"
    ticket.event_id = "event-1"
    ticket.status = "active"
    tickets.get_by_id = AsyncMock(return_value=ticket)

    await service.cancel("ticket-1")

    provider.unregister.assert_awaited_once_with(
        event_id="event-1",
        ticket_id="ticket-1",
    )
    assert ticket.status == "cancelled"
    tickets.save.assert_awaited_once()
    invalidate_cache.assert_called_once_with("event-1")


@pytest.mark.asyncio
async def test_cancel_ticket_fails_if_ticket_missing(dependencies):
    service, _, tickets, provider, invalidate_cache = dependencies
    from events_aggregator.services.tickets import TicketNotFoundError

    tickets.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(TicketNotFoundError):
        await service.cancel("missing-ticket")

    provider.unregister.assert_not_awaited()
    tickets.save.assert_not_awaited()
    invalidate_cache.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_ticket_fails_if_already_cancelled(dependencies):
    service, _, tickets, provider, invalidate_cache = dependencies
    from events_aggregator.services.tickets import TicketAlreadyCancelledError

    ticket = MagicMock()
    ticket.ticket_id = "ticket-1"
    ticket.event_id = "event-1"
    ticket.status = "cancelled"
    tickets.get_by_id = AsyncMock(return_value=ticket)

    with pytest.raises(TicketAlreadyCancelledError):
        await service.cancel("ticket-1")

    provider.unregister.assert_not_awaited()
    tickets.save.assert_not_awaited()
    invalidate_cache.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_ticket_fails_if_provider_does_not_confirm(
    dependencies,
):
    service, _, tickets, provider, invalidate_cache = dependencies
    provider.unregister.return_value = False

    ticket = MagicMock()
    ticket.ticket_id = "ticket-1"
    ticket.event_id = "event-1"
    ticket.status = "active"
    tickets.get_by_id = AsyncMock(return_value=ticket)

    with pytest.raises(ProviderOperationError):
        await service.cancel("ticket-1")

    assert ticket.status == "active"
    tickets.save.assert_not_awaited()
    invalidate_cache.assert_not_called()