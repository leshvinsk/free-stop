import asyncio
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from app import score_cache
from app.openf1.schemas import Session
from app.scoring.pipeline import SessionScore
from app.store import SESSIONS_TTL, ScoreStore


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
    async def run() -> None:
        async with httpx.AsyncClient() as http:
            store = ScoreStore(http)
            old = [_session()]
            store._calendars[2025] = (time.monotonic() - SESSIONS_TTL - 1, old)
            refreshed = asyncio.Event()

            async def slow_load(year: int) -> list[Session]:
                await refreshed.wait()
                return old

            store._load_calendar = slow_load  # type: ignore[method-assign]
            # Returns at once with the cached calendar rather than waiting on the refresh
            assert await asyncio.wait_for(store.sessions(2025), timeout=1) == old
            assert 2025 in store._calendar_refresh
            refreshed.set()
            await asyncio.sleep(0)

    asyncio.run(run())
