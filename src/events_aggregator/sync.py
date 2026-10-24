from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from events_aggregator.provider import EventsProviderClient
from events_aggregator.repositories.events import EventRepository
from events_aggregator.repositories.sync_metadata import SyncMetadataRepository
from events_aggregator.services.sync import SyncService


async def sync_events(session: AsyncSession) -> dict[str, Any]:
    """Synchronize provider events using repositories and the sync service."""
    service = SyncService(
        events=EventRepository(session),
        metadata=SyncMetadataRepository(session),
        provider=EventsProviderClient(),
    )
    return await service.sync()
