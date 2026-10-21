from datetime import UTC, datetime

import pytest

from app.openf1.schemas import Session
from app.scoring.formula import RaceLuckResult
from app.scoring.pipeline import SessionScore
from app.service import min_races


def _result(driver: int, luck: float | None) -> RaceLuckResult:
    return RaceLuckResult(
        driver_number=driver,
        race_luck=luck,
        race_execution=None,
        no_stops=False,
        insufficient_baseline_data=luck is None,
        stops=[],
    )


def _score(*lucks: float | None) -> SessionScore:
    session = Session(
        session_key=1,
        meeting_key=1,
        session_name="Race",
        session_type="Race",
        date_start=datetime(2026, 3, 1, tzinfo=UTC),
        year=2026,
        country_name="Australia",
        location="Melbourne",
        circuit_short_name="Melbourne",
    )
    results = [_result(i, luck) for i, luck in enumerate(lucks, 1)]
    return SessionScore(session, [], results, 20.0, False, 20.0, lap_status={}, periods=[])


def test_luck_is_measured_against_the_field() -> None:
    score = _score(15.0, 15.0, 15.0, 3.0)  # three got the safety car stop, one didn't
    assert score.field_average == pytest.approx(12.0)
    assert score.relative_luck(1) == pytest.approx(3.0)
    assert score.relative_luck(4) == pytest.approx(-9.0)


def test_everyone_equally_lucky_means_nobody_is() -> None:
    score = _score(14.0, 14.0, 14.0)
    assert all(score.relative_luck(d) == pytest.approx(0.0) for d in (1, 2, 3))


def test_unscored_drivers_stay_unscored() -> None:
    score = _score(10.0, None)
    assert score.relative_luck(2) is None
    assert score.relative_luck(1) == pytest.approx(0.0)


@pytest.mark.parametrize(("rounds", "needed"), [(0, 1), (2, 2), (6, 3), (24, 8)])
def test_min_races_for_the_headline_cards(rounds: int, needed: int) -> None:
    assert min_races(rounds) == needed
