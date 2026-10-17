
from collections.abc import AsyncGenerator

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from events_aggregator.config import (
    POSTGRES_CONNECTION_STRING,
    POSTGRES_DATABASE_NAME,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USERNAME,
)

if POSTGRES_CONNECTION_STRING:
    database_url = make_url(POSTGRES_CONNECTION_STRING).set(
        drivername="postgresql+asyncpg"
    )
else:
    database_url = make_url(
        f"postgresql+asyncpg://{POSTGRES_USERNAME}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE_NAME}"
    )

engine = create_async_engine(database_url, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
