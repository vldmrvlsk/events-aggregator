from typing import Any
from urllib.parse import quote, urljoin

import httpx

from events_aggregator.config import (
    EVENTS_PROVIDER_API_KEY,
    EVENTS_PROVIDER_URL,
)


class EventsProviderClient:
    def __init__(
        self,
        base_url: str = EVENTS_PROVIDER_URL,
        api_key: str = EVENTS_PROVIDER_API_KEY,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key}

    
    async def events(
        self,
        changed_at: str | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        url = cursor or urljoin(f"{self.base_url}/", "api/events/")
        params = {"changed_at": changed_at} if changed_at else None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                url,
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            payload = response.json()

        if not isinstance(payload, dict):
            raise TypeError("Provider returned an invalid events response")

        if not isinstance(payload.get("results"), list):
            raise TypeError("Provider returned an invalid events list")

        return payload


    async def seats(self, event_id: str) -> list[str]:
        url = urljoin(f"{self.base_url}/", f"api/events/{quote(event_id, safe='')}/seats/")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            payload: dict[str, Any] = response.json()

        seats = payload.get("seats")
        if not isinstance(seats, list) or not all(
            isinstance(seat, str) for seat in seats
        ):
            raise ValueError("Provider returned an invalid seats response")

        return seats

    async def register(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str:
        url = urljoin(f"{self.base_url}/", f"api/events/{quote(event_id, safe='')}/register/")
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "seat": seat,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()

        ticket_id = result.get("ticket_id")
        if not isinstance(ticket_id, str) or not ticket_id:
            raise ValueError("Provider returned an invalid ticket response")

        return ticket_id

    async def unregister(self, event_id: str, ticket_id: str) -> bool:
        url = urljoin(f"{self.base_url}/", f"api/events/{quote(event_id, safe='')}/unregister/")
        payload = {"ticket_id": ticket_id}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                "DELETE",
                url,
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()

        return result.get("success") is True
