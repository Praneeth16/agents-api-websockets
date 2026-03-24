"""Main FastAPI application for the event-driven support operations demo.

Features included:
- REST endpoint to ingest events
- background queue for asynchronous processing
- SQLite-backed event log and ticket state store
- WebSocket endpoint for a live dashboard
- HTML dashboard with live updates and ticket submission

Run:
    uvicorn app.main:app --reload --port 8002
Open:
    http://127.0.0.1:8002/dashboard
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from .agent import SupportOperationsAgent
from .connection_manager import ConnectionManager
from .models import Event, EventIn
from .storage import SqliteStore

load_dotenv()

app = FastAPI(title="Event-Driven Agent Demo", version="1.0.0")

store = SqliteStore()
manager = ConnectionManager()
event_queue: asyncio.Queue[Event] = asyncio.Queue()


async def publish_event(event: Event) -> None:
    """Save an event, update ticket state, and broadcast it to WebSocket clients."""

    await store.append_event(event)
    await _update_ticket_state_from_event(event)

    await manager.broadcast_json(
        {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "ticket_id": event.ticket_id,
            "correlation_id": event.correlation_id,
            "timestamp": event.timestamp,
            "payload": event.payload,
        }
    )


agent = SupportOperationsAgent(publish_event_callback=publish_event)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialise the database and start the background worker."""

    await store.init_db()
    asyncio.create_task(event_worker())


async def event_worker() -> None:
    """Continuously consume events from the queue and process them."""

    while True:
        event = await event_queue.get()
        try:
            await publish_event(event)
            await agent.handle_event(event)
        finally:
            event_queue.task_done()


@app.get("/")
def root() -> dict:
    """Simple landing route with useful links for students."""

    return {
        "message": "Event-driven agent demo is running.",
        "links": {
            "dashboard": "/dashboard",
            "health": "/health",
            "event_log": "/events/log",
            "ticket_states": "/tickets",
        },
    }


@app.get("/health")
def health() -> dict:
    """Basic health route."""

    return {"status": "ok"}


@app.post("/events", status_code=202)
async def ingest_event(payload: EventIn) -> dict:
    """Receive a new event and queue it for background processing."""

    event = Event(
        event_type=payload.event_type,
        ticket_id=payload.ticket_id,
        correlation_id=payload.correlation_id,
        payload=payload.payload,
    )
    await event_queue.put(event)
    return {
        "status": "accepted",
        "event_id": event.event_id,
        "ticket_id": event.ticket_id,
    }


@app.get("/events/log")
async def get_event_log() -> list[dict]:
    """Return all published events in JSON form."""

    events = await store.get_events()
    return [e.model_dump() for e in events]


@app.get("/tickets")
async def list_ticket_states() -> list[dict]:
    """Return the latest state for every known ticket."""

    states = await store.get_all_ticket_states()
    return [s.model_dump() for s in states]


@app.get("/tickets/{ticket_id}")
async def get_ticket_state(ticket_id: str) -> dict:
    """Return the current state for a single ticket if it exists."""

    state = await store.get_ticket_state(ticket_id)
    if state is None:
        return {"message": "Ticket not found"}
    return state.model_dump()


@app.get("/dashboard")
def dashboard() -> FileResponse:
    """Serve the HTML dashboard for the live demo."""

    dashboard_path = Path(__file__).resolve().parents[1] / "static" / "dashboard.html"
    return FileResponse(dashboard_path)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle live dashboard connections."""

    await manager.connect(websocket)

    await websocket.send_json(
        {
            "event_type": "system.connected",
            "ticket_id": "-",
            "payload": {"message": "Dashboard connected to live updates."},
        }
    )

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def _update_ticket_state_from_event(event: Event) -> None:
    """Translate events into a dashboard-friendly ticket state."""

    event_type = event.event_type
    payload = event.payload

    if event_type == "ticket.created":
        await store.upsert_ticket_state(
            ticket_id=event.ticket_id,
            correlation_id=event.correlation_id,
            latest_event_type=event_type,
            status="received",
            summary=str(payload.get("message", ""))[:120],
        )
        return

    if event_type == "ticket.processing.started":
        await store.upsert_ticket_state(
            ticket_id=event.ticket_id,
            correlation_id=event.correlation_id,
            latest_event_type=event_type,
            status="processing",
            summary=payload.get("message"),
        )
        return

    if event_type == "ticket.classified":
        await store.upsert_ticket_state(
            ticket_id=event.ticket_id,
            correlation_id=event.correlation_id,
            latest_event_type=event_type,
            status="classified",
            category=payload.get("category"),
            priority=payload.get("priority"),
            assigned_team=payload.get("assigned_team"),
            summary=payload.get("summary"),
        )
        return

    if event_type == "ticket.escalated":
        await store.upsert_ticket_state(
            ticket_id=event.ticket_id,
            correlation_id=event.correlation_id,
            latest_event_type=event_type,
            status="escalated",
            assigned_team=payload.get("assigned_team"),
            summary=payload.get("reason"),
        )
        return

    if event_type == "ticket.routed":
        await store.upsert_ticket_state(
            ticket_id=event.ticket_id,
            correlation_id=event.correlation_id,
            latest_event_type=event_type,
            status="routed",
            assigned_team=payload.get("assigned_team"),
            summary=payload.get("message"),
        )
        return

    if event_type == "ticket.update.received":
        await store.upsert_ticket_state(
            ticket_id=event.ticket_id,
            correlation_id=event.correlation_id,
            latest_event_type=event_type,
            status="updated",
            summary=str(payload),
        )
        return

    await store.upsert_ticket_state(
        ticket_id=event.ticket_id,
        correlation_id=event.correlation_id,
        latest_event_type=event_type,
        status="observed",
        summary=str(payload),
    )
