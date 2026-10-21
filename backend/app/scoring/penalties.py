"""
Penalties served during pit stops, read from the stewards' race control messages:
  "FIA STEWARDS: PENALTY SERVED - 10 SECOND TIME PENALTY FOR CAR 81 (PIA) - SAFETY CAR INFRINGEMENT"
  "FIA STEWARDS: PENALTY SERVED - DRIVE THROUGH PENALTY FOR CAR 44 (HAM) - SPEEDING IN THE PIT LANE"
  "FIA STEWARDS: PENALTY SERVED - STOP-AND-GO PENALTY FOR CAR 2 (SAR) - ..."
The "served" message arrives some laps after the stop, so it is matched to the driver's most
recent stop before it.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.openf1.schemas import PitStop, RaceControlMessage

_SERVED = re.compile(r"PENALTY SERVED - (?P<kind>.*?) FOR CAR (?P<car>\d+)")
_SECONDS = re.compile(r"(\d+) SECOND TIME PENALTY")
_WHOLE_STOP = ("DRIVE THROUGH", "STOP/GO", "STOP-AND-GO", "STOP AND GO")
_ISSUED = re.compile(r"STEWARDS: (?P<seconds>\d+) SECOND TIME PENALTY FOR CAR (?P<car>\d+)")

# A "served" message this long after a stop is about something else
MAX_REPORT_DELAY = timedelta(minutes=20)
# An unreported penalty is assumed served at a stop that ran this share of it over normal
INFER_THRESHOLD = 0.7


@dataclass(frozen=True)
class ServedPenalty:
    seconds: float  # time added to the stop by the penalty
    whole_stop: bool  # drive-through or stop-go: the visit was the penalty, not a tyre stop
    label: str  # e.g. "10s penalty"


def parse_served(msg: RaceControlMessage) -> tuple[int, ServedPenalty] | None:
    match = _SERVED.search(msg.message.upper())
    if match is None:
        return None
    kind = match["kind"]
    car = int(match["car"])
    if any(k in kind for k in _WHOLE_STOP):
        label = "Drive-through penalty" if "DRIVE THROUGH" in kind else "Stop-go penalty"
        return car, ServedPenalty(seconds=0.0, whole_stop=True, label=label)
    if seconds := _SECONDS.search(kind):
        value = float(seconds[1])
        return car, ServedPenalty(seconds=value, whole_stop=False, label=f"{value:g}s penalty")
    return None


def _could_serve(stop: PitStop, penalty: ServedPenalty) -> bool:
    # A drive-through never stops; when OpenF1 misses the drive-through record, this keeps
    # the message from landing on the real stop before it.
    drive_through = penalty.label.startswith("Drive")
    return not (drive_through and stop.stop_duration is not None and stop.stop_duration > 1.0)


def parse_issued(msg: RaceControlMessage) -> tuple[int, float] | None:
    """(car, seconds) for a time penalty being handed out, e.g.
    "FIA STEWARDS: 10 SECOND TIME PENALTY FOR CAR 22 (TSU) - CAUSING A COLLISION"."""
    match = _ISSUED.search(msg.message.upper())
    return (int(match["car"]), float(match["seconds"])) if match else None


def match_penalties(
    stops: list[PitStop],
    messages: list[RaceControlMessage],
    typical_lane: float | None = None,
) -> dict[int, ServedPenalty]:
    """Returns {index into `stops`: penalty served at that stop}. Several penalties served at
    the same stop are added together.

    Stewards don't always post a "served" message, so with `typical_lane` a time penalty that
    was handed out is also placed on the driver's next stop if that stop ran long by about
    the penalty's length."""
    served = _match_served(stops, messages, typical_lane)
    if typical_lane is not None:
        _infer_unreported(stops, messages, typical_lane, served)
    return served


def _infer_unreported(
    stops: list[PitStop],
    messages: list[RaceControlMessage],
    typical_lane: float,
    served: dict[int, ServedPenalty],
) -> None:
    timed = sorted(
        (m for m in messages if m.date is not None), key=lambda m: m.date or datetime.min
    )
    reported: dict[int, int] = {}
    for msg in timed:
        if (parsed := parse_served(msg)) is not None and not parsed[1].whole_stop:
            reported[parsed[0]] = reported.get(parsed[0], 0) + 1

    for msg in timed:
        if (issued := parse_issued(msg)) is None:
            continue
        car, seconds = issued
        if reported.get(car, 0) > 0:
            reported[car] -= 1  # a "served" message already accounts for this one
            continue
        after = sorted(
            (
                (i, s)
                for i, s in enumerate(stops)
                if s.driver_number == car and s.date is not None and msg.date and s.date > msg.date
            ),
            key=lambda pair: pair[1].date or datetime.min,
        )
        if not after:
            continue
        index, stop = after[0]
        if index not in served and stop.pit_duration - typical_lane >= seconds * INFER_THRESHOLD:
            served[index] = ServedPenalty(
                seconds=seconds, whole_stop=False, label=f"{seconds:g}s penalty"
            )


def _match_served(
    stops: list[PitStop], messages: list[RaceControlMessage], typical_lane: float | None
) -> dict[int, ServedPenalty]:
    served: dict[int, ServedPenalty] = {}
    for msg in messages:
        if msg.date is None or (parsed := parse_served(msg)) is None:
            continue
        car, penalty = parsed
        candidates = sorted(
            (
                (i, s)
                for i, s in enumerate(stops)
                if s.driver_number == car
                and s.date is not None
                and s.date <= msg.date
                and msg.date - s.date <= MAX_REPORT_DELAY
            ),
            key=lambda pair: pair[1].date or datetime.min,
            reverse=True,
        )
        if not candidates:
            continue
        # Most recent stop, unless an earlier one is the one that actually ran long
        index = candidates[0][0]
        if typical_lane is not None and penalty.seconds:
            index = next(
                (
                    i
                    for i, s in candidates
                    if s.pit_duration - typical_lane >= penalty.seconds * INFER_THRESHOLD
                ),
                index,
            )
        if not _could_serve(stops[index], penalty):
            continue
        if (prior := served.get(index)) is not None:
            total = prior.seconds + penalty.seconds
            penalty = ServedPenalty(
                seconds=total,
                whole_stop=prior.whole_stop or penalty.whole_stop,
                label=prior.label if prior.whole_stop else f"{total:g}s penalty",
            )
        served[index] = penalty
    return served
