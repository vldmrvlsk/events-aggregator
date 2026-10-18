from pydantic import BaseModel, EmailStr, Field


class TicketCreate(BaseModel):
    event_id: str = Field(min_length=1, max_length=36)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    seat: str = Field(min_length=1, max_length=50)