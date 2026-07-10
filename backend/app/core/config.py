"""
SentinelFlow AI — Application Configuration
Centralized settings with environment variable support and validation.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── General ──────────────────────────────────────────────
    PROJECT_NAME: str = "SentinelFlow AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ── Server ───────────────────────────────────────────────
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000

    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./sentinelflow.db"

    # ── Redis ────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Qdrant ───────────────────────────────────────────────
    QDRANT_MODE: str = "local"  # "local" or "server"
    QDRANT_PATH: str = "./data/qdrant"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "runbooks"
    QDRANT_VECTOR_SIZE: int = 384

    # ── Authentication ───────────────────────────────────────
    SECRET_KEY: str = "sentinelflow-dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days

    # ── Encryption ───────────────────────────────────────────
    ENCRYPTION_KEY: str = "sentinelflow-aes256-encryption-key!!"
    ENCRYPTION_KEYS: str = ""

    # ── LLM ──────────────────────────────────────────────────
    LLM_PROVIDER: str = "simulation"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_COST_SENSITIVE: bool = False
    LLM_LATENCY_CRITICAL: bool = False

    # ── Mastra ───────────────────────────────────────────────
    MASTRA_URL: str = "http://localhost:4111"
    MASTRA_SERVICE_URL: str = "http://localhost:3001"
    MASTRA_ENABLED: bool = True

    # Official Enkrypt Configuration (verified from official docs)
    ENKRYPTAI_API_KEY: str = ""
    ENKRYPTAI_BASE_URL: str = "https://api.enkryptai.com"
    ENKRYPTAI_ENABLED: bool = True

    # ── Slack ────────────────────────────────────────────────
    SLACK_ENABLED: bool = False
    SLACK_BOT_TOKEN: str = ""
    SLACK_WEBHOOK_URL: str = "http://localhost:8000/api/v1/integrations/slack/webhook"
    SLACK_CHANNEL: str = "#sentinelflow-alerts"

    # ── Threat Intelligence ──────────────────────────────────
    THREAT_INTEL_API_KEY: str = "sf-threat-intel-secret-key"
    VIRUSTOTAL_API_KEY: str = ""
    ABUSEIPDB_API_KEY: str = ""

    # ── Feature Flags ────────────────────────────────────────
    FF_DEMO_MODE: bool = True
    FF_SLACK_NOTIFICATIONS: bool = False
    FF_CLOUD_REMEDIATION: bool = True
    FF_MFA_REQUIRED: bool = False
    FF_WEBSOCKET_UPDATES: bool = True

    # ── Observability ────────────────────────────────────────
    OTEL_ENABLED: bool = True
    OTEL_EXPORTER: str = "console"
    OTEL_SERVICE_NAME: str = "sentinelflow-backend"

    # ── Rate Limiting ────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ── Production Pool Settings ─────────────────────────────
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_CONNECT_TIMEOUT: int = 5
    QDRANT_TIMEOUT: float = 10.0

    def __init__(self, **values):
        super().__init__(**values)
        if self.ENVIRONMENT == "production":
            try:
                import sys
                import os
                backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                if backend_dir not in sys.path:
                    sys.path.insert(0, backend_dir)
                
                from config import production
                if "DATABASE_POOL_SIZE" not in os.environ:
                    self.DATABASE_POOL_SIZE = production.DATABASE_POOL_SIZE
                if "DATABASE_MAX_OVERFLOW" not in os.environ:
                    self.DATABASE_MAX_OVERFLOW = production.DATABASE_MAX_OVERFLOW
                if "DATABASE_POOL_TIMEOUT" not in os.environ:
                    self.DATABASE_POOL_TIMEOUT = production.DATABASE_POOL_TIMEOUT
                if "REDIS_MAX_CONNECTIONS" not in os.environ:
                    self.REDIS_MAX_CONNECTIONS = production.REDIS_MAX_CONNECTIONS
                if "REDIS_CONNECT_TIMEOUT" not in os.environ:
                    self.REDIS_CONNECT_TIMEOUT = production.REDIS_CONNECT_TIMEOUT
                if "QDRANT_TIMEOUT" not in os.environ:
                    self.QDRANT_TIMEOUT = production.QDRANT_TIMEOUT
            except Exception:
                pass

    @property
    def get_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings singleton."""
    return Settings()
