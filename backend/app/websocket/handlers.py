"""
SentinelFlow AI — WebSocket Client Message Handlers
Processes incoming client WebSocket requests, validating payload boundaries and routing actions.
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any
from ..core.observability import logger
from .manager import ws_connection_manager


async def handle_client_message(session_id: str, message_text: str) -> None:
    """Validate message boundaries and process subscribe, unsubscribe, and ping actions."""
    # 1. Validate payload size constraint (Max 1MB / 1,048,576 bytes)
    if len(message_text.encode("utf-8")) > 1048576:
        logger.warning(f"Payload from session '{session_id}' exceeds 1MB limit. Action rejected.")
        return

    # 2. Parse payload JSON structure
    try:
        payload = json.loads(message_text)
    except json.JSONDecodeError:
        logger.warning(f"Malformed JSON payload received from session '{session_id}'")
        return

    action = payload.get("action")
    if not action:
        return

    # 3. Handle Actions
    if action == "ping":
        # Keepalive handshake response
        sock = ws_connection_manager.active_sockets.get(session_id)
        if sock:
            try:
                await sock.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }))
            except Exception as e:
                logger.error(f"Failed to respond to ping on session '{session_id}': {e}")
        return

    elif action == "subscribe":
        incident_id = payload.get("incident_id")
        filters = payload.get("filters")
        if incident_id is not None:
            ws_connection_manager.subscribe(session_id, int(incident_id), filters)

    elif action == "unsubscribe":
        incident_id = payload.get("incident_id")
        if incident_id is not None:
            ws_connection_manager.unsubscribe(session_id, int(incident_id))
