import asyncio
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from app import score_cache
from app.openf1.schemas import Session
from app.scoring.formula import RaceLuckResult, ScoredStop
from app.scoring.neutralised import FlagStatus
from app.scoring.pipeline import SessionScore
from app.store import SESSIONS_TTL, ScoreStore, has_lap_timing


def _session(key: int = 1, days_ago: int = 30) -> Session:
    start = datetime.now(UTC) - timedelta(days=days_ago)
    return Session(
        session_key=key,
        meeting_key=1,
        session_name="Race",
        session_type="Race",
        date_start=start,
        date_end=start + timedelta(hours=2),
        year=2025,
        country_name="Italy",
        location="Monza",
        circuit_short_name="Monza",
    )


def _score(session: Session) -> SessionScore:
    return SessionScore(session, [], [], 20.0, False, 2.4, lap_status={}, periods=[])


@pytest.fixture(autouse=True)
def _scores_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(score_cache, "DIR", tmp_path / "scores")


def test_saved_scores_load_back() -> None:
    session = _session()
    score_cache.save(_score(session))
    loaded = score_cache.load(session.session_key)
    assert loaded is not None and loaded.baseline == 20.0


def test_scores_from_older_code_are_discarded() -> None:
    session = _session()
    score_cache.save(_score(session))
    stale = score_cache.DIR / f"oldversion-{session.session_key}.pkl"
    stale.write_bytes(b"old")
    score_cache.prune()
    assert not stale.exists()
    assert score_cache.load(session.session_key) is not None


def test_a_restart_uses_the_saved_score_without_rescoring() -> None:
    session = _session()
    score_cache.save(_score(session))

    async def run() -> SessionScore:
        def no_network(request: httpx.Request) -> httpx.Response:
            raise AssertionError(f"unexpected request to {request.url}")

        async with httpx.AsyncClient(transport=httpx.MockTransport(no_network)) as http:
            return await ScoreStore(http).score(session)

    assert asyncio.run(run()).baseline == 20.0


def test_a_stale_calendar_is_served_while_it_refreshes() -> None:
    year = datetime.now(UTC).year  # only the current season's calendar changes

    async def run() -> None:
        async with httpx.AsyncClient() as http:
            store = ScoreStore(http)
            old = [_session()]
            store._calendars[year] = (time.monotonic() - SESSIONS_TTL - 1, old)
            refreshed = asyncio.Event()

            async def slow_load(year: int) -> list[Session]:
                await refreshed.wait()
                return old

            store._load_calendar = slow_load  # type: ignore[method-assign]
            # Returns at once with the cached calendar rather than waiting on the refresh
            assert await asyncio.wait_for(store.sessions(year), timeout=1) == old
            assert year in store._calendar_refresh
            refreshed.set()
            await asyncio.sleep(0)

    asyncio.run(run())


def test_a_finished_seasons_calendar_is_never_refreshed() -> None:
    year = datetime.now(UTC).year - 1

    async def run() -> None:
        async with httpx.AsyncClient() as http:
            store = ScoreStore(http)
            old = [_session()]
            store._calendars[year] = (time.monotonic() - SESSIONS_TTL - 1, old)
            assert await store.sessions(year) == old
            assert year not in store._calendar_refresh

    asyncio.run(run())


def _stop(time_loss: float | None) -> ScoredStop:
    return ScoredStop(
        lap_number=20,
        pit_duration=22.0,
        status=FlagStatus.GREEN,
        time_loss=time_loss,
        luck=None,
        execution=None,
        penalty=0.0,
    )


def _score_with_stops(session: Session, time_loss: float | None) -> SessionScore:
    result = RaceLuckResult(
        driver_number=44,
        race_luck=None,
        race_execution=None,
        no_stops=False,
        insufficient_baseline_data=True,
        stops=[_stop(time_loss)],
    )
    return SessionScore(session, [], [result], None, False, 2.4, lap_status={}, periods=[])


def test_a_race_without_lap_timing_is_not_final() -> None:
    session = _session()
    assert has_lap_timing(_score(session))  # no stops at all is a real result
    assert has_lap_timing(_score_with_stops(session, 21.0))
    assert not has_lap_timing(_score_with_stops(session, None))


def test_a_saved_score_without_lap_timing_is_scored_again() -> None:
    session = _session()
    score_cache.save(_score_with_stops(session, None))
    requested: list[str] = []

    async def run() -> None:
        def record(request: httpx.Request) -> httpx.Response:
            requested.append(request.url.path)
            return httpx.Response(200, json=[])

        async with httpx.AsyncClient(transport=httpx.MockTransport(record)) as http:
            await ScoreStore(http).score(session)

    asyncio.run(run())
    assert any(path.endswith("/laps") for path in requested)
