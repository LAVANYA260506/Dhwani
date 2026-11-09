"""Pydantic schemas for the application event trail."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    field_id: str | None
    source: str | None
    old_value: Any = None
    new_value: Any = None
    details: dict[str, Any] | None = None
    created_at: datetime


class EventList(BaseModel):
    """Events in chronological order. To poll for new ones, pass the last
    event ID you have as `after_id`."""

    events: list[EventRead]