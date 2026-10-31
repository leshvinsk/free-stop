"""
In-process store of scored race sessions.

- One in-flight scoring task per session, so concurrent requests never duplicate OpenF1 calls.
- Settled sessions are kept for the process lifetime and saved to disk (score_cache), so a
  restart loads them instead of re-scoring; sessions that finished recently are re-scored after
  RECENT_TTL to pick up late data.
- Stale-while-revalidate: once something has been fetched or scored, a visitor always gets the
  cached copy immediately and any refresh (calendar, recent scores, map, weather) runs in the
  background. Only the very first request for something waits on OpenF1.
- A background warmer scores a season race by race, so the leaderboard fills in progressively
  instead of blocking a request for minutes.
"""

import asyncio
import hashlib
import json
import logging
import time
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, TypeAdapter

from app import extras, headshots, photos, redis_cache, score_cache
from app.models import CircuitMap, RacePhotos, RaceWeather
from app.openf1 import client as openf1
from app.openf1.schemas import Session
from app.scoring.pipeline import SessionScore, score_session
from app.teams import FIRST_SEASON

logger = logging.getLogger(__name__)

RECENT_TTL = 300  # seconds before an unsettled session is re-scored
SESSIONS_TTL = 900  # seconds the season calendar is cached
FAILURE_COOLDOWN = 300  # seconds before a failed session is retried
INCOMPLETE_RETRY = 3600  # seconds before a race scored without lap timing is re-scored
SETTLE_DELAY = timedelta(hours=3)  # OpenF1 data is final this long after a race ends

# Finished races' maps, weather and photos, and finished seasons' calendars, are kept in Redis
# so a restart or deploy never sends a visitor back to OpenF1 for them. Keys carry a
# fingerprint of the code that builds them, so a change to that code rebuilds them.
_APP = Path(__file__).resolve().parent


def _fingerprint(*paths: Path) -> str:
    return hashlib.sha256(b"".join(p.read_bytes() for p in paths)).hexdigest()[:12]


_SCHEMAS = _APP / "openf1" / "schemas.py"
# Per kind, so changing the photo lookup doesn't throw away the slow-to-build circuit maps
_EXTRA_VERSIONS = {
    "circuit": _fingerprint(_APP / "extras.py", _APP / "models.py", _SCHEMAS),
    "weather": _fingerprint(_APP / "extras.py", _APP / "models.py", _SCHEMAS),
    "photos": _fingerprint(_APP / "photos.py", _APP / "models.py"),
}
_CALENDAR_VERSION = _fingerprint(_SCHEMAS)
_EXTRA_MODELS: dict[str, type[BaseModel]] = {
    "circuit": CircuitMap,
    "weather": RaceWeather,
    "photos": RacePhotos,
}
_sessions_adapter = TypeAdapter(list[Session])


def is_settled(session: Session) -> bool:
    end = session.date_end or session.date_start + timedelta(hours=3)
    return datetime.now(UTC) - end > SETTLE_DELAY


def has_lap_timing(result: SessionScore) -> bool:
    """False when a race has pit stops but not one could be timed, meaning OpenF1 sent no laps
    for it. That result is never kept as final, so the race is scored again once laps arrive."""
    stops = [stop for r in result.results for stop in r.stops]
    return not stops or any(stop.time_loss is not None for stop in stops)


def _season_over(year: int) -> bool:
    return year < datetime.now(UTC).year


def _load_extra(kind: str, session_key: int) -> BaseModel | None:
    text = redis_cache.load_text(f"fs:extra:{kind}:{_EXTRA_VERSIONS[kind]}:{session_key}")
    if text is None:
        return None
    try:
        return _EXTRA_MODELS[kind].model_validate_json(text)
    except ValueError:
        return None  # an unreadable entry is rebuilt and overwritten


def _save_extra(kind: str, session_key: int, value: object) -> None:
    # A race with no photos found is looked up again after a restart rather than kept empty
    if not isinstance(value, BaseModel) or (isinstance(value, RacePhotos) and not value.photos):
        return
    redis_cache.save_text(
        f"fs:extra:{kind}:{_EXTRA_VERSIONS[kind]}:{session_key}", value.model_dump_json()
    )


def _load_calendar_cache(year: int) -> tuple[list[Session], dict[int, str]] | None:
    text = redis_cache.load_text(f"fs:calendar:{_CALENDAR_VERSION}:{year}")
    if text is None:
        return None
    try:
        saved = json.loads(text)
        sessions = _sessions_adapter.validate_python(saved["sessions"])
        names = {int(k): str(v) for k, v in saved["meetings"].items()}
    except (ValueError, KeyError, TypeError):
        return None
    return sessions, names


def _save_calendar_cache(year: int, sessions: list[Session], names: dict[int, str]) -> None:
    payload = {
        "sessions": _sessions_adapter.dump_python(sessions, mode="json"),
        "meetings": {str(k): v for k, v in names.items()},
    }
    redis_cache.save_text(f"fs:calendar:{_CALENDAR_VERSION}:{year}", json.dumps(payload))


class ScoreStore:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http
        self._scores: dict[int, tuple[float, SessionScore]] = {}
        self._inflight: dict[int, asyncio.Task[SessionScore]] = {}
        self._failed_at: dict[int, float] = {}
        self._calendars: dict[int, tuple[float, list[Session]]] = {}
        self._calendar_locks: dict[int, asyncio.Lock] = {}
        self._calendar_refresh: dict[int, asyncio.Task[list[Session]]] = {}
        self._meeting_names: dict[int, str] = {}
        self._warmers: dict[int, asyncio.Task[None]] = {}
        self._cancelled: set[int] = set()
        self._background: set[asyncio.Task[Any]] = set()
        self._extras: dict[tuple[str, int], tuple[float, object]] = {}
        self._extras_inflight: dict[tuple[str, int], asyncio.Task[object]] = {}
        score_cache.prune()

    # ── calendar ────────────────────────────────────────────────────────────

    async def sessions(self, year: int) -> list[Session]:
        """Grand Prix race sessions that took place, in chronological order. Races that were
        cancelled stay on OpenF1's calendar with no data; once scoring finds them empty they
        are left out, so round numbers match the real season."""
        return [s for s in await self._calendar(year) if s.session_key not in self._cancelled]

    async def _calendar(self, year: int) -> list[Session]:
        cached = self._calendars.get(year)
        if cached is None:
            return await self._load_calendar(year)
        # A finished season's calendar never changes, so only the current one is refreshed
        stale = time.monotonic() - cached[0] >= SESSIONS_TTL and not _season_over(year)
        if stale and year not in self._calendar_refresh:
            task = asyncio.create_task(self._load_calendar(year))
            self._calendar_refresh[year] = task
            task.add_done_callback(lambda _: self._calendar_refresh.pop(year, None))
            self._track(task)
        return cached[1]

    async def _load_calendar(self, year: int) -> list[Session]:
        lock = self._calendar_locks.setdefault(year, asyncio.Lock())
        async with lock:
            cached = self._calendars.get(year)
            if cached and (_season_over(year) or time.monotonic() - cached[0] < SESSIONS_TTL):
                return cached[1]
            if _season_over(year) and (saved := _load_calendar_cache(year)):
                sessions, names = saved
                self._meeting_names.update(names)
                self._calendars[year] = (time.monotonic(), sessions)
                return sessions
            now = datetime.now(UTC)
            all_sessions, meetings = await asyncio.gather(
                openf1.get_sessions(self._http, year), openf1.get_meetings(self._http, year)
            )
            names = {m.meeting_key: m.meeting_name for m in meetings}
            self._meeting_names.update(names)
            sessions = sorted(
                (
                    s
                    for s in all_sessions
                    # session_type "Race" also covers sprints; only score Grands Prix
                    if s.session_name == "Race" and s.date_start <= now
                ),
                key=lambda s: s.date_start,
            )
            self._calendars[year] = (time.monotonic(), sessions)
            if _season_over(year) and sessions:
                _save_calendar_cache(year, sessions, names)
            return sessions

    def race_name(self, session: Session) -> str:
        return self._meeting_names.get(session.meeting_key, f"{session.country_name} Grand Prix")

    async def session(self, session_key: int) -> Session | None:
        for _, sessions in self._calendars.values():
            if match := next((s for s in sessions if s.session_key == session_key), None):
                return match
        found = await openf1.get_session(self._http, session_key)
        return found if found and found.year >= FIRST_SEASON else None

    # ── scores ──────────────────────────────────────────────────────────────

    def cached(self, session: Session) -> SessionScore | None:
        entry = self._scores.get(session.session_key)
        return entry[1] if entry else None

    def _is_fresh(self, session: Session) -> bool:
        entry = self._scores.get(session.session_key)
        if entry is None:
            return False
        age = time.monotonic() - entry[0]
        if not has_lap_timing(entry[1]):
            return age < INCOMPLETE_RETRY
        return is_settled(session) or age < RECENT_TTL

    def _recently_failed(self, session: Session) -> bool:
        failed_at = self._failed_at.get(session.session_key)
        return failed_at is not None and time.monotonic() - failed_at < FAILURE_COOLDOWN

    async def score(self, session: Session) -> SessionScore:
        key = session.session_key
        entry = self._scores.get(key)
        if entry and self._is_fresh(session):
            return entry[1]
        if (
            entry is None
            and is_settled(session)
            and (saved := score_cache.load(key))
            and has_lap_timing(saved)
        ):
            self._keep(session, saved)
            return saved
        task = self._inflight.get(key)
        if task is None:
            task = asyncio.create_task(self._compute(session))
            self._inflight[key] = task
            self._track(task)
        if entry:
            return entry[1]  # the older score now, the fresh one once the re-score finishes
        # Shield so a client disconnect doesn't cancel work other callers share
        return await asyncio.shield(task)

    def _keep(self, session: Session, result: SessionScore) -> None:
        self._scores[session.session_key] = (time.monotonic(), result)
        if not result.results and is_settled(session):
            self._cancelled.add(session.session_key)
        # Lets other sessions of the season borrow these drivers' photos, as live scoring does
        headshots.remember(result.drivers, session.year)

    async def _compute(self, session: Session) -> SessionScore:
        key = session.session_key
        try:
            result = await score_session(self._http, session, persist=is_settled(session))
            self._keep(session, result)
            if is_settled(session) and has_lap_timing(result):
                score_cache.save(result)
            elif is_settled(session):
                logger.warning("No lap timing for session %d yet, will retry", key)
            self._failed_at.pop(key, None)
            return result
        except Exception:
            self._failed_at[key] = time.monotonic()
            raise
        finally:
            self._inflight.pop(key, None)

    # ── background warming ──────────────────────────────────────────────────

    def ensure_warming(self, year: int, sessions: list[Session]) -> bool:
        """Start scoring any outstanding sessions in the background.
        Returns True while there is still work outstanding."""
        pending = [s for s in sessions if not self._is_fresh(s) and not self._recently_failed(s)]
        if not pending:
            return False
        warmer = self._warmers.get(year)
        if warmer is None or warmer.done():
            self._warmers[year] = asyncio.create_task(self._warm(year, pending))
        return True

    async def _warm(self, year: int, sessions: list[Session]) -> None:
        logger.info("Warming %d: %d sessions to score", year, len(sessions))
        for session in sessions:
            try:
                await self.score(session)
            except Exception:
                logger.exception("Failed to score session %d", session.session_key)
        logger.info("Warming %d complete", year)

    async def warm_year(self, year: int) -> None:
        try:
            all_sessions = await self.sessions(year)
            self.ensure_warming(year, all_sessions)
            self._track(asyncio.create_task(self._warm_extras(all_sessions)))
        except Exception:
            logger.exception("Could not start warming %d", year)

    async def _warm_extras(self, sessions: list[Session]) -> None:
        """Pre-load circuit map, weather and photos for every settled race."""
        for session in sessions:
            if not is_settled(session):
                continue
            for fetch in (self.circuit, self.weather, self.photos):
                try:
                    await fetch(session)
                except Exception:
                    logger.exception("Failed to warm extras for session %d", session.session_key)

    async def warm_all(self) -> None:
        """Warm scores and extras for every season the site covers."""
        current_year = datetime.now(UTC).year
        for year in range(FIRST_SEASON, current_year + 1):
            await self.warm_year(year)

    # ── race page extras (circuit map, weather) ─────────────────────────────

    async def circuit(self, session: Session) -> CircuitMap | None:
        result = await self._extra("circuit", session, extras.build_circuit)
        return result if isinstance(result, CircuitMap) else None

    async def weather(self, session: Session) -> RaceWeather | None:
        result = await self._extra("weather", session, extras.build_weather)
        return result if isinstance(result, RaceWeather) else None

    async def photos(self, session: Session) -> RacePhotos:
        await self.sessions(session.year)  # loads the official meeting names
        race_name = self.race_name(session)

        async def build(_http: httpx.AsyncClient, s: Session, *, persist: bool) -> RacePhotos:
            # Commons lookups take a few round trips, so finished races keep theirs on disk
            path = openf1.CACHE_DIR / f"commons-photos-{s.session_key}.json"
            if persist and path.exists():
                try:
                    return RacePhotos.model_validate_json(path.read_text("utf-8"))
                except ValueError:
                    pass  # corrupt or old format: look them up again
            found = await photos.find_photos(race_name, s)
            if persist and found.photos:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(found.model_dump_json(), "utf-8")
            return found

        result = await self._extra("photos", session, build)
        return (
            result
            if isinstance(result, RacePhotos)
            else RacePhotos(scope="none", category=None, photos=[])
        )

    def prefetch_extras(self, session: Session) -> None:
        """Start the race page's map, weather and photos now, so they are ready (or nearly)
        by the time the browser asks for them alongside the race itself."""
        for fetch in (self.circuit, self.weather, self.photos):
            self._track(asyncio.create_task(fetch(session)))

    def _track(self, task: asyncio.Task[Any]) -> None:
        """Keep a reference to background work and log its failure, which may have no awaiter."""
        self._background.add(task)
        task.add_done_callback(self._settle_background)

    def _settle_background(self, task: asyncio.Task[Any]) -> None:
        self._background.discard(task)
        if not task.cancelled() and (exc := task.exception()) is not None:
            logger.warning("Background task failed: %s", exc)

    async def _extra(
        self,
        kind: str,
        session: Session,
        build: Callable[..., Coroutine[Any, Any, object]],
    ) -> object:
        key = (kind, session.session_key)
        cached = self._extras.get(key)
        if cached and (is_settled(session) or time.monotonic() - cached[0] < RECENT_TTL):
            return cached[1]
        if cached is None and is_settled(session):
            saved = _load_extra(kind, session.session_key)
            if saved is not None:
                self._extras[key] = (time.monotonic(), saved)
                return saved
        task = self._extras_inflight.get(key)
        if task is None:
            task = asyncio.create_task(build(self._http, session, persist=is_settled(session)))
            self._extras_inflight[key] = task

            def done(t: asyncio.Task[object]) -> None:
                self._extras_inflight.pop(key, None)
                if not t.cancelled() and t.exception() is None:
                    self._extras[key] = (time.monotonic(), t.result())
                    if is_settled(session):
                        _save_extra(kind, session.session_key, t.result())

            task.add_done_callback(done)
            self._track(task)
        if cached:
            return cached[1]  # stale, refreshed in the background
        return await asyncio.shield(task)

    async def aclose(self) -> None:
        tasks: list[asyncio.Task[Any]] = [
            *self._warmers.values(),
            *self._inflight.values(),
            *self._extras_inflight.values(),
            *self._background,
        ]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
