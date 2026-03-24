"""SQLite-backed storage for the event-driven agent demo.

Replaces the in-memory store with a local SQLite database so ticket
state survives restarts.  Uses aiosqlite for non-blocking access.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from .models import Event, TicketState

DB_PATH = Path(__file__).resolve().parents[1] / "demo.db"


class SqliteStore:
    """Persist events and ticket state in a local SQLite database."""

    def __init__(self, db_path: str | Path = DB_PATH) -> None:
        self.db_path = str(db_path)

    async def init_db(self) -> None:
        """Create tables if they don't exist."""

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id       TEXT PRIMARY KEY,
                    event_type     TEXT NOT NULL,
                    ticket_id      TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    timestamp      TEXT NOT NULL,
                    payload        TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ticket_states (
                    ticket_id        TEXT PRIMARY KEY,
                    correlation_id   TEXT NOT NULL,
                    latest_event_type TEXT NOT NULL,
                    status           TEXT NOT NULL,
                    category         TEXT,
                    priority         TEXT,
                    assigned_team    TEXT,
                    summary          TEXT,
                    last_updated     TEXT NOT NULL
                )
            """)
            await db.commit()

    async def append_event(self, event: Event) -> None:
        """Insert an event into the database."""

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO events "
                "(event_id, event_type, ticket_id, correlation_id, timestamp, payload) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    event.event_id,
                    event.event_type,
                    event.ticket_id,
                    event.correlation_id,
                    event.timestamp,
                    json.dumps(event.payload),
                ),
            )
            await db.commit()

    async def upsert_ticket_state(
        self,
        *,
        ticket_id: str,
        correlation_id: str,
        latest_event_type: str,
        status: str,
        category: str | None = None,
        priority: str | None = None,
        assigned_team: str | None = None,
        summary: str | None = None,
    ) -> TicketState:
        """Create or update the current state for a ticket.

        Uses COALESCE so that NULL new values preserve the previous row value.
        """

        now = datetime.now(timezone.utc).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO ticket_states
                    (ticket_id, correlation_id, latest_event_type, status,
                     category, priority, assigned_team, summary, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticket_id) DO UPDATE SET
                    correlation_id    = excluded.correlation_id,
                    latest_event_type = excluded.latest_event_type,
                    status            = excluded.status,
                    category          = COALESCE(excluded.category, ticket_states.category),
                    priority          = COALESCE(excluded.priority, ticket_states.priority),
                    assigned_team     = COALESCE(excluded.assigned_team, ticket_states.assigned_team),
                    summary           = COALESCE(excluded.summary, ticket_states.summary),
                    last_updated      = excluded.last_updated
                """,
                (ticket_id, correlation_id, latest_event_type, status,
                 category, priority, assigned_team, summary, now),
            )
            await db.commit()

            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM ticket_states WHERE ticket_id = ?", (ticket_id,),
            )
            row = await cursor.fetchone()

        return _row_to_ticket_state(row)

    async def get_events(self) -> list[Event]:
        """Return all stored events ordered by time."""

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM events ORDER BY timestamp")
            rows = await cursor.fetchall()

        return [
            Event(
                event_id=r["event_id"],
                event_type=r["event_type"],
                ticket_id=r["ticket_id"],
                correlation_id=r["correlation_id"],
                timestamp=r["timestamp"],
                payload=json.loads(r["payload"]),
            )
            for r in rows
        ]

    async def get_all_ticket_states(self) -> list[TicketState]:
        """Return the latest state for every ticket."""

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM ticket_states ORDER BY last_updated DESC",
            )
            rows = await cursor.fetchall()

        return [_row_to_ticket_state(r) for r in rows]

    async def get_ticket_state(self, ticket_id: str) -> TicketState | None:
        """Return the current state for a single ticket."""

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM ticket_states WHERE ticket_id = ?", (ticket_id,),
            )
            row = await cursor.fetchone()

        if row is None:
            return None
        return _row_to_ticket_state(row)


def _row_to_ticket_state(row: aiosqlite.Row) -> TicketState:
    """Convert a database row into a TicketState model."""

    return TicketState(
        ticket_id=row["ticket_id"],
        correlation_id=row["correlation_id"],
        latest_event_type=row["latest_event_type"],
        status=row["status"],
        category=row["category"],
        priority=row["priority"],
        assigned_team=row["assigned_team"],
        summary=row["summary"],
        last_updated=row["last_updated"],
    )
