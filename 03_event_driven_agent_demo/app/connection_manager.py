"""WebSocket connection manager.

This small helper keeps the main application code clean and readable.
"""

from __future__ import annotations

from fastapi import WebSocket


class ConnectionManager:
    """Track connected WebSocket clients and broadcast JSON updates."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket client and store the connection."""

        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a client if it is present in the active list."""

        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_json(self, message: dict) -> None:
        """Send the same JSON message to every active client.

        Dead connections are removed quietly. This keeps the demo resilient
        without making the code complicated.
        """

        dead_connections: list[WebSocket] = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        for connection in dead_connections:
            self.disconnect(connection)
