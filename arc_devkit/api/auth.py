"""Shared API-key auth helpers for REST and WebSocket routes."""

import hmac
import os


def is_production() -> bool:
    """Read ENV at request time so tests can toggle it."""
    return os.getenv("ENV", "development").strip().lower() == "production"


def get_api_key() -> str | None:
    """Return the API key configured in the environment (optional)."""
    return os.getenv("API_KEY", "").strip() or None


def api_key_is_valid(candidate: str | None) -> bool:
    """Constant-time comparison against the configured API key."""
    required_key = get_api_key()
    if not required_key:
        return not is_production()
    if candidate is None:
        return False
    return hmac.compare_digest(candidate, required_key)
