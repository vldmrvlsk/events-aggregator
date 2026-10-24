from enum import StrEnum


class EventStatus(StrEnum):
    PUBLISHED = "published"


class TicketStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class SyncStatus(StrEnum):
    NEVER = "never"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
