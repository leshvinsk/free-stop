"""
API response models — the shapes returned to the Vue frontend.
These mirror src/types/api.ts in the frontend exactly.
"""

from datetime import date

from pydantic import BaseModel

from app.scoring.neutralised import FlagStatus


class Progress(BaseModel):
    """How much of a season has been scored. Clients poll until `complete` is true."""

    rounds_total: int
    rounds_scored: int
    complete: bool


class StopDetail(BaseModel):
    lap: int  # in-lap
    pit_duration: float  # pit-lane time
    status: FlagStatus  # race state while in the pit lane
    time_loss: float | None  # seconds lost to the field over in-lap + out-lap, car pace allowed for
    luck: float | None  # timing luck of the stop itself
    execution: float | None  # pit-lane time vs normal; + quicker than usual
    penalty: float  # seconds of penalty served at this stop
    missed: float  # ≤ 0: a neutralisation came just after this stop
    missed_status: FlagStatus | None
    missed_lap: int | None
    delta: float | None  # luck + missed: what this stop adds to race luck
    note: str | None


class RaceDriverResult(BaseModel):
    driver_number: int
    full_name: str
    name_acronym: str
    team_name: str
    team_key: str  # stable across renames, for linking to the team page
    team_colour: str | None
    headshot_url: str | None
    race_luck: float | None  # against this race's field average
    race_luck_raw: float | None  # sum of the driver's stops against a normal stop
    race_execution: float | None
    no_stops: bool
    insufficient_baseline_data: bool
    outcome: str | None  # DNF / DNS / DSQ
    stops: list[StopDetail]


class RaceEvent(BaseModel):
    lap: int
    type: FlagStatus
    message: str


class RaceDetail(BaseModel):
    session_key: int
    round: int | None
    race_name: str
    circuit: str
    date: date
    total_laps: int
    baseline_pit_loss: float | None  # time a normal green-flag stop costs
    baseline_estimated: bool  # no green-flag stops, so estimated from pit-lane time
    typical_pit_lane: float | None
    insufficient_baseline_data: bool
    field_average: float | None  # mean raw race luck; race_luck is measured from here
    drivers: list[RaceDriverResult]
    events: list[RaceEvent]


class SeasonDriver(BaseModel):
    driver_number: int
    full_name: str
    name_acronym: str
    team_name: str
    team_key: str
    team_colour: str | None
    headshot_url: str | None
    luck_per_race: float  # average race luck against the field; the ranking value
    season_luck: float  # total race luck against the field
    season_execution: float
    races_scored: int
    races_no_stops: int


class SeasonSummary(BaseModel):
    year: int
    progress: Progress
    min_races: int  # races needed to be named luckiest/unluckiest
    drivers: list[SeasonDriver]  # sorted by luck_per_race, luckiest → unluckiest


class RaceRef(BaseModel):
    session_key: int
    round: int
    race_name: str
    circuit: str
    location: str  # e.g. "Melbourne"; the frontend maps it to a track outline
    date: date


class DriverRaceResult(BaseModel):
    session_key: int
    round: int
    race_name: str
    circuit: str
    date: date
    race_luck: float | None  # against this race's field average
    race_luck_raw: float | None
    race_execution: float | None
    no_stops: bool
    insufficient_baseline_data: bool
    outcome: str | None  # DNF / DNS / DSQ


class DriverSummary(BaseModel):
    driver_number: int
    full_name: str
    name_acronym: str
    team_name: str
    team_key: str
    team_colour: str | None
    headshot_url: str | None
    luck_per_race: float
    season_luck: float
    season_execution: float
    races_scored: int
    progress: Progress
    races: list[DriverRaceResult]  # chronological order


class CircuitMap(BaseModel):
    """A lap of the circuit to draw and animate. Points are scaled into a box `width` ×
    `height` with y pointing down, ready for an SVG viewBox."""

    source: str  # which session the trace came from, e.g. "Qualifying"
    width: float
    height: float
    points: list[tuple[float, float]]
    drs_zones: list[tuple[int, int]]  # [start, end] point indices; end < start wraps the line
    straights: list[tuple[int, int]]  # full-throttle stretches, same index convention
    clockwise: bool  # direction of travel
    sectors: list[int]  # point indices where sectors 2 and 3 begin
    drs_era: bool  # False from 2026, when active aero replaced DRS


class WeatherSample(BaseModel):
    minute: float  # minutes after the start
    air: float | None
    track: float | None
    rain: bool


class RaceWeather(BaseModel):
    air_min: float | None
    air_max: float | None
    track_min: float | None
    track_max: float | None
    humidity: float | None  # average %
    wind_speed: float | None  # average m/s
    wind_direction: float | None  # average degrees the wind blows from
    rain_share: float  # share of readings with rain, 0..1
    samples: list[WeatherSample]


class TeamSeason(BaseModel):
    year: int
    name: str  # what the team was called that season


class TeamRaceDriver(BaseModel):
    driver_number: int
    name_acronym: str
    race_luck: float | None
    outcome: str | None  # DNF / DNS / DSQ


class TeamRaceResult(BaseModel):
    session_key: int
    round: int
    race_name: str
    circuit: str
    date: date
    race_luck: float | None  # the team's drivers combined, against the field
    race_execution: float | None
    no_stops: bool
    insufficient_baseline_data: bool
    drivers: list[TeamRaceDriver]


class TeamStanding(BaseModel):
    key: str
    name: str
    team_colour: str | None
    luck_per_race: float
    races_scored: int


class TeamSummary(BaseModel):
    key: str
    name: str
    team_colour: str | None
    year: int
    seasons: list[TeamSeason]  # every season of this team's lineage, oldest first
    progress: Progress
    rank: int | None  # position among the teams by luck per race
    teams_count: int
    luck_per_race: float
    season_luck: float
    season_execution: float
    pit_stops: int
    drivers: list[SeasonDriver]  # stats from their races for this team only
    races: list[TeamRaceResult]  # chronological order
    standings: list[TeamStanding]  # every team this season, luckiest first


class RacePhoto(BaseModel):
    url: str
    page_url: str  # the file's Commons page, for attribution
    caption: str
    author: str
    license: str  # e.g. "CC BY-SA 4.0"
    taken: str | None  # YYYY-MM-DD


class RacePhotos(BaseModel):
    scope: str  # "weekend" (that race weekend), "circuit" (other years) or "none"
    category: str | None
    photos: list[RacePhoto]
