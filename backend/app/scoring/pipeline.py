"""
Orchestrates data fetching and score computation for a single race session.
"""

import asyncio
import dataclasses
import logging
from datetime import datetime

import httpx

from app import headshots
from app.openf1 import client as openf1
from app.openf1.schemas import Driver, Lap, Session
from app.scoring.formula import RaceLuckResult, analyse_race
from app.scoring.neutralised import FlagStatus, Period, build_timeline, classify_laps

logger = logging.getLogger(__name__)


class SessionScore:
    def __init__(
        self,
        session: Session,
        drivers: list[Driver],
        results: list[RaceLuckResult],
        baseline: float | None,
        baseline_estimated: bool,
        typical_lane: float | None,
        lap_status: dict[int, FlagStatus],
        periods: list[Period],
        outcomes: dict[int, str] | None = None,
    ) -> None:
        self.session = session
        self.drivers = drivers
        self.results = results
        self.baseline = baseline
        self.baseline_estimated = baseline_estimated
        self.typical_lane = typical_lane
        self.lap_status = lap_status
        self.periods = periods
        # DNF / DNS / DSQ by driver number; those drivers are not scored for this race
        self.outcomes = outcomes or {}
        self._driver_map: dict[int, Driver] = {d.driver_number: d for d in drivers}

    def driver(self, number: int) -> Driver | None:
        return self._driver_map.get(number)

    def outcome(self, number: int) -> str | None:
        return self.outcomes.get(number)

    @property
    def field_average(self) -> float | None:
        """Mean race luck across the drivers scored in this race."""
        lucks = [r.race_luck for r in self.results if r.race_luck is not None]
        return sum(lucks) / len(lucks) if lucks else None

    def relative_luck(self, number: int) -> float | None:
        """Race luck against the rest of this race's field. Luck is about rivals: if everyone
        pitted under the same safety car, nobody gained on anybody."""
        result = next((r for r in self.results if r.driver_number == number), None)
        average = self.field_average
        if result is None or result.race_luck is None or average is None:
            return None
        return result.race_luck - average


async def score_session(
    http: httpx.AsyncClient,
    session: Session,
    *,
    persist: bool = False,
) -> SessionScore:
    logger.info("Scoring session %d (%s)", session.session_key, session.location)

    pit_stops, rc_messages, drivers, laps, classification = await asyncio.gather(
        openf1.get_pit_stops(http, session.session_key, persist=persist),
        openf1.get_race_control(http, session.session_key, persist=persist),
        openf1.get_drivers(http, session.session_key, persist=persist),
        openf1.get_laps(http, session.session_key, persist=persist),
        openf1.get_session_result(http, session.session_key, persist=persist),
    )
    outcomes = {r.driver_number: o for r in classification if (o := r.outcome)}

    await headshots.resolve(http, drivers, session.year)

    lap_numbers = (
        [lap.lap_number for lap in laps]
        + [m.lap_number for m in rc_messages if m.lap_number]
        + [p.lap_number for p in pit_stops]
    )
    if not lap_numbers:
        logger.warning("No race data for session %d — skipping", session.session_key)
        return SessionScore(session, drivers, [], None, False, None, lap_status={}, periods=[])

    lap_status = classify_laps(rc_messages, max(lap_numbers))
    timeline = build_timeline(rc_messages, _leader_lap_starts(laps))
    analysis = analyse_race(
        [d.driver_number for d in drivers], pit_stops, laps, rc_messages, timeline, lap_status
    )
    # A retirement or disqualification ends the race early, so its pit stops can't be judged
    # against a full race. Those drivers carry no luck or crew score, which also keeps them
    # out of the field average and season totals.
    results = [
        dataclasses.replace(r, race_luck=None, race_execution=None)
        if r.driver_number in outcomes
        else r
        for r in analysis.results
    ]
    return SessionScore(
        session,
        drivers,
        results,
        analysis.baseline,
        analysis.baseline_estimated,
        analysis.typical_lane,
        lap_status,
        timeline.periods,
        outcomes,
    )


def _leader_lap_starts(laps: list[Lap]) -> dict[int, datetime]:
    """When the first car started each lap."""
    starts: dict[int, datetime] = {}
    for lap in laps:
        if lap.date_start is not None and (
            lap.lap_number not in starts or lap.date_start < starts[lap.lap_number]
        ):
            starts[lap.lap_number] = lap.date_start
    return starts
