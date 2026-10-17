
FROM python:3.13-slim

RUN addgroup --system --gid 1000 appuser && \
    adduser --system --uid 1000 --ingroup appuser appuser

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./

RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev

ENV UV_CACHE_DIR=/tmp/uv-cache
ENV HOME=/tmp

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "uv run --no-sync alembic upgrade head && exec uv run --no-sync uvicorn events_aggregator.main:app --host 0.0.0.0 --port 8000"]