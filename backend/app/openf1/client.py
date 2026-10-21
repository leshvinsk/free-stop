import asyncio
import hashlib
import json
import logging
import os
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, TypeAdapter
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.openf1.schemas import (
    CarSample,
    Driver,
    Lap,
    Location,
    Meeting,
    PitStop,
    RaceControlMessage,
    Session,
    SessionResult,
    Weather,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openf1.org/v1"
CACHE_DIR = Path(os.getenv("OPENF1_CACHE_DIR", Path(__file__).resolve().parents[2] / ".cache"))

T = TypeVar("T", bound=BaseModel)


class RateLimiter:
    """Sliding-window limiter enforcing both a per-second and a per-minute budget."""

    def __init__(self, per_second: int, per_minute: int) -> None:
        self._per_second = per_second
        self._per_minute = per_minute
        self._stamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        # Holding the lock while sleeping makes waiters queue FIFO.
        async with self._lock:
            while True:
                now = time.monotonic()
                while self._stamps and now - self._stamps[0] >= 60:
                    self._stamps.popleft()
                in_last_second = sum(1 for t in self._stamps if now - t < 1)
                if len(self._stamps) < self._per_minute and in_last_second < self._per_second:
                    self._stamps.append(now)
                    return
                waits = [0.05]
                if len(self._stamps) >= self._per_minute:
                    waits.append(60 - (now - self._stamps[0]))
                if in_last_second >= self._per_second:
                    waits.append(1 - (now - self._stamps[-self._per_second]))
                await asyncio.sleep(max(waits))


# OpenF1 free tier: 3 req/s and 30 req/min. Stay just under both.
_limiter = RateLimiter(
    per_second=3,
    per_minute=int(os.getenv("OPENF1_REQUESTS_PER_MINUTE", "28")),
)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    return isinstance(exc, (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError))


def _cache_path(path: str, params: dict[str, Any]) -> Path:
    key = json.dumps({"path": path, "params": params}, sort_keys=True)
    digest = hashlib.sha1(key.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{path.strip('/')}-{digest}.json"


def _read_disk(path: Path) -> list[dict[str, Any]] | None:
    try:
        return json.loads(path.read_text("utf-8"))  # type: ignore[no-any-return]
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _write_disk(path: Path, payload: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), "utf-8")
    tmp.replace(path)


@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def _fetch(
    client: httpx.AsyncClient, path: str, params: dict[str, Any]
) -> list[dict[str, Any]]:
    await _limiter.acquire()
    logger.info("OpenF1 GET %s %s", path, params)
    response = await client.get(f"{BASE_URL}{path}", params=params)
    if response.status_code == 404:
        # OpenF1 returns 404 when no records match the query (rather than [])
        return []
    if response.status_code == 429:
        retry_after = float(response.headers.get("Retry-After", "10"))
        logger.warning("OpenF1 rate limited; backing off %.0fs", retry_after)
        await asyncio.sleep(retry_after)
    response.raise_for_status()
    return response.json()  # type: ignore[no-any-return]


async def _get(
    client: httpx.AsyncClient,
    path: str,
    params: dict[str, Any],
    *,
    persist: bool = False,
    keep: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Fetch from OpenF1. With persist=True the response is stored on disk and reused forever,
    which is only safe for sessions whose data has settled. `keep` trims each record to the
    named fields so bulky payloads stay small on disk."""
    disk_path = _cache_path(path, params)
    if persist and (cached := _read_disk(disk_path)) is not None:
        return cached
    payload = await _fetch(client, path, params)
    if keep:
        payload = [{k: r.get(k) for k in keep} for r in payload]
    if persist and payload:
        _write_disk(disk_path, payload)
    return payload


_meeting_adapter = TypeAdapter(list[Meeting])
_session_adapter = TypeAdapter(list[Session])
_pit_adapter = TypeAdapter(list[PitStop])
_lap_adapter = TypeAdapter(list[Lap])
_weather_adapter = TypeAdapter(list[Weather])
_location_adapter = TypeAdapter(list[Location])
_car_adapter = TypeAdapter(list[CarSample])
_rc_adapter = TypeAdapter(list[RaceControlMessage])
_driver_adapter = TypeAdapter(list[Driver])
_result_adapter = TypeAdapter(list[SessionResult])


async def get_meetings(client: httpx.AsyncClient, year: int) -> list[Meeting]:
    raw = await _get(client, "/meetings", {"year": year})
    return _meeting_adapter.validate_python(raw)


async def get_sessions(client: httpx.AsyncClient, year: int) -> list[Session]:
    raw = await _get(client, "/sessions", {"year": year, "session_type": "Race"})
    return _session_adapter.validate_python(raw)


async def get_session(client: httpx.AsyncClient, session_key: int) -> Session | None:
    raw = await _get(client, "/sessions", {"session_key": session_key})
    sessions = _session_adapter.validate_python(raw)
    return sessions[0] if sessions else None


async def get_pit_stops(
    client: httpx.AsyncClient, session_key: int, *, persist: bool = False
) -> list[PitStop]:
    raw = await _get(client, "/pit", {"session_key": session_key}, persist=persist)
    # Drive-throughs and incomplete records come back without a duration
    return _pit_adapter.validate_python([r for r in raw if r.get("pit_duration")])


async def get_laps(
    client: httpx.AsyncClient, session_key: int, *, persist: bool = False
) -> list[Lap]:
    raw = await _get(
        client,
        "/laps",
        {"session_key": session_key},
        persist=persist,
        keep=(
            "driver_number",
            "lap_number",
            "date_start",
            "lap_duration",
            "duration_sector_1",
            "duration_sector_2",
        ),
    )
    return _lap_adapter.validate_python(raw)


async def get_race_control(
    client: httpx.AsyncClient, session_key: int, *, persist: bool = False
) -> list[RaceControlMessage]:
    raw = await _get(client, "/race_control", {"session_key": session_key}, persist=persist)
    return _rc_adapter.validate_python(raw)


async def get_drivers(
    client: httpx.AsyncClient, session_key: int, *, persist: bool = False
) -> list[Driver]:
    raw = await _get(client, "/drivers", {"session_key": session_key}, persist=persist)
    # OpenF1 can return duplicate driver entries per session; keep first occurrence
    seen: set[int] = set()
    drivers: list[Driver] = []
    for d in _driver_adapter.validate_python(raw):
        if d.driver_number not in seen:
            seen.add(d.driver_number)
            drivers.append(d)
    return drivers


async def get_session_result(
    client: httpx.AsyncClient, session_key: int, *, persist: bool = False
) -> list[SessionResult]:
    raw = await _get(
        client,
        "/session_result",
        {"session_key": session_key},
        persist=persist,
        keep=("driver_number", "dnf", "dns", "dsq"),
    )
    return _result_adapter.validate_python(raw)


async def get_meeting_sessions(client: httpx.AsyncClient, meeting_key: int) -> list[Session]:
    """Every session of a Grand Prix weekend (practice, qualifying, sprint, race)."""
    raw = await _get(client, "/sessions", {"meeting_key": meeting_key})
    return _session_adapter.validate_python(raw)


async def get_weather(
    client: httpx.AsyncClient, session_key: int, *, persist: bool = False
) -> list[Weather]:
    raw = await _get(client, "/weather", {"session_key": session_key}, persist=persist)
    return _weather_adapter.validate_python(raw)


def _window(session_key: int, driver: int, start: datetime, end: datetime) -> dict[str, Any]:
    # OpenF1 filters with operators in the key: date>=…&date<=…
    return {
        "session_key": session_key,
        "driver_number": driver,
        "date>": start.isoformat(),
        "date<": end.isoformat(),
    }


async def get_location(
    client: httpx.AsyncClient,
    session_key: int,
    driver: int,
    start: datetime,
    end: datetime,
    *,
    persist: bool = False,
) -> list[Location]:
    params = _window(session_key, driver, start, end)
    raw = await _get(client, "/location", params, persist=persist, keep=("date", "x", "y"))
    return _location_adapter.validate_python(raw)


async def get_car_data(
    client: httpx.AsyncClient,
    session_key: int,
    driver: int,
    start: datetime,
    end: datetime,
    *,
    persist: bool = False,
) -> list[CarSample]:
    params = _window(session_key, driver, start, end)
    raw = await _get(client, "/car_data", params, persist=persist, keep=("date", "speed", "drs"))
    return _car_adapter.validate_python(raw)
