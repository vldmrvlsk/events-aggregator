
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from events_aggregator.main import app, lifespan


@pytest.mark.asyncio
async def test_lifespan_starts_and_cancels_background_task():
    started = asyncio.Event()
    stopped = asyncio.Event()

    async def fake_worker():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    with patch(
        "events_aggregator.main.daily_sync_worker",
        side_effect=fake_worker,
    ):
        async with lifespan(app):
            await asyncio.wait_for(started.wait(), timeout=1)

        assert stopped.is_set()




@pytest.mark.asyncio
async def test_daily_sync_worker_logs_failure_and_retries():
    from events_aggregator.main import daily_sync_worker

    session_context = AsyncMock()
    session_context.__aenter__.return_value = AsyncMock()
    session_context.__aexit__.return_value = False

    logged = asyncio.Event()

    def record_error(*args, **kwargs):
        logged.set()

    with (
        patch(
            "events_aggregator.main.AsyncSessionLocal",
            return_value=session_context,
        ),
        patch(
            "events_aggregator.main.sync_events",
            new_callable=AsyncMock,
            side_effect=RuntimeError("provider unavailable"),
        ),
        patch(
            "events_aggregator.main.logger.exception",
            side_effect=record_error,
        ) as log_exception,
    ):
        task = asyncio.create_task(daily_sync_worker())

        try:
            await asyncio.wait_for(logged.wait(), timeout=1)
        finally:
            task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

    log_exception.assert_called_once_with("Daily event sync failed")
