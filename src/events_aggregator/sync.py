
from datetime import date, datetime
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from events_aggregator.config import (
    EVENTS_PROVIDER_API_KEY,
    EVENTS_PROVIDER_URL,
)
from events_aggregator.models import Event, SyncMetadata


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

    url = f"{EVENTS_PROVIDER_URL.rstrip('/')}/api/events/"
    headers = {"x-api-key": EVENTS_PROVIDER_API_KEY}
    params = {"changed_at": changed_since}
    processed = 0
    max_changed_at = metadata.last_changed_at

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            while url:
                response = await client.get(
                    url,
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                payload = response.json()

                for item in payload.get("results", []):
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
                        "number_of_visitors": item.get("number_of_visitors", 0),
                        "changed_at": _parse_datetime(item.get("changed_at")),
                        "created_at": _parse_datetime(item.get("created_at")),
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

                url = payload.get("next")
                params = None

        metadata.last_sync_time = datetime.now().astimezone()
        metadata.last_changed_at = max_changed_at
        metadata.sync_status = "success"
        await session.commit()

        return {
            "status": "success",
            "processed": processed,
            "last_changed_at": (
                max_changed_at.isoformat() if max_changed_at else None
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
