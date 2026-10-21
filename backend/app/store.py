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
import logging
import time
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app import extras, headshots, photos, score_cache
from app.models import CircuitMap, RacePhotos, RaceWeather
from app.openf1 import client as openf1
from app.openf1.schemas import Session
from app.scoring.pipeline import SessionScore, score_session
from app.teams import FIRST_SEASON

logger = logging.getLogger(__name__)

RECENT_TTL = 300  # seconds before an unsettled session is re-scored
SESSIONS_TTL = 900  # seconds the season calendar is cached
FAILURE_COOLDOWN = 300  # seconds before a failed session is retried
SETTLE_DELAY = timedelta(hours=3)  # OpenF1 data is final this long after a race ends


def is_settled(session: Session) -> bool:
    end = session.date_end or session.date_start + timedelta(hours=3)
    return datetime.now(UTC) - end > SETTLE_DELAY


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
        if time.monotonic() - cached[0] >= SESSIONS_TTL and year not in self._calendar_refresh:
            task = asyncio.create_task(self._load_calendar(year))
            self._calendar_refresh[year] = task
            task.add_done_callback(lambda _: self._calendar_refresh.pop(year, None))
            self._track(task)
        return cached[1]

    async def _load_calendar(self, year: int) -> list[Session]:
        lock = self._calendar_locks.setdefault(year, asyncio.Lock())
        async with lock:
            cached = self._calendars.get(year)
            if cached and time.monotonic() - cached[0] < SESSIONS_TTL:
                return cached[1]
            now = datetime.now(UTC)
            all_sessions, meetings = await asyncio.gather(
                openf1.get_sessions(self._http, year), openf1.get_meetings(self._http, year)
            )
            self._meeting_names.update({m.meeting_key: m.meeting_name for m in meetings})
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
        return is_settled(session) or time.monotonic() - entry[0] < RECENT_TTL

    def _recently_failed(self, session: Session) -> bool:
        failed_at = self._failed_at.get(session.session_key)
        return failed_at is not None and time.monotonic() - failed_at < FAILURE_COOLDOWN

    async def score(self, session: Session) -> SessionScore:
        key = session.session_key
        entry = self._scores.get(key)
        if entry and self._is_fresh(session):
            return entry[1]
        if entry is None and is_settled(session) and (saved := score_cache.load(key)):
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
            if is_settled(session):
                score_cache.save(result)
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
            self.ensure_warming(year, await self.sessions(year))
        except Exception:
            logger.exception("Could not start warming %d", year)

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
        task = self._extras_inflight.get(key)
        if task is None:
            task = asyncio.create_task(build(self._http, session, persist=is_settled(session)))
            self._extras_inflight[key] = task

            def done(t: asyncio.Task[object]) -> None:
                self._extras_inflight.pop(key, None)
                if not t.cancelled() and t.exception() is None:
                    self._extras[key] = (time.monotonic(), t.result())

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
