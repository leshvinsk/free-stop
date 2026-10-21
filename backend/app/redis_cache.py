"""
Redis-backed cache layer. When REDIS_URL is set the client connects on first use.
All callers get None / no-op when Redis is unavailable — no exceptions propagate.
"""

from __future__ import annotations

import logging
import os
import pickle
from typing import Any

logger = logging.getLogger(__name__)

_client: Any = None  # redis.Redis | None
_checked = False


def _get() -> Any:
    """Return a live Redis client, or None if unavailable."""
    global _client, _checked
    if _checked:
        return _client
    _checked = True

    url = os.environ.get("REDIS_URL", "")
    if not url:
        return None

    try:
        import redis

        c = redis.from_url(url, decode_responses=False, socket_timeout=2, socket_connect_timeout=2)
        c.ping()
        _client = c
        logger.info("Redis connected (%s)", url.split("@")[-1])
    except Exception as exc:
        logger.warning("Redis unavailable, falling back to disk cache: %s", exc)
        _client = None

    return _client


def load(key: str) -> Any:
    c = _get()
    if c is None:
        return None
    try:
        raw = c.get(key)
        return pickle.loads(raw) if raw else None  # noqa: S301
    except Exception as exc:
        logger.debug("Redis load failed for %s: %s", key, exc)
        return None


def save(key: str, value: Any, ttl_days: int = 30) -> None:
    c = _get()
    if c is None:
        return
    try:
        c.setex(key, ttl_days * 86400, pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))
    except Exception as exc:
        logger.debug("Redis save failed for %s: %s", key, exc)
