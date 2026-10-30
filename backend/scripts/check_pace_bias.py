"""
Checks that timing luck does not depend on how fast a car is.

A normal green-flag stop has no luck in it, so with fair scoring every team's green-flag
stops average close to zero. This scores every race of the chosen seasons, prints each team's
average green-stop luck next to its usual pace gap to the field, and the correlation between
the two across every team and season. A correlation near zero means car speed no longer
predicts luck; strongly negative means slow cars look unlucky, strongly positive the reverse.

Usage (from backend/):
    python scripts/check_pace_bias.py            # 2024, 2025 and 2026
    python scripts/check_pace_bias.py 2025       # one season

OpenF1 responses for finished races are cached in backend/.cache, so later runs are quick.
Exits with status 1 when the correlation is beyond MAX_CORRELATION.
"""

from __future__ import annotations

import asyncio
import statistics
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.openf1 import client as openf1  # noqa: E402
from app.scoring.neutralised import FlagStatus  # noqa: E402
from app.scoring.pipeline import score_session  # noqa: E402

SEASONS = (2024, 2025, 2026)
MAX_CORRELATION = 0.3


async def collect(seasons: list[int]) -> dict[tuple[int, str], tuple[list[float], list[float]]]:
    """(season, team) → (luck of each plain green-flag stop, each driver-race pace gap)."""
    data: dict[tuple[int, str], tuple[list[float], list[float]]] = defaultdict(lambda: ([], []))
    async with httpx.AsyncClient(timeout=60) as http:
        for year in seasons:
            for session in await openf1.get_sessions(http, year):
                if session.session_name != "Race" or session.date_start > datetime.now(UTC):
                    continue
                scored = await score_session(http, session, persist=True)
                for result in scored.results:
                    driver = scored.driver(result.driver_number)
                    if driver is None:
                        continue
                    luck, pace = data[(year, driver.team_name)]
                    if result.own_pace is not None:
                        pace.append(result.own_pace)
                    luck.extend(
                        stop.luck
                        for stop in result.stops
                        if stop.status == FlagStatus.GREEN
                        and stop.luck is not None
                        and not stop.missed
                    )
    return data


def main() -> None:
    seasons = [int(a) for a in sys.argv[1:]] or list(SEASONS)
    data = collect_sync(seasons)
    rows = [
        (year, team, statistics.mean(luck), statistics.mean(pace), len(luck))
        for (year, team), (luck, pace) in sorted(data.items())
        if luck and pace
    ]
    for year in seasons:
        print(f"\n{year}  team, average luck of plain green-flag stops, usual pace gap")
        for _, team, luck, pace, stops in sorted(
            (r for r in rows if r[0] == year), key=lambda r: r[3]
        ):
            print(f"  {team:<20} {luck:+6.2f} s   {pace:+6.2f} s/lap   ({stops} stops)")

    correlation = statistics.correlation([r[3] for r in rows], [r[2] for r in rows])
    print(f"\nCorrelation between car pace and green-stop luck: {correlation:+.2f}")
    if abs(correlation) > MAX_CORRELATION:
        print(f"Beyond ±{MAX_CORRELATION}: car speed is influencing the luck scores.")
        sys.exit(1)
    print("Car speed does not predict luck.")


def collect_sync(seasons: list[int]) -> dict[tuple[int, str], tuple[list[float], list[float]]]:
    return asyncio.run(collect(seasons))


if __name__ == "__main__":
    main()
