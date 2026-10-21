"""
Pit-stop luck, measured on track.

Under a safety car the pit lane takes as long as ever; the saving is that rivals are crawling
round behind the safety car meanwhile. So each stop is measured by how much time it cost
against the rest of the field, not by the pit-lane clock.

For every stop:
  time_loss   = (in-lap + out-lap) − field pace over the same two laps, where field pace is
                the median clean lap of the other cars that started a lap closest in time
                under the same race state. Matching on time means a safety car appearing
                mid-lap slows the reference laps as much as it slows the stopping car.
  lane_excess = pit-lane time − the race's typical pit-lane time.
                Crew speed, double-stack waits and served penalties all live here.
  adjusted    = max(0, time_loss − lane_excess)   (the cost had the pit lane gone normally;
                                                   a stop can't be better than free)

  baseline    = trimmed mean of `adjusted` for stops made entirely under green flags
  luck        = baseline − adjusted                       (+ timing made it cheaper)
  execution   = typical lane time − (lane time − penalty) (+ crew quicker than usual)

Missed opportunities: when the race is neutralised a lap or two after a driver stops, the
cars that pit under it get a cheap stop and the driver who just paid full price does not.
  missed = −max(0, gain − luck of the earlier stop)
  gain   = median luck of the stops made under that SC/VSC, or a whole normal stop for a red
           flag (teams may change tyres for free while the race is suspended)
Skipped when most of the field was caught out the same way, since then nobody lost out.

race_luck = Σ (luck + missed) over the driver's stops
"""

import statistics
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from app.openf1.schemas import Lap, PitStop, RaceControlMessage
from app.scoring.neutralised import FlagStatus, Period, Timeline
from app.scoring.penalties import ServedPenalty, match_penalties

# Stops this many times slower than normal are repairs, retirements, red-flag waits or
# incidents on the in/out-lap — not timing luck — so they are left unscored.
OUTLIER_FACTOR = 1.5
# A neutralisation this many laps after a stop counts as "just missed it".
MISSED_WINDOW_LAPS = 2
# Field-pace reference: the clean laps that started closest in time to the stopping car's.
REFERENCE_LAPS = 7
MIN_REFERENCE_LAPS = 2
REFERENCE_GAPS = (timedelta(seconds=60), timedelta(seconds=180), timedelta(seconds=300))
MIN_BASELINE_STOPS = 3
# A visit under the safety car this much quicker than a normal stop never stopped at all.
PASS_THROUGH_MARGIN = 2.0
TRIM_PCT = 0.10

LapIndex = dict[int, dict[int, Lap]]  # driver → lap number → lap
LapState = tuple[FlagStatus, FlagStatus, FlagStatus]


@dataclass(frozen=True)
class ScoredStop:
    lap_number: int  # the in-lap
    pit_duration: float  # pit-lane time
    status: FlagStatus  # race state while the car was in the pit lane
    time_loss: float | None  # seconds lost to the field over in-lap + out-lap
    luck: float | None  # None when the stop can't be scored
    execution: float | None
    penalty: float  # seconds of penalty served at this stop
    missed: float = 0.0  # ≤ 0: a neutralisation followed straight after this stop
    missed_status: FlagStatus | None = None
    missed_lap: int | None = None
    note: str | None = None  # why a stop is unscored or special

    @property
    def total(self) -> float | None:
        if self.luck is None and not self.missed:
            return None
        return (self.luck or 0.0) + self.missed


@dataclass(frozen=True)
class RaceLuckResult:
    driver_number: int
    race_luck: float | None  # None when the race has no baseline
    race_execution: float | None
    no_stops: bool
    insufficient_baseline_data: bool
    stops: list[ScoredStop]


@dataclass(frozen=True)
class RaceAnalysis:
    baseline: float | None  # normal green-flag pit loss
    baseline_estimated: bool  # no green-flag stops to measure, so taken from pit-lane time
    typical_lane: float | None  # normal pit-lane time
    results: list[RaceLuckResult]


@dataclass
class _Draft:
    stop: PitStop
    status: FlagStatus
    penalty: ServedPenalty | None
    in_lap: int
    out_lap: int
    time_loss: float | None = None
    adjusted: float | None = None
    execution: float | None = None
    fully_green: bool = False
    genuine: bool = True  # a real tyre stop (not a penalty, pass-through, red-flag wait…)
    note: str | None = None
    luck: float | None = None
    missed: tuple[float, FlagStatus, int] | None = None

    @property
    def driver(self) -> int:
        return self.stop.driver_number


def analyse_race(
    driver_numbers: list[int],
    stops: list[PitStop],
    laps: list[Lap],
    messages: list[RaceControlMessage],
    timeline: Timeline,
    lap_status: dict[int, FlagStatus],
) -> RaceAnalysis:
    laps_by_driver = _index_laps(laps)
    drafts = _drafts(stops, messages, laps_by_driver, timeline, lap_status)

    typical_lane = compute_typical_lane(drafts)
    if typical_lane is not None:
        for d in drafts:
            if _is_pass_through(d, typical_lane):
                d.genuine = False
                d.note = "Drove through the pit lane behind the safety car"

    # Pass-throughs happen to everyone at once, so those laps stay usable as a reference
    visits = [d for d in drafts if d.note is None]
    field = _Field(laps_by_driver, visits, timeline)
    for d in visits:
        _measure(d, typical_lane, field, visits)

    baseline = compute_baseline(
        [d.adjusted for d in drafts if d.fully_green and d.adjusted is not None]
    )
    estimated = False
    if baseline is None and typical_lane is not None and any(d.adjusted for d in drafts):
        # Every stop came under a neutralisation. A green stop costs roughly the pit-lane
        # time (the lane replaces a stretch of track that takes a few seconds at speed), so
        # fall back to that rather than leaving the race unscored.
        baseline, estimated = typical_lane, True

    if baseline is not None:
        for d in drafts:
            if d.status == FlagStatus.RED:
                d.luck = 0.0  # everyone gets the free tyre change; missed covers the losers
            elif d.adjusted is not None and d.adjusted > baseline * OUTLIER_FACTOR:
                d.note = "Lost heavy time on the in- or out-lap — not scored"
            elif d.adjusted is not None:
                d.luck = baseline - d.adjusted
        _assign_missed(drafts, baseline, timeline, laps_by_driver)

    results = [
        _result(dn, [d for d in drafts if d.driver == dn], baseline) for dn in driver_numbers
    ]
    return RaceAnalysis(
        baseline=baseline,
        baseline_estimated=estimated,
        typical_lane=typical_lane,
        results=results,
    )


def compute_baseline(adjusted_losses: list[float], trim_pct: float = TRIM_PCT) -> float | None:
    """Trimmed mean of green-flag pit losses after dropping outliers.
    Returns None if fewer than MIN_BASELINE_STOPS qualifying stops exist."""
    values = [v for v in adjusted_losses if v > 0]
    if values:
        median = statistics.median(values)
        values = [v for v in values if median / OUTLIER_FACTOR <= v <= median * OUTLIER_FACTOR]
    if len(values) < MIN_BASELINE_STOPS:
        return None
    values.sort()
    trim_n = int(len(values) * trim_pct)
    trimmed = values[trim_n : len(values) - trim_n] if trim_n else values
    return statistics.mean(trimmed)


def compute_typical_lane(drafts: list[_Draft]) -> float | None:
    """Median pit-lane time of ordinary stops. Green-flag stops only where possible: under a
    safety car the field is sometimes driven through the pit lane without stopping."""
    usable = [
        d for d in drafts if d.status != FlagStatus.RED and not (d.penalty and d.penalty.whole_stop)
    ]
    green = [d for d in usable if d.status == FlagStatus.GREEN]
    lanes = [_lane_without_penalty(d) for d in green or usable]
    if not lanes:
        return None
    median = statistics.median(lanes)
    return statistics.median([v for v in lanes if v <= median * OUTLIER_FACTOR])


# ── stop preparation ─────────────────────────────────────────────────────────


def _drafts(
    stops: list[PitStop],
    messages: list[RaceControlMessage],
    laps_by_driver: LapIndex,
    timeline: Timeline,
    lap_status: dict[int, FlagStatus],
) -> list[_Draft]:
    statuses = [_stop_status(s, timeline, lap_status) for s in stops]
    green = [
        s.pit_duration for s, st in zip(stops, statuses, strict=True) if st == FlagStatus.GREEN
    ]
    rough_lane = statistics.median(green or [s.pit_duration for s in stops]) if stops else None
    penalties = match_penalties(stops, messages, rough_lane)
    drafts = []
    for i, (stop, status) in enumerate(zip(stops, statuses, strict=True)):
        in_lap, out_lap = _stop_laps(stop, laps_by_driver.get(stop.driver_number, {}))
        drafts.append(_Draft(stop, status, penalties.get(i), in_lap, out_lap))
    return drafts


def _stop_status(
    stop: PitStop, timeline: Timeline, lap_status: dict[int, FlagStatus]
) -> FlagStatus:
    if stop.entry is not None and stop.date is not None:
        return timeline.worst_between(stop.entry, stop.date)
    return lap_status.get(stop.lap_number + 1, FlagStatus.GREEN)


def _stop_laps(stop: PitStop, own: dict[int, Lap]) -> tuple[int, int]:
    """(in-lap, out-lap). OpenF1's lap_number is the in-lap at some circuits and the out-lap
    at others, depending on where the timing line sits along the pit lane, so the laps are
    found from the pit entry and exit timestamps instead."""
    if stop.entry is not None and stop.date is not None:
        entered = _lap_at(own, stop.entry)
        exited = _lap_at(own, stop.date)
        if entered is not None and exited is not None:
            return entered, max(exited, entered + 1)
    return stop.lap_number, stop.lap_number + 1


def _is_pass_through(d: _Draft, typical_lane: float) -> bool:
    """A trip down the pit lane with no stop: only happens behind the safety car, and is
    quicker than any real stop because nobody is stationary."""
    if d.status != FlagStatus.SC:
        return False
    if d.stop.stop_duration is not None:
        return d.stop.stop_duration < 1.0
    return d.stop.pit_duration < typical_lane - PASS_THROUGH_MARGIN


def _lane_without_penalty(d: _Draft) -> float:
    return d.stop.pit_duration - (d.penalty.seconds if d.penalty else 0.0)


# ── per-stop measurement ─────────────────────────────────────────────────────


class _Field:
    """Lap timing for the whole field, for measuring a stop against everyone else."""

    def __init__(self, laps_by_driver: LapIndex, visits: list[_Draft], timeline: Timeline) -> None:
        self.laps_by_driver = laps_by_driver
        self.timeline = timeline
        pitting: dict[int, set[int]] = defaultdict(set)
        for v in visits:
            pitting[v.driver].update(range(v.in_lap, v.out_lap + 1))
        # Clean laps: not lap 1, not an in- or out-lap. Tagged with how the race state ran
        # through the lap, so a green lap is never the reference for a safety-car lap, nor a
        # lap the safety car joined halfway for one spent wholly behind it.
        self._clean: list[tuple[int, datetime, float, LapState]] = [
            (driver, lap.date_start, lap.lap_duration, self.lap_state(lap))
            for driver, laps in laps_by_driver.items()
            for lap in laps.values()
            if lap.date_start is not None
            and lap.lap_duration is not None
            and lap.lap_number != 1
            and lap.lap_number not in pitting[driver]
        ]

    def lap_state(self, lap: Lap) -> LapState:
        """(state at the start, worst state during, state at the end)."""
        if lap.date_start is None or lap.date_end is None:
            return FlagStatus.GREEN, FlagStatus.GREEN, FlagStatus.GREEN
        return (
            self.timeline.status_at(lap.date_start),
            self.timeline.worst_between(lap.date_start, lap.date_end),
            self.timeline.status_at(lap.date_end),
        )

    def time_loss(self, d: _Draft) -> tuple[float, datetime, datetime] | None:
        """In-lap + out-lap against what the rest of the field lapped at the same moments."""
        own = self.laps_by_driver.get(d.driver, {})
        in_lap, out_lap = own.get(d.in_lap), own.get(d.out_lap)
        if (
            in_lap is None
            or out_lap is None
            or in_lap.lap_duration is None
            or out_lap.lap_duration is None
            or in_lap.date_start is None
            or out_lap.date_end is None
        ):
            return None
        in_pace, out_pace = self.pace(in_lap, d.driver), self.pace(out_lap, d.driver)
        if in_pace is None or out_pace is None:
            return None
        loss = in_lap.lap_duration + out_lap.lap_duration - in_pace - out_pace
        return loss, in_lap.date_start, out_lap.date_end

    def pace(self, lap: Lap, exclude_driver: int) -> float | None:
        """Median of the other cars' clean laps that started closest to this one under the
        same race state. When most of the field pits at once (typical under a safety car)
        clean laps are scarce, so the window widens, and then the state match loosens from
        the exact pattern to just the worst state during the lap."""
        assert lap.date_start is not None
        start, state = lap.date_start, self.lap_state(lap)
        for exact in (True, False):
            nearby = sorted(
                (abs(their_start - start), duration)
                for driver, their_start, duration, their_state in self._clean
                if driver != exclude_driver
                and (their_state == state if exact else their_state[1] == state[1])
            )[:REFERENCE_LAPS]
            for max_gap in REFERENCE_GAPS:
                nearest = [duration for gap, duration in nearby if gap <= max_gap]
                if len(nearest) >= MIN_REFERENCE_LAPS:
                    return statistics.median(nearest)
        return None


def _measure(d: _Draft, typical_lane: float | None, field: _Field, visits: list[_Draft]) -> None:
    lane = d.stop.pit_duration
    if d.status == FlagStatus.RED:
        d.genuine = False
        d.note = "Free tyre change under the red flag"
        return
    if d.penalty and d.penalty.whole_stop:
        d.genuine = False
        d.note = d.penalty.label
        return
    if typical_lane is None:
        return
    if _lane_without_penalty(d) > typical_lane * OUTLIER_FACTOR:
        d.genuine = False
        d.note = "Abnormal stop — repairs, retirement or a long wait"
        return

    d.execution = typical_lane - _lane_without_penalty(d)
    if any(
        other is not d
        and other.driver == d.driver
        and other.in_lap <= d.out_lap
        and other.out_lap >= d.in_lap
        for other in visits
    ):
        d.note = "Back-to-back pit visits — the laps can't be separated"
        return
    measured = field.time_loss(d)
    if measured is None:
        d.note = "No lap timing to measure against"
        return
    d.time_loss, window_start, window_end = measured
    window = field.timeline.worst_between(window_start, window_end)
    if window == FlagStatus.RED:
        d.note = "Red flag came out during the in- or out-lap"
        return
    # Under a safety car the car that pits can close up to the queue, which would otherwise
    # read as a stop that gained time.
    d.adjusted = max(0.0, d.time_loss - (lane - typical_lane))
    d.fully_green = window == FlagStatus.GREEN
    if d.penalty:
        d.note = f"{d.penalty.label} served — not counted as bad luck"


# ── missed opportunities ─────────────────────────────────────────────────────


def _assign_missed(
    drafts: list[_Draft], baseline: float, timeline: Timeline, laps_by_driver: LapIndex
) -> None:
    by_driver: dict[int, list[_Draft]] = defaultdict(list)
    for d in drafts:
        by_driver[d.driver].append(d)

    for period in timeline.periods:
        gain = _period_gain(period, drafts, baseline)
        if gain is None or gain <= 0:
            continue

        caught_out: list[tuple[_Draft, float]] = []
        running = 0
        for driver in laps_by_driver.keys() | by_driver.keys():
            laps = laps_by_driver.get(driver, {})
            if not _still_running(laps, period.start):
                continue
            running += 1
            own = by_driver.get(driver, [])
            before = [d for d in own if d.genuine and d.stop.date and d.stop.date < period.start]
            if not before:
                continue
            prior = max(before, key=lambda d: d.stop.date or datetime.min)
            current_lap = _lap_at(laps, period.start) or period.start_lap
            if prior.in_lap < current_lap - MISSED_WINDOW_LAPS:
                continue
            if period.status != FlagStatus.RED and any(_entered_during(d, period) for d in own):
                continue  # pitted again under it, so got the cheap stop anyway
            # Unmeasured stops are assumed to have cost what was normal for their conditions
            prior_luck = prior.luck if prior.luck is not None else _typical_luck(prior, drafts)
            missed = -max(0.0, gain - prior_luck)
            if missed < 0:
                caught_out.append((prior, missed))

        # When most of the field was caught out the same way, nobody lost out to anybody
        if len(caught_out) * 2 > running:
            continue
        for prior, missed in caught_out:
            if prior.missed is None or missed < prior.missed[0]:
                prior.missed = (missed, period.status, period.start_lap)


def _entered_during(d: _Draft, period: Period) -> bool:
    return d.stop.entry is not None and period.start <= d.stop.entry <= period.end


def _period_gain(period: Period, drafts: list[_Draft], baseline: float) -> float | None:
    """What pitting during this neutralisation saved, on average."""
    if period.status == FlagStatus.RED:
        return baseline  # a whole stop, for free
    under = [
        d.luck
        for d in drafts
        if d.luck is not None and d.status == period.status and _entered_during(d, period)
    ]
    return statistics.median(under) if under else None  # nobody pitted: nothing to miss


def _typical_luck(stop: _Draft, drafts: list[_Draft]) -> float:
    if stop.status == FlagStatus.GREEN:
        return 0.0
    same = [d.luck for d in drafts if d.luck is not None and d.status == stop.status]
    return statistics.median(same) if same else 0.0


def _lap_at(laps: dict[int, Lap], t: datetime) -> int | None:
    """The lap a driver was on at time `t`."""
    started = [lap.lap_number for lap in laps.values() if lap.date_start and lap.date_start <= t]
    return max(started, default=None)


def _still_running(laps: dict[int, Lap], t: datetime) -> bool:
    # No lap data at all means we can't tell, so give the benefit of the doubt
    return not laps or any(lap.date_start and lap.date_start > t for lap in laps.values())


# ── assembly ─────────────────────────────────────────────────────────────────


def _index_laps(laps: list[Lap]) -> LapIndex:
    index: LapIndex = defaultdict(dict)
    for lap in laps:
        index[lap.driver_number][lap.lap_number] = lap
    return index


def _scored(d: _Draft) -> ScoredStop:
    stop = ScoredStop(
        lap_number=d.in_lap,
        pit_duration=d.stop.pit_duration,
        status=d.status,
        time_loss=d.time_loss,
        luck=d.luck,
        execution=d.execution,
        penalty=d.penalty.seconds if d.penalty and not d.penalty.whole_stop else 0.0,
        note=d.note,
    )
    if d.missed is not None:
        missed, status, lap = d.missed
        stop = replace(stop, missed=missed, missed_status=status, missed_lap=lap)
    return stop


def _result(driver_number: int, drafts: list[_Draft], baseline: float | None) -> RaceLuckResult:
    stops = [_scored(d) for d in sorted(drafts, key=lambda d: d.in_lap)]
    totals = [s.total for s in stops if s.total is not None]
    executions = [s.execution for s in stops if s.execution is not None]
    return RaceLuckResult(
        driver_number=driver_number,
        race_luck=(sum(totals) if baseline is not None else None) if stops else 0.0,
        race_execution=sum(executions) if executions else None,
        no_stops=not stops,
        insufficient_baseline_data=baseline is None,
        stops=stops,
    )
