from sqlalchemy.ext.asyncio import AsyncSession

from events_aggregator.models import Ticket


class TicketRepository:
    """Database operations for tickets."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, ticket_id: str) -> Ticket | None:
        return await self.session.get(Ticket, ticket_id)

    async def add(self, ticket: Ticket) -> None:
        self.session.add(ticket)

    async def save(self) -> None:
        await self.session.commit()
