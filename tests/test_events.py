
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from events_aggregator.main import app, get_db
from events_aggregator.models import Event, Ticket


@pytest.fixture
def event():
    return Event(
        id="test-event-001",
        name="Test event",
        event_time=datetime(2026, 12, 1, tzinfo=UTC),
        registration_deadline=datetime(2026, 11, 30, tzinfo=UTC),
        status="published",
        number_of_visitors=0,
        place={
            "name": "Test venue",
            "seats_pattern": "A1-3,B1-2",
        },
        changed_at=None,
        created_at=None,
        status_changed_at=None,
    )


@pytest.fixture
def client(event):
    session = MagicMock()
    session.get = AsyncMock(
        side_effect=lambda model, item_id: (
            None if item_id == "missing-event" else event
        )
    )
    session.commit = AsyncMock()
    session.add = MagicMock()

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_event_detail_returns_place_and_seats_pattern(client):
    response = client.get("/api/events/test-event-001")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-event-001"
    assert "place" in data
    assert data["place"]["seats_pattern"] == "A1-3,B1-2"


def test_event_seats_returns_expected_fields(client, monkeypatch):
    async def fake_seats(event_id: str) -> list[str]:
        assert event_id == "test-event-001"
        return ["A1", "A3", "B1"]

    monkeypatch.setattr(
        "events_aggregator.main.provider_client.seats",
        fake_seats,
    )

    response = client.get("/api/events/test-event-001/seats")

    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == "test-event-001"
    assert data["available_seats"] == ["A1", "A3", "B1"]


def test_event_detail_returns_404_for_missing_event():
    session = MagicMock()
    session.get = AsyncMock(return_value=None)

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            response = test_client.get("/api/events/missing-event")

        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_event_seats_uses_cache(client, monkeypatch):
    from events_aggregator.main import seats_cache

    seats_cache.clear()
    provider_mock = AsyncMock(return_value=["A1", "B2"])

    monkeypatch.setattr(
        "events_aggregator.main.provider_client.seats",
        provider_mock,
    )

    first_response = client.get("/api/events/test-event-001/seats")
    second_response = client.get("/api/events/test-event-001/seats")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["available_seats"] == ["A1", "B2"]
    assert second_response.json()["available_seats"] == ["A1", "B2"]
    provider_mock.assert_awaited_once_with("test-event-001")

    seats_cache.clear()


def test_create_ticket_success(client, monkeypatch):
    from events_aggregator.main import seats_cache

    async def fake_register(**kwargs):
        assert kwargs["event_id"] == "test-event-001"
        assert kwargs["seat"] == "A1"
        return "ticket-123"

    monkeypatch.setattr(
        "events_aggregator.main.provider_client.register",
        fake_register,
    )

    response = client.post(
        "/api/tickets",
        json={
            "event_id": "test-event-001",
            "first_name": "Ivan",
            "last_name": "Petrov",
            "email": "ivan@example.com",
            "seat": "A1",
        },
    )

    assert response.status_code == 201
    assert response.json() == {"ticket_id": "ticket-123"}
    seats_cache.pop("test-event-001", None)


def test_create_ticket_returns_404_for_missing_event(client, monkeypatch):
    from events_aggregator.main import provider_client

    register_mock = AsyncMock()
    monkeypatch.setattr(provider_client, "register", register_mock)

    response = client.post(
        "/api/tickets",
        json={
            "event_id": "missing-event",
            "first_name": "Ivan",
            "last_name": "Petrov",
            "email": "ivan@example.com",
            "seat": "A1",
        },
    )

    assert response.status_code == 404
    register_mock.assert_not_awaited()


def test_cancel_ticket_success(client, event, monkeypatch):
    from events_aggregator.main import provider_client

    ticket = Ticket(
        ticket_id="ticket-123",
        event_id="test-event-001",
        first_name="Ivan",
        last_name="Petrov",
        email="ivan@example.com",
        seat="A1",
        status="active",
    )

    session = MagicMock()
    session.get = AsyncMock(return_value=ticket)
    session.commit = AsyncMock()

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    unregister_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(provider_client, "unregister", unregister_mock)

    try:
        with TestClient(app) as test_client:
            response = test_client.delete("/api/tickets/ticket-123")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"success": True}
    assert ticket.status == "cancelled"
    session.commit.assert_awaited_once()
    unregister_mock.assert_awaited_once_with(
        event_id="test-event-001",
        ticket_id="ticket-123",
    )


def test_cancel_ticket_returns_404_for_missing_ticket(monkeypatch):
    from events_aggregator.main import provider_client

    session = MagicMock()
    session.get = AsyncMock(return_value=None)

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    unregister_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(provider_client, "unregister", unregister_mock)

    try:
        with TestClient(app) as test_client:
            response = test_client.delete("/api/tickets/missing-ticket")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    unregister_mock.assert_not_awaited()


def test_cancel_ticket_returns_409_if_already_cancelled(monkeypatch):
    from events_aggregator.main import provider_client

    ticket = Ticket(
        ticket_id="ticket-123",
        event_id="test-event-001",
        first_name="Ivan",
        last_name="Petrov",
        email="ivan@example.com",
        seat="A1",
        status="cancelled",
    )

    session = MagicMock()
    session.get = AsyncMock(return_value=ticket)

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    unregister_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(provider_client, "unregister", unregister_mock)

    try:
        with TestClient(app) as test_client:
            response = test_client.delete("/api/tickets/ticket-123")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    unregister_mock.assert_not_awaited()


def test_cancel_ticket_returns_502_if_provider_fails(monkeypatch):
    from events_aggregator.main import provider_client

    ticket = Ticket(
        ticket_id="ticket-123",
        event_id="test-event-001",
        first_name="Ivan",
        last_name="Petrov",
        email="ivan@example.com",
        seat="A1",
        status="active",
    )

    session = MagicMock()
    session.get = AsyncMock(return_value=ticket)
    session.commit = AsyncMock()

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    unregister_mock = AsyncMock(return_value=False)
    monkeypatch.setattr(provider_client, "unregister", unregister_mock)

    try:
        with TestClient(app) as test_client:
            response = test_client.delete("/api/tickets/ticket-123")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert ticket.status == "active"
    session.commit.assert_not_awaited()
    unregister_mock.assert_awaited_once_with(
        event_id="test-event-001",
        ticket_id="ticket-123",
    )


def test_cancel_ticket_returns_502_on_provider_exception(monkeypatch):
    from events_aggregator.main import provider_client

    ticket = Ticket(
        ticket_id="ticket-123",
        event_id="test-event-001",
        first_name="Ivan",
        last_name="Petrov",
        email="ivan@example.com",
        seat="A1",
        status="active",
    )

    session = MagicMock()
    session.get = AsyncMock(return_value=ticket)
    session.commit = AsyncMock()

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    unregister_mock = AsyncMock(side_effect=RuntimeError("Provider unavailable"))
    monkeypatch.setattr(provider_client, "unregister", unregister_mock)

    try:
        with TestClient(app) as test_client:
            response = test_client.delete("/api/tickets/ticket-123")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert ticket.status == "active"
    session.commit.assert_not_awaited()
    unregister_mock.assert_awaited_once_with(
        event_id="test-event-001",
        ticket_id="ticket-123",
    )
