"""
SentinelFlow AI — WebSocket Connection Manager
Maintains concurrent socket structures, tracks subscriptions, handles offline queues, and routes messages.
"""

import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Set, List
from fastapi import WebSocket, WebSocketDisconnect
from ..core.observability import logger
from ..integrations.redis_pubsub import pubsub_manager

class ConnectionManager:
    """Manages active socket channels, filtering logic, and offline queues."""

    def __init__(self):
        # session_id -> WebSocket
        self.active_sockets: Dict[str, WebSocket] = {}
        # user_id -> set of active session_ids
        self.user_sessions: Dict[int, Set[str]] = {}
        # session_id -> user_id
        self.session_users: Dict[str, int] = {}
        # session_id -> set of incident_ids subscribed
        self.session_subscriptions: Dict[str, Set[int]] = {}
        # incident_id -> set of session_ids subscribed
        self.incident_subscribers: Dict[int, Set[str]] = {}
        # session_id -> filters dict
        self.session_filters: Dict[str, Dict[str, Any]] = {}
        # user_id -> list of queued dict messages
        self.offline_queues: Dict[int, List[Dict[str, Any]]] = {}

    async def connect(self, websocket: WebSocket, user_id: int, session_id: str) -> None:
        """Accept connection, validate limit rate, and flush offline queues."""
        # 1. Enforce max 5 concurrent connections limit
        sessions = self.user_sessions.setdefault(user_id, set())
        if len(sessions) >= 5:
            logger.warning(f"Connection rate limit hit for User #{user_id}. Max concurrent connections (5) exceeded.")
            # Disconnect/close socket
            await websocket.accept()
            await websocket.close(code=4003, reason="Max concurrent sessions exceeded")
            return

        # 2. Accept and store socket session
        await websocket.accept()
        self.active_sockets[session_id] = websocket
        self.session_users[session_id] = user_id
        sessions.add(session_id)
        self.session_subscriptions[session_id] = set()
        self.session_filters[session_id] = {}

        try:
            from ..core.observability import track_ws_connection
            track_ws_connection(1)
        except Exception:
            pass

        logger.info(f"WebSocket session '{session_id}' accepted for User #{user_id}. Connections: {len(sessions)}/5")

        # 3. Flush offline queue messages
        if user_id in self.offline_queues:
            queued_msgs = self.offline_queues[user_id]
            # Keep only messages newer than 1 hour (3600 seconds)
            now_ts = time.time()
            valid_msgs = [m for m in queued_msgs if now_ts - m.get("_queued_at", 0) < 3600]
            
            for msg in valid_msgs:
                try:
                    await websocket.send_text(json.dumps(msg))
                except Exception as send_err:
                    logger.error(f"Failed to flush offline message to session {session_id}: {send_err}")
            
            del self.offline_queues[user_id]

    def disconnect(self, session_id: str) -> None:
        """Remove a session from tracking and clean up subscriptions."""
        if session_id not in self.active_sockets:
            return

        user_id = self.session_users.get(session_id)
        
        # Cleanup subscriptions mapping
        subs = self.session_subscriptions.get(session_id, set())
        for inc_id in subs:
            if inc_id in self.incident_subscribers:
                self.incident_subscribers[inc_id].discard(session_id)
                if not self.incident_subscribers[inc_id]:
                    del self.incident_subscribers[inc_id]

        if session_id in self.session_subscriptions:
            del self.session_subscriptions[session_id]
        if session_id in self.session_filters:
            del self.session_filters[session_id]

        # Clean user session registries
        if user_id is not None:
            if user_id in self.user_sessions:
                self.user_sessions[user_id].discard(session_id)
                if not self.user_sessions[user_id]:
                    del self.user_sessions[user_id]
            del self.session_users[session_id]

        if session_id in self.active_sockets:
            del self.active_sockets[session_id]
            try:
                from ..core.observability import track_ws_connection
                track_ws_connection(-1)
            except Exception:
                pass

        logger.info(f"WebSocket session '{session_id}' disconnected cleanly.")

    def subscribe(self, session_id: str, incident_id: int, filters: Optional[Dict[str, Any]] = None) -> None:
        """Subscribe session to updates for a specific incident."""
        if session_id not in self.active_sockets:
            return

        self.session_subscriptions.setdefault(session_id, set()).add(incident_id)
        self.incident_subscribers.setdefault(incident_id, set()).add(session_id)
        if filters:
            self.session_filters[session_id] = filters

        logger.info(f"WebSocket session '{session_id}' subscribed to Incident #{incident_id} with filters: {filters}")

    def unsubscribe(self, session_id: str, incident_id: int) -> None:
        """Unsubscribe session from specific incident updates."""
        if session_id in self.session_subscriptions:
            self.session_subscriptions[session_id].discard(incident_id)
        if incident_id in self.incident_subscribers:
            self.incident_subscribers[incident_id].discard(session_id)

    async def send_to_user_local(self, user_id: int, msg_type: str, data: Dict[str, Any]) -> bool:
        """Send a message to all active sessions of a local user. Returns True if delivered."""
        sessions = self.user_sessions.get(user_id, set())
        if not sessions:
            # Queue the message for offline user (up to 1 hour)
            payload = {
                "type": msg_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "_queued_at": time.time()
            }
            self.offline_queues.setdefault(user_id, []).append(payload)
            # Enforce max queue length of 100 per user
            if len(self.offline_queues[user_id]) > 100:
                self.offline_queues[user_id].pop(0)
            return False

        payload = {
            "type": msg_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        success = False
        broken_sessions = []
        for sid in list(sessions):
            sock = self.active_sockets.get(sid)
            if sock:
                try:
                    await sock.send_text(json.dumps(payload))
                    success = True
                    try:
                        from ..core.observability import track_ws_message_delivery
                        track_ws_message_delivery("success")
                    except Exception:
                        pass
                except Exception as err:
                    broken_sessions.append(sid)
                    logger.error(f"Failed to send WS message to session {sid}: {err}")
                    try:
                        from ..core.observability import track_ws_message_delivery
                        track_ws_message_delivery("failed")
                    except Exception:
                        pass

        for sid in broken_sessions:
            self.disconnect(sid)

        return success

    async def broadcast_incident_local(self, incident_id: int, msg_type: str, data: Dict[str, Any]) -> None:
        """Broadcast incident update event to all locally subscribed sessions."""
        subscribers = self.incident_subscribers.get(incident_id, set())
        if not subscribers:
            return

        payload = {
            "type": msg_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        broken_sessions = []
        for sid in list(subscribers):
            # Apply filters: check if message matches severity/service constraints
            filters = self.session_filters.get(sid)
            if filters:
                if "severity" in filters and data.get("severity") != filters["severity"]:
                    continue
                if "service" in filters and data.get("service") != filters["service"]:
                    continue

            sock = self.active_sockets.get(sid)
            if sock:
                try:
                    await sock.send_text(json.dumps(payload))
                except Exception as err:
                    broken_sessions.append(sid)
                    logger.error(f"Failed to send broadcast to session {sid}: {err}")

        for sid in broken_sessions:
            self.disconnect(sid)

    async def broadcast_all_local(self, msg_type: str, data: Dict[str, Any]) -> None:
        """Broadcast system-wide message to all connected local sessions."""
        payload = {
            "type": msg_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        broken_sessions = []
        for sid, sock in list(self.active_sockets.items()):
            try:
                await sock.send_text(json.dumps(payload))
            except Exception as err:
                broken_sessions.append(sid)
                logger.error(f"Failed to broadcast generic msg to session {sid}: {err}")

        for sid in broken_sessions:
            self.disconnect(sid)


# Instantiate the manager
ws_connection_manager = ConnectionManager()

# Store the main uvicorn event loop reference (set during lifespan startup)
_main_event_loop = None


def set_main_event_loop(loop) -> None:
    """Called during FastAPI lifespan to capture the running event loop."""
    global _main_event_loop
    _main_event_loop = loop
    logger.info("WebSocket broadcast: main event loop captured")


BROADCAST_TO_ALL_TYPES = {
    "LiveMetricsUpdate", "MastraExecution", "MetricsUpdate", "AgentActivity",
}


def pubsub_broadcast_handler(msg_type: str, data: Dict[str, Any]) -> None:
    """Forward pub/sub events to the running event loop of FastAPI if active."""
    import asyncio

    incident_id = data.get("incident_id")
    user_id = data.get("user_id")

    if msg_type in BROADCAST_TO_ALL_TYPES:
        coro = ws_connection_manager.broadcast_all_local(msg_type, data)
    elif incident_id is not None:
        coro = ws_connection_manager.broadcast_incident_local(int(incident_id), msg_type, data)
    elif user_id is not None:
        coro = ws_connection_manager.send_to_user_local(int(user_id), msg_type, data)
    else:
        coro = ws_connection_manager.broadcast_all_local(msg_type, data)

    # 1. Try to schedule on the currently running event loop (we're inside async context)
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
        return
    except RuntimeError:
        pass

    # 2. Fallback: use the stored main uvicorn event loop (we're in a sync thread)
    if _main_event_loop is not None and _main_event_loop.is_running():
        try:
            asyncio.run_coroutine_threadsafe(coro, _main_event_loop)
            return
        except Exception:
            pass

    # 3. Last resort: try get_event_loop (may not be uvicorn's loop)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop)
    except RuntimeError:
        pass


# Bind pub/sub callback to manager on module import
pubsub_manager.start_listening(pubsub_broadcast_handler)
