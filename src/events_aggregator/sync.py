
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from events_aggregator.models import Event, SyncMetadata
from events_aggregator.provider import EventsProviderClient


async def sync_events(session: AsyncSession) -> dict[str, Any]:
    """Fetch events from the provider and upsert them into the database."""
    metadata = await session.get(SyncMetadata, 1)

    if metadata is None:
        metadata = SyncMetadata(id=1, sync_status="running")
        session.add(metadata)
        await session.flush()
    else:
        metadata.sync_status = "running"

    changed_since = (
        metadata.last_changed_at.date().isoformat()
        if metadata.last_changed_at is not None
        else date(2000, 1, 1).isoformat()
    )

    processed = 0
    max_changed_at = metadata.last_changed_at

    try:
        provider = EventsProviderClient()
        cursor = None

        while True:
            payload = await provider.events(
                changed_at=changed_since if cursor is None else None,
                cursor=cursor,
            )

            for item in payload["results"]:
                event_id = str(item["id"])
                event = await session.get(Event, event_id)

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
                    "changed_at": _parse_datetime(
                        item.get("changed_at")
                    ),
                    "created_at": _parse_datetime(
                        item.get("created_at")
                    ),
                    "status_changed_at": _parse_datetime(
                        item.get("status_changed_at")
                    ),
                }

                if event is None:
                    event = Event(id=event_id, **event_data)
                    session.add(event)
                else:
                    for field, value in event_data.items():
                        setattr(event, field, value)

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

            cursor = payload.get("next")

            if not cursor:
                break

        metadata.last_sync_time = datetime.now().astimezone()
        metadata.last_changed_at = max_changed_at
        metadata.sync_status = "success"

        await session.commit()

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
        await session.rollback()

        failed_metadata = await session.get(SyncMetadata, 1)

        if failed_metadata is not None:
            failed_metadata.sync_status = "error"
            await session.commit()

        raise


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    return datetime.fromisoformat(value)
