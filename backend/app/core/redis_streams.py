"""
SentinelFlow AI — Redis Streams Abstraction
Provides Redis Streams-compatible event bus with automatic fallback to in-memory
queue when Redis is unavailable (for hackathon/demo environments).
"""

import json
import time
import threading
from collections import defaultdict, deque
from typing import Optional, Any
from datetime import datetime, timezone

from .config import get_settings

settings = get_settings()

# ── Try connecting to real Redis ─────────────────────────────
_redis_client = None

try:
    import redis as redis_lib
    pool = redis_lib.ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
        decode_responses=True,
        socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT,
    )
    _redis_client = redis_lib.Redis(connection_pool=pool)
    _redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False
    _redis_client = None


class InMemoryStreamBus:
    """In-memory Redis Streams simulation for zero-dependency development."""

    def __init__(self):
        self._streams: dict[str, deque] = defaultdict(deque)
        self._groups: dict[str, dict[str, int]] = defaultdict(dict)
        self._lock = threading.Lock()
        self._counter = 0

    def xadd(self, stream: str, fields: dict, maxlen: int = 10000) -> str:
        """Add a message to a stream. Returns message ID."""
        with self._lock:
            self._counter += 1
            msg_id = f"{int(time.time() * 1000)}-{self._counter}"
            self._streams[stream].append({
                "id": msg_id,
                "fields": fields,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            # Enforce maxlen
            while len(self._streams[stream]) > maxlen:
                self._streams[stream].popleft()
            return msg_id

    def xread(
        self, streams: dict[str, str], count: int = 10, block: int = 0
    ) -> list:
        """Read messages from streams starting after given IDs."""
        results = []
        for stream_name, last_id in streams.items():
            messages = []
            for msg in self._streams.get(stream_name, []):
                if last_id == "0" or msg["id"] > last_id:
                    messages.append((msg["id"], msg["fields"]))
            if messages:
                results.append((stream_name, messages[:count]))
        return results

    def xlen(self, stream: str) -> int:
        """Get the number of messages in a stream."""
        return len(self._streams.get(stream, []))

    def xrange(self, stream: str, start: str = "-", end: str = "+", count: int = 100) -> list:
        """Get messages in a range."""
        msgs = list(self._streams.get(stream, []))
        return [(m["id"], m["fields"]) for m in msgs[:count]]


class StreamBus:
    """
    Unified stream bus interface.
    Uses Redis when available, falls back to in-memory.
    """

    def __init__(self):
        self._fallback = InMemoryStreamBus()

    @property
    def is_redis(self) -> bool:
        return REDIS_AVAILABLE and _redis_client is not None

    def publish(self, stream: str, data: dict, maxlen: int = 10000) -> str:
        """Publish a message to a stream."""
        serialized = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in data.items()}

        if self.is_redis:
            try:
                return _redis_client.xadd(stream, serialized, maxlen=maxlen)
            except Exception:
                pass

        return self._fallback.xadd(stream, serialized, maxlen=maxlen)

    def consume(
        self,
        stream: str,
        last_id: str = "0",
        count: int = 50,
    ) -> list[tuple[str, dict]]:
        """Consume messages from a stream."""
        if self.is_redis:
            try:
                result = _redis_client.xread({stream: last_id}, count=count, block=0)
                if result:
                    return [(msg_id, fields) for _, messages in result for msg_id, fields in messages]
                return []
            except Exception:
                pass

        raw = self._fallback.xread({stream: last_id}, count=count)
        if raw:
            return [(msg_id, fields) for _, messages in raw for msg_id, fields in messages]
        return []

    def stream_length(self, stream: str) -> int:
        """Get message count in a stream."""
        if self.is_redis:
            try:
                return _redis_client.xlen(stream)
            except Exception:
                pass
        return self._fallback.xlen(stream)

    def cache_set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set a cached value with TTL (seconds)."""
        serialized = json.dumps(value)
        if self.is_redis:
            try:
                _redis_client.setex(key, ttl, serialized)
                return
            except Exception:
                pass
        # Fallback: no caching in memory mode (acceptable for demo)

    def cache_get(self, key: str) -> Optional[Any]:
        """Get a cached value."""
        if self.is_redis:
            try:
                val = _redis_client.get(key)
                return json.loads(val) if val else None
            except Exception:
                pass
        return None


# ── Global singleton ─────────────────────────────────────────
stream_bus = StreamBus()
