"""
SentinelFlow AI — Production Configuration Overrides
Centralizes production database pool sizes, Redis connection policies, and Qdrant timeout limits.
"""

import os

# Database Connection Pool settings (PostgreSQL connection optimization)
DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "20"))
DATABASE_MAX_OVERFLOW = int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))
DATABASE_POOL_TIMEOUT = int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))

# Redis Connection settings (Connection pooling parameters)
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
REDIS_CONNECT_TIMEOUT = int(os.getenv("REDIS_CONNECT_TIMEOUT", "5"))

# Qdrant Timeout Settings
QDRANT_TIMEOUT = float(os.getenv("QDRANT_TIMEOUT", "10.0"))
