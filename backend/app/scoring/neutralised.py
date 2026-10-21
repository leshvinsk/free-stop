"""
Works out when a race was neutralised, both per lap (for charts) and to the second (for scoring).

The OpenF1 race_control endpoint emits messages when the race state changes. Real-world forms:
  SafetyCar     "SAFETY CAR DEPLOYED"          → SC from now
  SafetyCar     "SAFETY CAR IN THIS LAP"       → SC ends when the leader next crosses the line
  SafetyCar     "VSC DEPLOYED"                 → VSC from now (older seasons spell it out)
  SafetyCar     "VSC ENDING"                   → VSC ends now
  Flag RED / Other "RED FLAG - RACE SUSPENDED" → RED from now
  SessionStatus "SESSION STARTED" / Flag GREEN → GREEN again after a red flag
There is no explicit green flag after a safety car, so its end must come from "IN THIS LAP".
"TRACK CLEAR" is ignored: it often arrives while the safety car is still out.
"""

from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.openf1.schemas import RaceControlMessage


class FlagStatus(StrEnum):
    GREEN = "GREEN"
    SC = "SC"
    VSC = "VSC"
    RED = "RED"


SEVERITY = {FlagStatus.GREEN: 0, FlagStatus.VSC: 1, FlagStatus.SC: 2, FlagStatus.RED: 3}

# Fallback for when the SC ends if lap timing can't tell us when the leader crossed the line
SC_IN_FALLBACK = timedelta(seconds=90)


@dataclass(frozen=True)
class Period:
    """A continuous spell of neutralisation."""

    status: FlagStatus
    start: datetime
    end: datetime
    start_lap: int


class Timeline:
    """Race state to the second, built from timestamped race control messages."""

    def __init__(self, changes: list[tuple[datetime, int, FlagStatus]]) -> None:
        self._times = [t for t, _, _ in changes]
        self._changes = changes
        self.periods: list[Period] = []
        for i, (start, lap, status) in enumerate(changes):
            if status == FlagStatus.GREEN:
                continue
            end = (
                changes[i + 1][0]
                if i + 1 < len(changes)
                else datetime.max.replace(tzinfo=start.tzinfo)
            )
            self.periods.append(Period(status, start, end, lap))

    def status_at(self, t: datetime) -> FlagStatus:
        i = bisect_right(self._times, t) - 1
        return self._changes[i][2] if i >= 0 else FlagStatus.GREEN

    def worst_between(self, start: datetime, end: datetime) -> FlagStatus:
        """Most severe state at any point in [start, end]."""
        worst = self.status_at(start)
        for p in self.periods:
            if p.start <= end and p.end > start and SEVERITY[p.status] > SEVERITY[worst]:
                worst = p.status
        return worst


def build_timeline(messages: list[RaceControlMessage], lap_starts: dict[int, datetime]) -> Timeline:
    """`lap_starts` maps lap number → when the leader started it, used to place SC endings."""
    changes: list[tuple[datetime, int, FlagStatus]] = []
    current = FlagStatus.GREEN
    for msg in sorted((m for m in messages if m.date), key=lambda m: m.date or datetime.min):
        assert msg.date is not None
        lap = msg.lap_number or 1
        parsed = _parse_message(msg)
        if parsed is None:
            continue
        _, status = parsed
        when = msg.date
        if status == FlagStatus.GREEN:
            if current == FlagStatus.GREEN:
                continue
            if _is_restart(msg) and current != FlagStatus.RED:
                continue  # pit-exit-open / session-started messages only end a red flag
            if current == FlagStatus.SC and "IN THIS LAP" in msg.message.upper():
                # The safety car pulls in as the leader starts the next lap
                when = max(lap_starts.get(lap + 1) or msg.date + SC_IN_FALLBACK, msg.date)
        changes.append((when, lap, status))
        current = status
    changes.sort(key=lambda c: c[0])
    return Timeline(changes)


def classify_laps(
    messages: list[RaceControlMessage],
    total_laps: int,
) -> dict[int, FlagStatus]:
    """Returns a dict mapping every lap_number 1..total_laps → FlagStatus.

    A lap that sees several changes shows the most severe of them, so a red flag that is
    resumed on the same lap number (the lap count doesn't advance while suspended) still shows.
    """
    ordered = sorted(
        (m for m in messages if m.lap_number is not None),
        key=lambda m: (m.lap_number or 0, m.date.timestamp() if m.date else 0.0),
    )
    changes = [change for m in ordered if (change := _parse_message(m)) is not None]
    # Stable sort keeps message order for changes that land on the same lap
    changes.sort(key=lambda c: c[0])

    result: dict[int, FlagStatus] = {}
    current = FlagStatus.GREEN
    i = 0
    for lap in range(1, total_laps + 1):
        on_this_lap: list[FlagStatus] = []
        while i < len(changes) and changes[i][0] <= lap:
            current = changes[i][1]
            on_this_lap.append(current)
            i += 1
        result[lap] = max(on_this_lap, key=SEVERITY.__getitem__) if on_this_lap else current
    return result


def _is_restart(msg: RaceControlMessage) -> bool:
    return msg.category.lower() in {"flag", "sessionstatus"}


def _parse_message(msg: RaceControlMessage) -> tuple[int, FlagStatus] | None:
    """Returns (lap the new status starts, status), or None if the message isn't a state change."""
    lap = msg.lap_number or 1
    category = msg.category.lower()
    text = msg.message.upper()

    if category in {"safetycar", "virtualsafetycar"}:
        virtual = category == "virtualsafetycar" or "VSC" in text or "VIRTUAL" in text
        if "ENDING" in text or "IN THIS LAP" in text:
            return lap + 1, FlagStatus.GREEN
        if "DEPLOYED" in text:
            return lap, FlagStatus.VSC if virtual else FlagStatus.SC
    elif category == "flag":
        flag = (msg.flag or "").upper()
        if flag == "RED":
            return lap, FlagStatus.RED
        if flag == "GREEN":
            return lap, FlagStatus.GREEN
    elif category == "sessionstatus":
        if "STARTED" in text:
            return lap, FlagStatus.GREEN
    elif text.startswith("RED FLAG"):
        return lap, FlagStatus.RED
    return None
