from sqlalchemy.ext.asyncio import AsyncSession

from events_aggregator.models import SyncMetadata


class SyncMetadataRepository:
    """Database operations for synchronization metadata."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self) -> SyncMetadata | None:
        return await self.session.get(SyncMetadata, 1)

    async def add(self, metadata: SyncMetadata) -> None:
        self.session.add(metadata)

    async def save(self) -> None:
        await self.session.commit()

    async def flush(self) -> None:
        await self.session.flush()

    async def rollback(self) -> None:
        await self.session.rollback()
