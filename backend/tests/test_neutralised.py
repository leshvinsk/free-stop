import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.openf1.schemas import RaceControlMessage
from app.scoring.neutralised import FlagStatus, build_timeline, classify_laps

FIXTURE = Path(__file__).parent / "fixtures" / "race_control_sample.json"


@pytest.fixture()
def messages() -> list[RaceControlMessage]:
    raw = json.loads(FIXTURE.read_text())
    return [RaceControlMessage(**item) for item in raw]


def test_green_before_sc(messages: list[RaceControlMessage]) -> None:
    result = classify_laps(messages, total_laps=50)
    # Laps 1–14 should be GREEN
    for lap in range(1, 15):
        assert result[lap] == FlagStatus.GREEN, f"lap {lap} should be GREEN"


def test_sc_period(messages: list[RaceControlMessage]) -> None:
    result = classify_laps(messages, total_laps=50)
    # Laps 15–19 should be SC
    for lap in range(15, 20):
        assert result[lap] == FlagStatus.SC, f"lap {lap} should be SC"


def test_green_after_sc(messages: list[RaceControlMessage]) -> None:
    result = classify_laps(messages, total_laps=50)
    # Lap 20 onwards should be GREEN (until VSC)
    for lap in range(20, 35):
        assert result[lap] == FlagStatus.GREEN, f"lap {lap} should be GREEN"


def test_vsc_period(messages: list[RaceControlMessage]) -> None:
    result = classify_laps(messages, total_laps=50)
    # Laps 35–37 should be VSC
    for lap in range(35, 38):
        assert result[lap] == FlagStatus.VSC, f"lap {lap} should be VSC"


def test_green_after_vsc(messages: list[RaceControlMessage]) -> None:
    result = classify_laps(messages, total_laps=50)
    # Lap 38 onwards should be GREEN
    for lap in range(38, 51):
        assert result[lap] == FlagStatus.GREEN, f"lap {lap} should be GREEN"


def test_covers_all_laps(messages: list[RaceControlMessage]) -> None:
    result = classify_laps(messages, total_laps=50)
    assert set(result.keys()) == set(range(1, 51))


def _msg(lap: int, category: str, message: str, flag: str | None = None) -> RaceControlMessage:
    return RaceControlMessage(
        session_key=1, lap_number=lap, category=category, flag=flag, message=message
    )


# Message shapes as OpenF1 actually sends them: no green flag after a safety car,
# VSC under the SafetyCar category, and TRACK CLEAR arriving mid-SC.
REAL_WORLD = [
    _msg(1, "Flag", "GREEN LIGHT - PIT EXIT OPEN", "GREEN"),
    _msg(12, "SafetyCar", "SAFETY CAR DEPLOYED"),
    _msg(13, "Flag", "TRACK CLEAR", "CLEAR"),
    _msg(15, "SafetyCar", "SAFETY CAR IN THIS LAP"),
    _msg(30, "SafetyCar", "VSC DEPLOYED"),
    _msg(31, "SafetyCar", "VSC ENDING"),
    _msg(40, "Flag", "RED FLAG", "RED"),
    _msg(42, "Flag", "GREEN LIGHT - PIT EXIT OPEN", "GREEN"),
]


def test_real_world_message_shapes() -> None:
    result = classify_laps(REAL_WORLD, total_laps=50)
    expected = (
        {lap: FlagStatus.GREEN for lap in range(1, 12)}
        | {lap: FlagStatus.SC for lap in range(12, 16)}
        | {lap: FlagStatus.GREEN for lap in range(16, 30)}
        | {lap: FlagStatus.VSC for lap in range(30, 32)}
        | {lap: FlagStatus.GREEN for lap in range(32, 40)}
        | {lap: FlagStatus.RED for lap in range(40, 42)}
        | {lap: FlagStatus.GREEN for lap in range(42, 51)}
    )
    assert result == expected


def test_red_flag_from_other_category_and_restart_on_same_lap() -> None:
    # Monaco 2026: red flag sent as "Other", resumed via SessionStatus on the same lap number
    messages = [
        _msg(60, "SafetyCar", "SAFETY CAR DEPLOYED"),
        _msg(65, "SafetyCar", "SAFETY CAR IN THIS LAP"),
        _msg(68, "Other", "RED FLAG - RACE SUSPENDED"),
        _msg(68, "SessionStatus", "SESSION STARTED"),
    ]
    result = classify_laps(messages, total_laps=70)
    assert result[67] == FlagStatus.GREEN
    assert result[68] == FlagStatus.RED  # the lap it happened on still shows it
    assert result[69] == FlagStatus.GREEN


T = datetime(2026, 5, 1, 14, 0, tzinfo=UTC)


def _timed(minute: float, lap: int, category: str, message: str, flag: str | None = None):  # type: ignore[no-untyped-def]
    return RaceControlMessage(
        session_key=1,
        lap_number=lap,
        date=T + timedelta(minutes=minute),
        category=category,
        message=message,
        flag=flag,
    )


class TestTimeline:
    def test_safety_car_ends_when_the_leader_starts_the_next_lap(self) -> None:
        messages = [
            _timed(10, 8, "SafetyCar", "SAFETY CAR DEPLOYED"),
            _timed(15, 10, "SafetyCar", "SAFETY CAR IN THIS LAP"),
        ]
        timeline = build_timeline(messages, {11: T + timedelta(minutes=16.5)})
        assert timeline.status_at(T + timedelta(minutes=9)) == FlagStatus.GREEN
        assert timeline.status_at(T + timedelta(minutes=16)) == FlagStatus.SC
        assert timeline.status_at(T + timedelta(minutes=17)) == FlagStatus.GREEN
        assert len(timeline.periods) == 1

    def test_vsc_ends_on_the_ending_message(self) -> None:
        messages = [
            _timed(10, 8, "SafetyCar", "VIRTUAL SAFETY CAR DEPLOYED"),
            _timed(12, 9, "SafetyCar", "VIRTUAL SAFETY CAR ENDING"),
        ]
        timeline = build_timeline(messages, {})
        assert timeline.status_at(T + timedelta(minutes=11)) == FlagStatus.VSC
        assert timeline.status_at(T + timedelta(minutes=12, seconds=1)) == FlagStatus.GREEN

    def test_pit_exit_open_only_ends_a_red_flag(self) -> None:
        messages = [
            _timed(0, 1, "Flag", "GREEN LIGHT - PIT EXIT OPEN", "GREEN"),
            _timed(10, 8, "SafetyCar", "SAFETY CAR DEPLOYED"),
            _timed(11, 8, "Other", "RED FLAG - RACE SUSPENDED"),
            _timed(40, 8, "Flag", "GREEN LIGHT - PIT EXIT OPEN", "GREEN"),
        ]
        timeline = build_timeline(messages, {})
        assert timeline.status_at(T + timedelta(minutes=10, seconds=30)) == FlagStatus.SC
        assert timeline.status_at(T + timedelta(minutes=20)) == FlagStatus.RED
        assert timeline.status_at(T + timedelta(minutes=41)) == FlagStatus.GREEN

    def test_worst_between_sees_a_short_neutralisation(self) -> None:
        messages = [
            _timed(10, 8, "SafetyCar", "VSC DEPLOYED"),
            _timed(10.5, 8, "SafetyCar", "VSC ENDING"),
        ]
        timeline = build_timeline(messages, {})
        assert (
            timeline.worst_between(T + timedelta(minutes=9), T + timedelta(minutes=11))
            == FlagStatus.VSC
        )
