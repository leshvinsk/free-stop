"""
Scoring tests on synthetic races: 8 cars lapping in 90s, 2s apart, so every number is known.
A green-flag stop costs 22s (in-lap +10s, out-lap +12s) through a 20s pit lane.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.openf1.schemas import Lap, PitStop, RaceControlMessage
from app.scoring.formula import OWN_PACE_WEIGHT, RaceAnalysis, analyse_race, compute_baseline
from app.scoring.neutralised import FlagStatus, build_timeline, classify_laps

T0 = datetime(2026, 3, 1, 14, 0, tzinfo=UTC)
DRIVERS = list(range(1, 9))
LAPS = 20
LAP = 90.0
LANE = 20.0
GREEN_IN, GREEN_OUT = 10.0, 12.0  # a normal stop: 22s lost


def _durations(**overrides: dict[int, float]) -> dict[int, list[float]]:
    """Every driver laps in LAP seconds; overrides are {"d<n>": {lap: duration}}."""
    table = {d: [LAP] * LAPS for d in DRIVERS}
    for key, laps in overrides.items():
        for lap, duration in laps.items():
            table[int(key[1:])][lap - 1] = duration
    return table


def _laps(table: dict[int, list[float]]) -> list[Lap]:
    laps = []
    for i, (driver, durations) in enumerate(table.items()):
        t = T0 + timedelta(seconds=2 * i)
        for n, duration in enumerate(durations, 1):
            laps.append(
                Lap(driver_number=driver, lap_number=n, date_start=t, lap_duration=duration)
            )
            t += timedelta(seconds=duration)
    return laps


def _stop(laps: list[Lap], driver: int, in_lap: int, lane: float = LANE, **kw: object) -> PitStop:
    """A stop whose pit lane straddles the timing line at the end of `in_lap`."""
    lap = next(lp for lp in laps if lp.driver_number == driver and lp.lap_number == in_lap)
    assert lap.date_end is not None
    exit_ = lap.date_end + timedelta(seconds=lane / 2)
    fields: dict[str, object] = {"lap_number": in_lap} | kw
    return PitStop(session_key=1, driver_number=driver, pit_duration=lane, date=exit_, **fields)  # type: ignore[arg-type]


def _msg(
    date: datetime, lap: int, category: str, message: str, flag: str | None = None
) -> RaceControlMessage:
    return RaceControlMessage(
        session_key=1, date=date, lap_number=lap, category=category, message=message, flag=flag
    )


def _analyse(
    laps: list[Lap], stops: list[PitStop], messages: list[RaceControlMessage] | None = None
) -> RaceAnalysis:
    messages = messages or []
    starts: dict[int, datetime] = {}
    for lap in laps:
        if lap.date_start and (
            lap.lap_number not in starts or lap.date_start < starts[lap.lap_number]
        ):
            starts[lap.lap_number] = lap.date_start
    return analyse_race(
        DRIVERS,
        stops,
        laps,
        messages,
        build_timeline(messages, starts),
        classify_laps(messages, LAPS),
    )


def _stops_of(analysis: RaceAnalysis, driver: int):  # type: ignore[no-untyped-def]
    return next(r for r in analysis.results if r.driver_number == driver).stops


def _green_race() -> tuple[list[Lap], list[PitStop]]:
    """Drivers 1-4 make an ordinary green-flag stop on laps 5-8."""
    table = _durations(
        **{f"d{d}": {4 + d: LAP + GREEN_IN, 5 + d: LAP + GREEN_OUT} for d in range(1, 5)}
    )
    laps = _laps(table)
    return laps, [_stop(laps, d, 4 + d) for d in range(1, 5)]


class TestGreenFlagStops:
    def test_baseline_is_the_time_lost_to_the_field(self) -> None:
        laps, stops = _green_race()
        analysis = _analyse(laps, stops)
        assert analysis.baseline == pytest.approx(22.0)
        assert analysis.typical_lane == pytest.approx(LANE)
        assert not analysis.baseline_estimated

    def test_ordinary_stops_are_neither_lucky_nor_unlucky(self) -> None:
        laps, stops = _green_race()
        for result in _analyse(laps, stops).results:
            assert result.race_luck == pytest.approx(0.0)
            for stop in result.stops:
                assert stop.status == FlagStatus.GREEN
                assert stop.time_loss == pytest.approx(22.0)
                assert stop.execution == pytest.approx(0.0)

    def test_drivers_without_stops_score_zero(self) -> None:
        laps, stops = _green_race()
        result = next(r for r in _analyse(laps, stops).results if r.driver_number == 8)
        assert result.no_stops and result.race_luck == 0.0

    def test_slow_crew_counts_as_execution_not_luck(self) -> None:
        table = _durations(
            **{f"d{d}": {4 + d: LAP + GREEN_IN, 5 + d: LAP + GREEN_OUT} for d in range(1, 4)},
            d4={8: LAP + GREEN_IN + 3, 9: LAP + GREEN_OUT},  # 3s stuck wheel nut
        )
        laps = _laps(table)
        stops = [_stop(laps, d, 4 + d) for d in range(1, 4)] + [_stop(laps, 4, 8, lane=LANE + 3)]
        slow = _stops_of(_analyse(laps, stops), 4)[0]
        assert slow.execution == pytest.approx(-3.0)
        assert slow.luck == pytest.approx(0.0, abs=0.01)

    def test_lap_number_reported_as_the_out_lap_is_corrected(self) -> None:
        # At some circuits OpenF1 tags the stop with the out-lap
        laps, stops = _green_race()
        stops[0] = _stop(laps, 1, 5, lap_number=6)
        stop = _stops_of(_analyse(laps, stops), 1)[0]
        assert stop.lap_number == 5
        assert stop.luck == pytest.approx(0.0)


class TestPenalties:
    def _race(self, message: str, minutes_after_stop: float = 3) -> RaceAnalysis:
        table = _durations(
            **{f"d{d}": {4 + d: LAP + GREEN_IN, 5 + d: LAP + GREEN_OUT} for d in range(1, 4)},
            d4={8: LAP + GREEN_IN + 10, 9: LAP + GREEN_OUT},
        )
        laps = _laps(table)
        stops = [_stop(laps, d, 4 + d) for d in range(1, 4)] + [_stop(laps, 4, 8, lane=LANE + 10)]
        sent = (stops[-1].date or T0) + timedelta(minutes=minutes_after_stop)
        return _analyse(laps, stops, [_msg(sent, 11, "Other", message)])

    def test_served_time_penalty_is_neither_bad_luck_nor_bad_execution(self) -> None:
        analysis = self._race(
            "FIA STEWARDS: PENALTY SERVED - 10 SECOND TIME PENALTY FOR CAR 4 (XXX) - UNSAFE RELEASE"
        )
        stop = _stops_of(analysis, 4)[0]
        assert stop.penalty == 10.0
        assert stop.execution == pytest.approx(0.0)
        assert stop.luck == pytest.approx(0.0, abs=0.01)

    def test_unreported_penalty_is_inferred_from_the_long_stop(self) -> None:
        # Stewards hand the penalty out before the stop but never post a "served" message
        message = "FIA STEWARDS: 10 SECOND TIME PENALTY FOR CAR 4 (XXX) - CAUSING A COLLISION"
        stop = _stops_of(self._race(message, minutes_after_stop=-5), 4)[0]
        assert stop.penalty == 10.0
        assert stop.execution == pytest.approx(0.0)

    def test_penalty_handed_out_after_the_stop_is_not_inferred(self) -> None:
        message = "FIA STEWARDS: 10 SECOND TIME PENALTY FOR CAR 4 (XXX) - CAUSING A COLLISION"
        assert _stops_of(self._race(message), 4)[0].penalty == 0.0

    def test_drive_through_is_not_scored(self) -> None:
        laps, stops = _green_race()
        drive_through = _stop(laps, 6, 12, lane=15.0)
        served_at = (drive_through.date or T0) + timedelta(seconds=30)
        message = "FIA STEWARDS: PENALTY SERVED - DRIVE THROUGH PENALTY FOR CAR 6 (XXX) - SPEEDING"
        stop = _stops_of(
            _analyse(laps, [*stops, drive_through], [_msg(served_at, 13, "Other", message)]), 6
        )[0]
        assert stop.luck is None and stop.note == "Drive-through penalty"


def _sc_race() -> tuple[list[Lap], list[PitStop], list[RaceControlMessage]]:
    """Safety car laps 12-14 (everyone laps in 130s). Driver 5 pits under it and loses only
    8s; driver 6 pitted under green on lap 10, two laps before it came out."""
    sc = {12: 130.0, 13: 130.0, 14: 130.0}
    table = _durations(
        **{f"d{d}": {4 + d: LAP + GREEN_IN, 5 + d: LAP + GREEN_OUT} for d in range(1, 5)},
        d5=sc | {12: 133.0, 13: 135.0},
        d6={10: LAP + GREEN_IN, 11: LAP + GREEN_OUT} | sc,
        d7=sc,
        d8=sc,
    )
    for d in range(1, 5):
        table[d][11:14] = [130.0] * 3
    laps = _laps(table)
    leader_lap = {lp.lap_number: lp for lp in laps if lp.driver_number == 1}
    sc_out = leader_lap[12].date_start
    assert sc_out is not None
    messages = [
        _msg(sc_out, 12, "SafetyCar", "SAFETY CAR DEPLOYED"),
        _msg(sc_out + timedelta(seconds=300), 14, "SafetyCar", "SAFETY CAR IN THIS LAP"),
    ]
    stops = [_stop(laps, d, 4 + d) for d in range(1, 5)]
    stops += [_stop(laps, 5, 12), _stop(laps, 6, 10)]
    return laps, stops, messages


class TestSafetyCar:
    def test_stop_under_safety_car_is_lucky(self) -> None:
        analysis = _analyse(*_sc_race())
        stop = _stops_of(analysis, 5)[0]
        assert stop.status == FlagStatus.SC
        assert stop.time_loss == pytest.approx(8.0)
        assert stop.luck == pytest.approx(14.0)

    def test_pitting_just_before_the_safety_car_is_a_missed_opportunity(self) -> None:
        analysis = _analyse(*_sc_race())
        stop = _stops_of(analysis, 6)[0]
        assert stop.luck == pytest.approx(0.0)
        assert stop.missed == pytest.approx(-14.0)
        assert stop.missed_status == FlagStatus.SC and stop.missed_lap == 12
        result = next(r for r in analysis.results if r.driver_number == 6)
        assert result.race_luck == pytest.approx(-14.0)

    def test_stops_long_before_the_safety_car_are_not_penalised(self) -> None:
        analysis = _analyse(*_sc_race())
        assert all(s.missed == 0 for d in (1, 2, 3, 4) for s in _stops_of(analysis, d))

    def test_luck_is_capped_at_a_free_stop(self) -> None:
        laps, stops, messages = _sc_race()
        # Driver 5 somehow gains time over the in/out laps
        for lap in laps:
            if lap.driver_number == 5 and lap.lap_number in (12, 13):
                lap.lap_duration = 125.0
        stop = _stops_of(_analyse(laps, stops, messages), 5)[0]
        assert stop.luck == pytest.approx(22.0)

    def test_pit_lane_pass_through_is_not_a_stop(self) -> None:
        laps, stops, messages = _sc_race()
        stops.append(_stop(laps, 7, 13, lane=15.0))
        stop = _stops_of(_analyse(laps, stops, messages), 7)[0]
        assert stop.luck is None and stop.execution is None
        assert stop.note == "Drove through the pit lane behind the safety car"


class TestRedFlag:
    def test_red_flag_tyre_change_is_neutral_and_earlier_stop_is_wasted(self) -> None:
        laps, stops = _green_race()
        leader = {lp.lap_number: lp for lp in laps if lp.driver_number == 1}
        red_at = leader[10].date_start
        assert red_at is not None
        messages = [
            _msg(red_at, 10, "Other", "RED FLAG - RACE SUSPENDED"),
            _msg(red_at + timedelta(minutes=30), 10, "SessionStatus", "SESSION STARTED"),
        ]
        # Driver 4 stopped on lap 8; drivers 7 and 8 sat in the pit lane during the red flag
        waits = [
            PitStop(
                session_key=1,
                driver_number=d,
                lap_number=10,
                pit_duration=1800.0,
                date=red_at + timedelta(minutes=30, seconds=10),
            )
            for d in (7, 8)
        ]
        analysis = _analyse(laps, stops + waits, messages)

        free = _stops_of(analysis, 7)[0]
        assert free.status == FlagStatus.RED and free.luck == 0.0
        wasted = _stops_of(analysis, 4)[0]
        assert wasted.missed == pytest.approx(-22.0)
        assert wasted.missed_status == FlagStatus.RED


class TestComputeBaseline:
    def test_trims_and_drops_outliers(self) -> None:
        assert compute_baseline([22.0, 22.5, 23.0, 23.5, 80.0]) == pytest.approx(22.75)

    def test_needs_three_stops(self) -> None:
        assert compute_baseline([22.0, 23.0]) is None


class TestOwnPace:
    def test_a_slow_car_is_not_charged_for_being_slow(self) -> None:
        # Driver 4 laps a second slower than everyone else all race, then makes a normal stop
        slow = {lap: LAP + 1 for lap in range(1, LAPS + 1)}
        table = _durations(
            **{f"d{d}": {4 + d: LAP + GREEN_IN, 5 + d: LAP + GREEN_OUT} for d in range(1, 4)},
            d4=slow | {8: LAP + 1 + GREEN_IN, 9: LAP + 1 + GREEN_OUT},
        )
        laps = _laps(table)
        stops = [_stop(laps, d, 4 + d) for d in range(1, 5)]
        analysis = _analyse(laps, stops)
        result = next(r for r in analysis.results if r.driver_number == 4)
        assert result.own_pace == pytest.approx(1.0)
        # Its pit laps are 2s slower than the field's only because the car is; that much
        # counts as pace rather than stop cost, scaled to how much of it shows on pit laps
        assert result.stops[0].time_loss == pytest.approx(
            GREEN_IN + GREEN_OUT + 2 - 2 * OWN_PACE_WEIGHT
        )

    def test_the_pace_correction_skips_laps_behind_the_safety_car(self) -> None:
        # Behind the safety car every car laps at the same speed, slow car or not
        laps, stops, messages = _sc_race()
        for lap in laps:
            if lap.driver_number == 5 and lap.lap_number not in (12, 13, 14):
                lap.lap_duration = LAP + 1
        analysis = _analyse(_laps(_table_of(laps)), stops, messages)
        result = next(r for r in analysis.results if r.driver_number == 5)
        assert result.own_pace == pytest.approx(1.0)
        # Only the few seconds of the in-lap before the safety car came out are corrected;
        # correcting both laps in full would take 2 x OWN_PACE_WEIGHT seconds off
        assert result.stops[0].time_loss == pytest.approx(8.0, abs=0.05)

    def test_equal_cars_have_no_pace_gap(self) -> None:
        laps, stops = _green_race()
        assert all(r.own_pace == pytest.approx(0.0) for r in _analyse(laps, stops).results)


def _table_of(laps: list[Lap]) -> dict[int, list[float]]:
    """Lap durations back into a table, so start times are rebuilt from them."""
    table: dict[int, list[float]] = {}
    for lap in sorted(laps, key=lambda lp: (lp.driver_number, lp.lap_number)):
        assert lap.lap_duration is not None
        table.setdefault(lap.driver_number, []).append(lap.lap_duration)
    return table
