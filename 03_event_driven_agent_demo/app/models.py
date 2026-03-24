"""Shared data models for the event-driven agent demo."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventIn(BaseModel):
    """Request model used by external systems to send events into the API."""

    event_type: str = Field(..., examples=["ticket.created"])
    ticket_id: str = Field(..., examples=["T-1001"])
    correlation_id: str = Field(..., examples=["corr-1001"])
    payload: dict[str, Any]


class Event(BaseModel):
    """Internal event model used everywhere inside the application."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    ticket_id: str
    correlation_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: dict[str, Any]


class TicketState(BaseModel):
    """Current state of a ticket as seen by the support operations dashboard."""

    ticket_id: str
    correlation_id: str
    latest_event_type: str
    status: str
    category: str | None = None
    priority: str | None = None
    assigned_team: str | None = None
    summary: str | None = None
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
