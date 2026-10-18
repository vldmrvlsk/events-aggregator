
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import date
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from events_aggregator.database import AsyncSessionLocal, get_db
from events_aggregator.models import Event, Ticket
from events_aggregator.paginator import EventsPaginator
from events_aggregator.provider import EventsProviderClient
from events_aggregator.schemas import TicketCreate
from events_aggregator.sync import sync_events

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SECONDS = 24 * 60 * 60


async def daily_sync_worker() -> None:
    """Run event synchronization once every 24 hours."""
    while True:
        try:
            async with AsyncSessionLocal() as session:
                result = await sync_events(session)

            logger.info("Daily event sync completed: %s", result)

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Daily event sync failed")

        await asyncio.sleep(SYNC_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the background synchronization task."""
    sync_task = asyncio.create_task(daily_sync_worker())

    try:
        yield
    finally:
        sync_task.cancel()

        try:
            await sync_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Events Aggregator",
    lifespan=lifespan,
)

provider_client = EventsProviderClient()

SEATS_CACHE_TTL = 30
seats_cache: dict[str, tuple[float, list[str]]] = {}


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/sync/trigger", status_code=status.HTTP_200_OK)
async def trigger_sync(
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await sync_events(session)


@app.get("/api/events")
async def list_events(
    date_from: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    paginator = EventsPaginator(session)
    page_result = await paginator.paginate(
        date_from=date_from,
        page=page,
        page_size=page_size,
    )

    next_page = page_result["next_page"]
    previous_page = page_result["previous_page"]

    next_url = (
        _build_page_url(next_page, page_size, date_from)
        if next_page is not None
        else None
    )
    previous_url = (
        _build_page_url(previous_page, page_size, date_from)
        if previous_page is not None
        else None
    )

    return {
        "count": page_result["count"],
        "next": next_url,
        "previous": previous_url,
        "results": [
            _serialize_event(event)
            for event in page_result["results"]
        ],
    }


@app.get("/api/events/{event_id}")
async def get_event(
    event_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    event = await session.get(Event, event_id)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    return _serialize_event(event)


@app.get("/api/events/{event_id}/seats")
async def get_event_seats(
    event_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    event = await session.get(Event, event_id)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    cached = seats_cache.get(event_id)
    now = time.monotonic()

    if cached is not None:
        cached_at, cached_seats = cached
        if now - cached_at < SEATS_CACHE_TTL:
            return {
                "event_id": event.id,
                "available_seats": cached_seats,
            }

    try:
        available_seats = await provider_client.seats(event_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve available seats from provider",
        ) from exc

    seats_cache[event_id] = (time.monotonic(), available_seats)

    return {
        "event_id": event.id,
        "available_seats": available_seats,
    }


@app.post("/api/tickets", status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_data: TicketCreate,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    event = await session.get(Event, ticket_data.event_id)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    try:
        ticket_id = await provider_client.register(
            event_id=ticket_data.event_id,
            first_name=ticket_data.first_name,
            last_name=ticket_data.last_name,
            email=str(ticket_data.email),
            seat=ticket_data.seat,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ticket registration failed at provider",
        ) from exc

    ticket = Ticket(
        ticket_id=ticket_id,
        event_id=ticket_data.event_id,
        first_name=ticket_data.first_name,
        last_name=ticket_data.last_name,
        email=str(ticket_data.email),
        seat=ticket_data.seat,
        status="active",
    )
    session.add(ticket)
    await session.commit()

    seats_cache.pop(ticket_data.event_id, None)

    return {"ticket_id": ticket_id}


@app.delete("/api/tickets/{ticket_id}")
async def cancel_ticket(
    ticket_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    ticket = await session.get(Ticket, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    if ticket.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ticket is already cancelled",
        )

    try:
        success = await provider_client.unregister(
            event_id=ticket.event_id,
            ticket_id=ticket.ticket_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ticket cancellation failed at provider",
        ) from exc

    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Provider did not confirm ticket cancellation",
        )

    ticket.status = "cancelled"
    await session.commit()

    seats_cache.pop(ticket.event_id, None)

    return {"success": True}


def _build_page_url(
    page: int,
    page_size: int,
    date_from: date | None,
) -> str:
    url = f"/api/events?page={page}&page_size={page_size}"

    if date_from is not None:
        url += f"&date_from={date_from.isoformat()}"

    return url


def _serialize_event(event: Event) -> dict[str, Any]:
    return {
        "id": event.id,
        "name": event.name,
        "place": event.place,
        "event_time": (
            event.event_time.isoformat() if event.event_time else None
        ),
        "registration_deadline": (
            event.registration_deadline.isoformat()
            if event.registration_deadline
            else None
        ),
        "status": event.status,
        "number_of_visitors": event.number_of_visitors,
        "changed_at": (
            event.changed_at.isoformat() if event.changed_at else None
        ),
        "created_at": (
            event.created_at.isoformat() if event.created_at else None
        ),
        "status_changed_at": (
            event.status_changed_at.isoformat()
            if event.status_changed_at
            else None
        ),
    }
