"""
Race page extras that don't affect scoring: a map of the circuit, and the weather.

The circuit is traced from the fastest lap of qualifying, because in qualifying every driver
opens DRS in every zone; in the race the flap only opens within a second of the car ahead, so
zones would be missing. The lap only supplies the track's shape, zones and straights.
"""

import asyncio
import math
from bisect import bisect_left
from datetime import datetime, timedelta

import httpx

from app.models import CircuitMap, RaceWeather, WeatherSample
from app.openf1 import client as openf1
from app.openf1.schemas import CarSample, Lap, Location, Session

MAP_SIZE = 1000.0  # longest side of the scaled map
DRS_OPEN = 10  # telemetry codes 10, 12 and 14 mean the flap is open
LAST_DRS_SEASON = 2025
MIN_ZONE_POINTS = 3  # shorter runs of "open" are telemetry blips
# A straight: running within this share of the lap's top speed for a few samples
STRAIGHT_SPEED_SHARE = 0.86
MIN_STRAIGHT_POINTS = 8


async def build_circuit(
    http: httpx.AsyncClient, race: Session, *, persist: bool
) -> CircuitMap | None:
    sessions = await openf1.get_meeting_sessions(http, race.meeting_key)
    quali = next((s for s in sessions if s.session_name == "Qualifying"), None)
    source = quali or race
    laps = await openf1.get_laps(http, source.session_key, persist=persist)
    lap = _fastest(laps)
    if lap is None or lap.date_start is None or lap.date_end is None:
        return None

    start, end = lap.date_start, lap.date_end + timedelta(seconds=0.5)
    key, driver = source.session_key, lap.driver_number
    locations, samples = await asyncio.gather(
        openf1.get_location(http, key, driver, start, end, persist=persist),
        openf1.get_car_data(http, key, driver, start, end, persist=persist),
    )
    if len(locations) < 20:
        return None
    return _circuit(lap, locations, samples, quali is not None, race.year)


async def build_weather(
    http: httpx.AsyncClient, race: Session, *, persist: bool
) -> RaceWeather | None:
    readings = await openf1.get_weather(http, race.session_key, persist=persist)
    end = race.date_end or race.date_start + timedelta(hours=3)
    during = [w for w in readings if race.date_start <= w.date <= end] or readings
    if not during:
        return None

    def values(field: str) -> list[float]:
        return [v for w in during if (v := _reading(getattr(w, field))) is not None]

    air, track = values("air_temperature"), values("track_temperature")
    rainy = [bool(w.rainfall) for w in during]
    return RaceWeather(
        air_min=min(air, default=None),
        air_max=max(air, default=None),
        track_min=min(track, default=None),
        track_max=max(track, default=None),
        humidity=_mean(values("humidity")),
        wind_speed=_mean(values("wind_speed")),
        wind_direction=_mean_angle(values("wind_direction")),
        rain_share=sum(rainy) / len(rainy),
        samples=[
            WeatherSample(
                minute=round((w.date - race.date_start).total_seconds() / 60, 1),
                air=_reading(w.air_temperature),
                track=_reading(w.track_temperature),
                rain=bool(w.rainfall),
            )
            for w in during
        ],
    )


# ── helpers ──────────────────────────────────────────────────────────────────


def _fastest(laps: list[Lap]) -> Lap | None:
    timed = [lap for lap in laps if lap.lap_duration and lap.date_start]
    return min(timed, key=lambda lap: lap.lap_duration or math.inf, default=None)


def _circuit(
    lap: Lap,
    locations: list[Location],
    samples: list[CarSample],
    from_qualifying: bool,
    year: int,
) -> CircuitMap:
    assert lap.date_start is not None and lap.lap_duration is not None
    xs, ys = [p.x for p in locations], [p.y for p in locations]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    scale = MAP_SIZE / span
    # Screen y points down, track y points up
    points = [((x - min(xs)) * scale, (max(ys) - y) * scale) for x, y in zip(xs, ys, strict=True)]
    times = [max(0.0, (p.date - lap.date_start).total_seconds()) for p in locations]
    # Shoelace sum; with screen y pointing down, a positive sum runs clockwise
    area = sum(
        points[i][0] * points[(i + 1) % len(points)][1]
        - points[(i + 1) % len(points)][0] * points[i][1]
        for i in range(len(points))
    )

    at = [_nearest(samples, p.date) for p in locations]
    speeds = [float(s.speed) if s and s.speed is not None else 0.0 for s in at]
    open_flags = [bool(s and s.drs is not None and s.drs >= DRS_OPEN) for s in at]

    sectors = []
    elapsed = 0.0
    for split in (lap.duration_sector_1, lap.duration_sector_2):
        if split is None:
            break
        elapsed += split
        sectors.append(min(range(len(times)), key=lambda i: abs(times[i] - elapsed)))

    top = max(speeds, default=0.0)
    fast = [v >= top * STRAIGHT_SPEED_SHARE for v in speeds]
    return CircuitMap(
        source="Qualifying" if from_qualifying else "Race",
        width=round((max(xs) - min(xs)) * scale, 1),
        height=round((max(ys) - min(ys)) * scale, 1),
        points=[(round(x, 1), round(y, 1)) for x, y in points],
        drs_zones=_zones(open_flags),
        straights=_zones(fast, MIN_STRAIGHT_POINTS),
        clockwise=area > 0,
        sectors=sectors,
        drs_era=year <= LAST_DRS_SEASON,
    )


def _nearest(samples: list[CarSample], t: datetime) -> CarSample | None:
    if not samples:
        return None
    i = bisect_left([s.date for s in samples], t)
    options = [samples[j] for j in (i - 1, i) if 0 <= j < len(samples)]
    return min(options, key=lambda s: abs(s.date - t))


def _zones(open_flags: list[bool], min_points: int = MIN_ZONE_POINTS) -> list[tuple[int, int]]:
    """Runs of flagged points. A run that crosses the start line is joined into one that
    wraps (end index below start index)."""
    zones: list[tuple[int, int]] = []
    start: int | None = None
    for i, on in enumerate(open_flags):
        if on and start is None:
            start = i
        elif not on and start is not None:
            zones.append((start, i - 1))
            start = None
    if start is not None:
        if zones and zones[0][0] == 0:
            zones[0] = (start, zones[0][1])
        else:
            zones.append((start, len(open_flags) - 1))
    n = len(open_flags)
    return [z for z in zones if (z[1] - z[0]) % n >= min_points]


def _reading(value: float | None) -> float | None:
    """The weather station sends 0.0 when a sensor drops out; no Grand Prix runs below
    freezing, so treat it as missing."""
    return value if value is not None and value > 0 else None


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def _mean_angle(degrees: list[float]) -> float | None:
    """Average of compass bearings (so 350° and 10° average to 0°, not 180°)."""
    if not degrees:
        return None
    x = sum(math.cos(math.radians(d)) for d in degrees)
    y = sum(math.sin(math.radians(d)) for d in degrees)
    return round(math.degrees(math.atan2(y, x))) % 360
