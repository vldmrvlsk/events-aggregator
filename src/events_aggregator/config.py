
import os

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DATABASE_NAME = os.getenv(
    "POSTGRES_DATABASE_NAME",
    "events_aggregator",
)
POSTGRES_USERNAME = os.getenv("POSTGRES_USERNAME", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

EVENTS_PROVIDER_URL = os.getenv(
    "EVENTS_PROVIDER_URL",
    "http://events-provider.dev-2.python-labs.ru",
)
EVENTS_PROVIDER_API_KEY = os.getenv("EVENTS_PROVIDER_API_KEY", "")

POSTGRES_CONNECTION_STRING = os.getenv("POSTGRES_CONNECTION_STRING", "")
