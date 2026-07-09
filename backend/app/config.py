"""
Proxy config module forwarding settings to app.core.config.
"""
from .core.config import get_settings

settings = get_settings()
