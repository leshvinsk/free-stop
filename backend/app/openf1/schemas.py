from datetime import datetime, timedelta

from pydantic import BaseModel


class Meeting(BaseModel):
    meeting_key: int
    meeting_name: str  # e.g. "Miami Grand Prix"


class Session(BaseModel):
    session_key: int
    meeting_key: int
    session_name: str
    session_type: str
    date_start: datetime
    date_end: datetime | None = None
    year: int
    country_name: str
    location: str
    circuit_short_name: str


class PitStop(BaseModel):
    session_key: int
    driver_number: int
    lap_number: int  # the in-lap
    pit_duration: float  # total seconds in pit lane
    date: datetime | None = None  # pit exit
    stop_duration: float | None = None  # stationary time; not reported for every season

    @property
    def entry(self) -> datetime | None:
        return self.date - timedelta(seconds=self.pit_duration) if self.date else None


class Lap(BaseModel):
    driver_number: int
    lap_number: int
    date_start: datetime | None = None
    lap_duration: float | None = None  # None on lap 1, red-flag laps and some pit laps
    duration_sector_1: float | None = None
    duration_sector_2: float | None = None

    @property
    def date_end(self) -> datetime | None:
        if self.date_start is None or self.lap_duration is None:
            return None
        return self.date_start + timedelta(seconds=self.lap_duration)


class RaceControlMessage(BaseModel):
    session_key: int
    lap_number: int | None = None
    date: datetime | None = None
    category: str  # "SafetyCar" | "VirtualSafetyCar" | "Flag" | "Other"
    flag: str | None = None  # "RED" | "GREEN" | "YELLOW" | "CHEQUERED" | None
    message: str


class Driver(BaseModel):
    session_key: int
    driver_number: int
    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    name_acronym: str
    team_name: str
    team_colour: str | None = None
    headshot_url: str | None = None


class SessionResult(BaseModel):
    """A driver's classification. Drivers who were never entered (Sargeant at Melbourne 2024,
    whose car went to Albon) are absent rather than flagged."""

    driver_number: int
    dnf: bool | None = None
    dns: bool | None = None
    dsq: bool | None = None

    @property
    def outcome(self) -> str | None:
        if self.dsq:
            return "DSQ"
        if self.dns:
            return "DNS"
        if self.dnf:
            return "DNF"
        return None


class Weather(BaseModel):
    """One reading from the circuit's weather station, about once a minute."""

    date: datetime
    air_temperature: float | None = None
    track_temperature: float | None = None
    humidity: float | None = None
    rainfall: float | None = None  # non-zero while it is raining
    wind_speed: float | None = None  # m/s
    wind_direction: float | None = None  # degrees


class Location(BaseModel):
    """A car's position on track, about 4 times a second."""

    date: datetime
    x: float
    y: float


class CarSample(BaseModel):
    """Car telemetry, about 4 times a second."""

    date: datetime
    speed: float | None = None  # km/h
    drs: int | None = None  # 10, 12, 14 = flap open; 8 = eligible; 0/1 = off
