from datetime import date, datetime
from typing import Any

from events_aggregator.events_paginator import EventsPaginator
from events_aggregator.models import SyncMetadata
from events_aggregator.provider import EventsProviderClient
from events_aggregator.repositories.events import EventRepository
from events_aggregator.repositories.sync_metadata import SyncMetadataRepository
from events_aggregator.statuses import SyncStatus


class SyncService:
    """Business logic for synchronizing events from the provider."""

    def __init__(
        self,
        events: EventRepository,
        metadata: SyncMetadataRepository,
        provider: EventsProviderClient,
    ) -> None:
        self.events = events
        self.metadata = metadata
        self.provider = provider

    async def sync(self) -> dict[str, Any]:
        metadata = await self.metadata.get()

        if metadata is None:
            metadata = SyncMetadata(id=1, sync_status=SyncStatus.RUNNING)
            await self.metadata.add(metadata)
            await self.metadata.flush()
        else:
            metadata.sync_status = SyncStatus.RUNNING

        changed_since = (
            metadata.last_changed_at.date().isoformat()
            if metadata.last_changed_at is not None
            else date(2000, 1, 1).isoformat()
        )

        processed = 0
        max_changed_at = metadata.last_changed_at

        try:
            async for payload in EventsPaginator(
                self.provider,
                changed_at=changed_since,
            ):
                for item in payload["results"]:
                    event_id = str(item["id"])
                    event_data = {
                        "name": item["name"],
                        "place": item.get("place"),
                        "event_time": _parse_datetime(item.get("event_time")),
                        "registration_deadline": _parse_datetime(
                            item.get("registration_deadline")
                        ),
                        "status": item["status"],
                        "number_of_visitors": item.get(
                            "number_of_visitors", 0
                        ),
                        "changed_at": _parse_datetime(item.get("changed_at")),
                        "created_at": _parse_datetime(item.get("created_at")),
                        "status_changed_at": _parse_datetime(
                            item.get("status_changed_at")
                        ),
                    }

                    await self.events.upsert(event_id, event_data)

                    event_changed_at = event_data["changed_at"]
                    if (
                        event_changed_at is not None
                        and (
                            max_changed_at is None
                            or event_changed_at > max_changed_at
                        )
                    ):
                        max_changed_at = event_changed_at

                    processed += 1

            metadata.last_sync_time = datetime.now().astimezone()
            metadata.last_changed_at = max_changed_at
            metadata.sync_status = SyncStatus.SUCCESS

            await self.metadata.save()

            return {
                "status": "success",
                "processed": processed,
                "last_changed_at": (
                    max_changed_at.isoformat()
                    if max_changed_at
                    else None
                ),
            }

        except Exception:
            await self.metadata.rollback()

            failed_metadata = await self.metadata.get()
            if failed_metadata is not None:
                failed_metadata.sync_status = SyncStatus.ERROR
                await self.metadata.save()

            raise


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    return datetime.fromisoformat(value)
