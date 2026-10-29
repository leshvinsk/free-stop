from datetime import UTC, datetime

import pytest
from redis.exceptions import NoPermissionError

from app import redis_cache, store
from app.models import RacePhoto, RacePhotos
from app.openf1.schemas import Session


class FakeRedis:
    def __init__(self, allow_getex: bool = True) -> None:
        self.data: dict[str, bytes] = {}
        self.ttls: dict[str, int] = {}
        self.allow_getex = allow_getex

    def getex(self, key: str, ex: int) -> bytes | None:
        if not self.allow_getex:
            raise NoPermissionError("NOPERM this user has no permissions to run 'getex'")
        if key in self.data:
            self.ttls[key] = ex
        return self.data.get(key)

    def get(self, key: str) -> bytes | None:
        return self.data.get(key)

    def setex(self, key: str, ttl: int, value: bytes) -> None:
        self.data[key] = value
        self.ttls[key] = ttl


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    client = FakeRedis()
    monkeypatch.setattr(redis_cache, "_get", lambda: client)
    monkeypatch.setattr(redis_cache, "_refresh_on_read", True)
    return client


def _session(year: int = 2025) -> Session:
    return Session(
        session_key=9947,
        meeting_key=1,
        session_name="Race",
        session_type="Race",
        date_start=datetime(year, 7, 6, 14, tzinfo=UTC),
        year=year,
        country_name="United Kingdom",
        location="Silverstone",
        circuit_short_name="Silverstone",
    )


def test_a_read_pushes_the_expiry_back(fake: FakeRedis) -> None:
    redis_cache.save_text("fs:test", "{}")
    fake.ttls["fs:test"] = 5
    assert redis_cache.load_text("fs:test") == "{}"
    assert fake.ttls["fs:test"] == redis_cache.TTL_DAYS * 86400


def test_without_getex_permission_reads_still_work(
    fake: FakeRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake.allow_getex = False
    redis_cache.save_text("fs:test", "{}")
    assert redis_cache.load_text("fs:test") == "{}"
    assert redis_cache.load_text("fs:test") == "{}"  # plain GET from then on


def test_race_photos_round_trip_as_json(fake: FakeRedis) -> None:
    store._save_extra("photos", 9947, RacePhotos(scope="none", category=None, photos=[]))
    assert fake.data == {}  # nothing found yet, so it is looked up again after a restart

    found = RacePhotos(
        scope="weekend",
        category="2025 British Grand Prix",
        photos=[
            RacePhoto(
                url="https://upload.wikimedia.org/a.jpg",
                page_url="https://commons.wikimedia.org/wiki/File:A.jpg",
                caption="Start",
                author="Someone",
                license="CC BY-SA 4.0",
                taken="2025-07-06",
            )
        ],
    )
    store._save_extra("photos", 9947, found)
    (key,) = fake.data
    assert key.startswith("fs:extra:photos:")
    assert store._load_extra("photos", 9947) == found


def test_a_finished_calendar_round_trips(fake: FakeRedis) -> None:
    session = _session()
    store._save_calendar_cache(2025, [session], {1: "British Grand Prix"})
    saved = store._load_calendar_cache(2025)
    assert saved is not None
    sessions, names = saved
    assert sessions == [session]
    assert names == {1: "British Grand Prix"}


def test_an_unreadable_entry_is_ignored(fake: FakeRedis) -> None:
    redis_cache.save_text(f"fs:extra:weather:{store._EXTRA_VERSIONS['weather']}:9947", "not json")
    assert store._load_extra("weather", 9947) is None
