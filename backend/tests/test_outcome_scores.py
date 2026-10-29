from app.scoring.formula import RaceLuckResult
from app.scoring.pipeline import without_outcome_luck


def _result(driver: int) -> RaceLuckResult:
    return RaceLuckResult(
        driver_number=driver,
        race_luck=1.5,
        race_execution=0.4,
        no_stops=False,
        insufficient_baseline_data=False,
        stops=[],
    )


def test_a_retirement_keeps_its_crew_score_but_loses_its_luck() -> None:
    retired, finished = without_outcome_luck([_result(1), _result(2)], {1: "DNF"})
    assert retired.race_luck is None
    assert retired.race_execution == 0.4
    assert finished.race_luck == 1.5
    assert finished.race_execution == 0.4
