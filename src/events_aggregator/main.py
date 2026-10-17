
from datetime import date

from fastapi import Depends, FastAPI, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from events_aggregator.database import get_db
from events_aggregator.models import Event
from events_aggregator.sync import sync_events

app = FastAPI(title="Events Aggregator")


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/sync/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await sync_events(session)


@app.get("/api/events")
async def list_events(
    date_from: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Event)

    if date_from is not None:
        query = query.where(Event.event_time >= date_from)

    count_query = select(func.count()).select_from(query.subquery())
    count = await session.scalar(count_query)
    count = count or 0

    result = await session.scalars(
        query.order_by(Event.event_time, Event.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    events = result.all()

    next_page = (
        f"/api/events?page={page + 1}&page_size={page_size}"
        if page * page_size < count
        else None
    )
    previous_page = (
        f"/api/events?page={page - 1}&page_size={page_size}"
        if page > 1
        else None
    )

    return {
        "count": count,
        "next": next_page,
        "previous": previous_page,
        "results": [
            {
                "id": event.id,
                "name": event.name,
                "place": event.place,
                "event_time": (
                    event.event_time.isoformat()
                    if event.event_time
                    else None
                ),
                "registration_deadline": (
                    event.registration_deadline.isoformat()
                    if event.registration_deadline
                    else None
                ),
                "status": event.status,
                "number_of_visitors": event.number_of_visitors,
                "changed_at": (
                    event.changed_at.isoformat()
                    if event.changed_at
                    else None
                ),
                "created_at": (
                    event.created_at.isoformat()
                    if event.created_at
                    else None
                ),
                "status_changed_at": (
                    event.status_changed_at.isoformat()
                    if event.status_changed_at
                    else None
                ),
            }
            for event in events
        ],
    }
