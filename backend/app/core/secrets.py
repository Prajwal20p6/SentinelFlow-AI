"""
SentinelFlow AI — Centralized Secrets Management Provider
Provides a unified abstraction for reading credentials and sensitive secrets
from environment variables (default, zero-config local/demo) or cloud secret managers
(e.g., AWS Secrets Manager).
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SecretProvider(ABC):
    """Abstract Base Class for Secret Providers."""

    @abstractmethod
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve secret value by key name."""
        pass


class EnvSecretProvider(SecretProvider):
    """Environment Variable Secret Provider (Local Dev / Standard Env vars)."""

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return os.getenv(key, default)


class AWSSecretProvider(SecretProvider):
    """AWS Secrets Manager Provider with caching and fallback support."""

    def __init__(self, region_name: Optional[str] = None, secret_bundle_name: Optional[str] = None):
        self.region_name = region_name or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
        self.secret_bundle_name = secret_bundle_name or os.getenv("AWS_SECRET_NAME") or "sentinelflow/production/secrets"
        self._cache: Dict[str, str] = {}
        self._bundle_loaded: bool = False
        self._boto_client: Any = None

    def _get_boto_client(self) -> Any:
        if self._boto_client is None:
            try:
                import boto3
                self._boto_client = boto3.client("secretsmanager", region_name=self.region_name)
            except Exception as exc:
                logger.warning(f"aws_secrets_manager_init_failed: {exc}")
                self._boto_client = False
        return self._boto_client

    def _load_secret_bundle(self) -> None:
        if self._bundle_loaded:
            return
        client = self._get_boto_client()
        if client:
            try:
                response = client.get_secret_value(SecretId=self.secret_bundle_name)
                if "SecretString" in response:
                    payload = json.loads(response["SecretString"])
                    if isinstance(payload, dict):
                        for k, v in payload.items():
                            self._cache[k.upper()] = str(v)
            except Exception as exc:
                logger.warning(f"aws_secrets_bundle_fetch_failed for {self.secret_bundle_name}: {exc}")
        self._bundle_loaded = True

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        upper_key = key.upper()
        # 1. Check cache first
        if upper_key in self._cache:
            return self._cache[upper_key]

        # 2. Try loading JSON bundle from AWS Secrets Manager
        self._load_secret_bundle()
        if upper_key in self._cache:
            return self._cache[upper_key]

        # 3. Try fetching single secret by key name from AWS Secrets Manager
        client = self._get_boto_client()
        if client:
            try:
                response = client.get_secret_value(SecretId=key)
                if "SecretString" in response:
                    val = response["SecretString"]
                    self._cache[upper_key] = val
                    return val
            except Exception:
                pass

        # 4. Fallback to OS environment variable
        env_val = os.getenv(key)
        if env_val is not None:
            self._cache[upper_key] = env_val
            return env_val

        return default


_secret_provider_instance: Optional[SecretProvider] = None


def get_secret_provider() -> SecretProvider:
    """Factory function to get active SecretProvider instance."""
    global _secret_provider_instance
    if _secret_provider_instance is None:
        provider_type = os.getenv("SECRETS_PROVIDER", "env").strip().lower()
        if provider_type == "aws":
            _secret_provider_instance = AWSSecretProvider()
        else:
            _secret_provider_instance = EnvSecretProvider()
    return _secret_provider_instance


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Centralized function to load a secret value.
    Delegates to the configured SecretProvider (env or aws).
    """
    return get_secret_provider().get_secret(key, default)


def reset_secrets_cache() -> None:
    """Resets secret provider singleton (useful for unit testing)."""
    global _secret_provider_instance
    _secret_provider_instance = None
