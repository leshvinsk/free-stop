"""
Redis-backed cache layer. When REDIS_URL is set the client connects on first use.
All callers get None / no-op when Redis is unavailable — no exceptions propagate.

Every read pushes the key's expiry back by TTL_DAYS, so anything still being served stays
cached indefinitely while keys left behind by an older version of the code expire on their own.
"""

from __future__ import annotations

import logging
import os
import pickle
import time
from typing import Any

logger = logging.getLogger(__name__)

TTL_DAYS = 60

_client: Any = None  # redis.Redis | None
_next_attempt = 0.0
# Redis is reached over the internet, so a failed connection is retried rather than
# disabling the cache until the next restart
_RETRY_SECONDS = 60
# Cleared if the Redis user is not allowed GETEX; plain GET is used from then on
_refresh_on_read = True


def _get() -> Any:
    """Return a live Redis client, or None if unavailable."""
    global _client, _next_attempt
    if _client is not None or time.monotonic() < _next_attempt:
        return _client
    _next_attempt = time.monotonic() + _RETRY_SECONDS

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


def _read(c: Any, key: str) -> bytes | None:
    """GET that also pushes the expiry back, falling back to plain GET if not permitted."""
    global _refresh_on_read
    if _refresh_on_read:
        from redis.exceptions import ResponseError

        try:
            return c.getex(key, ex=TTL_DAYS * 86400)  # type: ignore[no-any-return]
        except ResponseError as exc:
            _refresh_on_read = False
            logger.warning("Redis GETEX not permitted, keys will expire on schedule: %s", exc)
    return c.get(key)  # type: ignore[no-any-return]


def load(key: str) -> Any:
    c = _get()
    if c is None:
        return None
    try:
        raw = _read(c, key)
        return pickle.loads(raw) if raw else None  # noqa: S301
    except Exception as exc:
        logger.debug("Redis load failed for %s: %s", key, exc)
        return None


def save(key: str, value: Any) -> None:
    c = _get()
    if c is None:
        return
    try:
        c.setex(key, TTL_DAYS * 86400, pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))
    except Exception as exc:
        logger.debug("Redis save failed for %s: %s", key, exc)


def load_text(key: str) -> str | None:
    """A JSON document stored with save_text, or None."""
    c = _get()
    if c is None:
        return None
    try:
        raw = _read(c, key)
        return raw.decode("utf-8") if raw else None
    except Exception as exc:
        logger.debug("Redis load failed for %s: %s", key, exc)
        return None


def save_text(key: str, text: str) -> None:
    c = _get()
    if c is None:
        return
    try:
        c.setex(key, TTL_DAYS * 86400, text.encode("utf-8"))
    except Exception as exc:
        logger.debug("Redis save failed for %s: %s", key, exc)
