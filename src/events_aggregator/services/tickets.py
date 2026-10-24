from collections.abc import Callable

from events_aggregator.models import Ticket
from events_aggregator.provider import EventsProviderClient
from events_aggregator.repositories.events import EventRepository
from events_aggregator.repositories.tickets import TicketRepository
from events_aggregator.schemas import TicketCreate
from events_aggregator.statuses import TicketStatus


class TicketServiceError(Exception):
    """Base exception for ticket service errors."""


class EventNotFoundError(TicketServiceError):
    """The requested event does not exist."""


class TicketNotFoundError(TicketServiceError):
    """The requested ticket does not exist."""


class TicketAlreadyCancelledError(TicketServiceError):
    """The ticket has already been cancelled."""


class ProviderOperationError(TicketServiceError):
    """The provider operation failed."""


class TicketService:
    """Business logic for ticket registration and cancellation."""

    def __init__(
        self,
        events: EventRepository,
        tickets: TicketRepository,
        provider: EventsProviderClient,
        invalidate_seats_cache: Callable[[str], None],
    ) -> None:
        self.events = events
        self.tickets = tickets
        self.provider = provider
        self.invalidate_seats_cache = invalidate_seats_cache

    async def create(self, data: TicketCreate) -> str:
        event = await self.events.get_by_id(data.event_id)
        if event is None:
            raise EventNotFoundError("Event not found")

        try:
            ticket_id = await self.provider.register(
                event_id=data.event_id,
                first_name=data.first_name,
                last_name=data.last_name,
                email=str(data.email),
                seat=data.seat,
            )
        except Exception as exc:
            raise ProviderOperationError(
                "Ticket registration failed at provider"
            ) from exc

        ticket = Ticket(
            ticket_id=ticket_id,
            event_id=data.event_id,
            first_name=data.first_name,
            last_name=data.last_name,
            email=str(data.email),
            seat=data.seat,
            status=TicketStatus.ACTIVE,
        )
        await self.tickets.add(ticket)
        await self.tickets.save()
        self.invalidate_seats_cache(data.event_id)

        return ticket_id

    async def cancel(self, ticket_id: str) -> None:
        ticket = await self.tickets.get_by_id(ticket_id)

        if ticket is None:
            raise TicketNotFoundError("Ticket not found")

        if ticket.status != TicketStatus.ACTIVE:
            raise TicketAlreadyCancelledError(
                "Ticket is already cancelled"
            )

        try:
            success = await self.provider.unregister(
                event_id=ticket.event_id,
                ticket_id=ticket.ticket_id,
            )
        except Exception as exc:
            raise ProviderOperationError(
                "Ticket cancellation failed at provider"
            ) from exc

        if not success:
            raise ProviderOperationError(
                "Provider did not confirm ticket cancellation"
            )

        ticket.status = TicketStatus.CANCELLED
        await self.tickets.save()
        self.invalidate_seats_cache(ticket.event_id)
