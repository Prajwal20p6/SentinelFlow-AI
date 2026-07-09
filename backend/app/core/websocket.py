"""
SentinelFlow AI — WebSocket Manager
Real-time incident updates, telemetry streaming, and notification push.
"""

import json
from datetime import datetime, timezone

from fastapi import WebSocket

from .observability import logger


class ConnectionManager:
    """Manages active WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("ws_client_connected", total=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("ws_client_disconnected", total=len(self.active_connections))

    async def broadcast(self, message_type: str, data: dict):
        """Broadcast a message to all connected clients."""
        message = json.dumps({
            "type": message_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def send_to(self, websocket: WebSocket, message_type: str, data: dict):
        """Send a message to a specific client."""
        message = json.dumps({
            "type": message_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        try:
            await websocket.send_text(message)
        except Exception:
            self.disconnect(websocket)


# Global singleton
ws_manager = ConnectionManager()
