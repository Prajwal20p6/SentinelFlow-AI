"""
SentinelFlow AI — Redis Pub/Sub Integration
Enables horizontal scaling of WebSocket connections across multiple server workers.
"""

import json
import threading
from typing import Dict, Any, Callable
from ..core.config import get_settings
from ..core.observability import logger
from ..core.redis_streams import REDIS_AVAILABLE, _redis_client

settings = get_settings()

WS_BROADCAST_CHANNEL = "sentinelflow:ws:broadcast"


class RedisPubSubManager:
    """Manages Redis Pub/Sub subscription and broadcasting."""

    def __init__(self):
        self._pubsub = None
        self._listener_thread = None
        self._callback: Callable[[str, Dict[str, Any]], None] = None

    def start_listening(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Start a background listener thread for Redis Pub/Sub broadcasts."""
        self._callback = callback

        if not REDIS_AVAILABLE or _redis_client is None:
            logger.info("Redis unavailable. Bypassing pub/sub listener setup.")
            return

        try:
            self._pubsub = _redis_client.pubsub(ignore_subscribe_messages=True)
            self._pubsub.subscribe(WS_BROADCAST_CHANNEL)
            
            self._listener_thread = threading.Thread(
                target=self._pubsub_loop,
                daemon=True,
                name="sentinelflow-pubsub"
            )
            self._listener_thread.start()
            logger.info(f"Redis Pub/Sub listener started on channel: '{WS_BROADCAST_CHANNEL}'")
        except Exception as e:
            logger.error(f"Failed to start Redis Pub/Sub listener: {e}")

    def _pubsub_loop(self) -> None:
        """Pub/Sub polling loop executing in a daemon background thread."""
        while True:
            try:
                if self._pubsub is None:
                    break
                message = self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    payload = json.loads(message["data"])
                    msg_type = payload.get("type")
                    data = payload.get("data")
                    if msg_type and data is not None and self._callback:
                        self._callback(msg_type, data)
            except Exception as loop_err:
                logger.error(f"Error in Redis Pub/Sub listener thread: {loop_err}")

    def publish(self, msg_type: str, data: Dict[str, Any]) -> None:
        """Publish a message to the pub/sub channel for other nodes to pick up."""
        payload = {"type": msg_type, "data": data}
        
        # 1. Publish to Redis if connected
        if REDIS_AVAILABLE and _redis_client is not None:
            try:
                _redis_client.publish(WS_BROADCAST_CHANNEL, json.dumps(payload))
                return
            except Exception as e:
                logger.error(f"Redis publish failed: {e}")

        # 2. Local fallback if Redis is offline
        if self._callback:
            try:
                self._callback(msg_type, data)
            except Exception as e:
                logger.error(f"Local pubsub callback failed: {e}")


# Global Pub/Sub Manager Instance
pubsub_manager = RedisPubSubManager()
