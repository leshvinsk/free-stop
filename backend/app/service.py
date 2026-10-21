"""
Service layer: turns scored sessions into API response models.
Routers are thin; all business logic lives here.
"""

from collections import defaultdict

from app import headshots
from app.models import (
    DriverRaceResult,
    DriverSummary,
    Progress,
    RaceDetail,
    RaceDriverResult,
    RaceEvent,
    RaceRef,
    SeasonDriver,
    SeasonSummary,
    StopDetail,
    TeamRaceDriver,
    TeamRaceResult,
    TeamSeason,
    TeamStanding,
    TeamSummary,
)
from app.openf1.schemas import Session
from app.scoring.formula import ScoredStop
from app.scoring.neutralised import FlagStatus
from app.scoring.pipeline import SessionScore
from app.store import ScoreStore
from app.teams import seasons as team_seasons
from app.teams import team_key


async def get_race_detail(store: ScoreStore, session_key: int) -> RaceDetail | None:
    session = await store.session(session_key)
    if session is None:
        return None
    store.prefetch_extras(session)
    season = await store.sessions(session.year)
    round_no = next((i for i, s in enumerate(season, 1) if s.session_key == session_key), None)
    scored = await store.score(session)
    return _build_race_detail(store, scored, round_no)


async def get_season_summary(store: ScoreStore, year: int) -> SeasonSummary:
    sessions = await store.sessions(year)
    pending = store.ensure_warming(year, sessions)
    scores = [sc for s in sessions if (sc := store.cached(s)) is not None]
    return SeasonSummary(
        year=year,
        progress=Progress(
            rounds_total=len(sessions), rounds_scored=len(scores), complete=not pending
        ),
        min_races=min_races(len(scores)),
        drivers=_rank_drivers(scores),
    )


def min_races(rounds_scored: int) -> int:
    """A stand-in with a couple of lucky races shouldn't headline the season: to be named
    luckiest or unluckiest a driver needs a third of the rounds (and at least three)."""
    return max(1, min(rounds_scored, max(3, -(-rounds_scored // 3))))


async def get_driver_summary(
    store: ScoreStore, driver_number: int, year: int
) -> DriverSummary | None:
    season = await get_season_summary(store, year)
    season_driver = next((d for d in season.drivers if d.driver_number == driver_number), None)
    if season_driver is None:
        return None

    races: list[DriverRaceResult] = []
    for round_no, session in enumerate(await store.sessions(year), 1):
        scored = store.cached(session)
        if scored is None:
            continue
        result = next((r for r in scored.results if r.driver_number == driver_number), None)
        if result is None:
            continue
        races.append(
            DriverRaceResult(
                session_key=session.session_key,
                round=round_no,
                race_name=store.race_name(session),
                circuit=session.circuit_short_name,
                date=session.date_start.date(),
                race_luck=_round(scored.relative_luck(driver_number)),
                race_luck_raw=_round(result.race_luck),
                race_execution=result.race_execution,
                no_stops=result.no_stops,
                insufficient_baseline_data=result.insufficient_baseline_data,
                outcome=scored.outcome(driver_number),
            )
        )

    return DriverSummary(
        **season_driver.model_dump(exclude={"races_no_stops"}),
        progress=season.progress,
        races=races,
    )


async def get_race_index(store: ScoreStore, year: int) -> list[RaceRef]:
    return [
        RaceRef(
            session_key=s.session_key,
            round=i,
            race_name=store.race_name(s),
            circuit=s.circuit_short_name,
            location=s.location,
            date=s.date_start.date(),
        )
        for i, s in enumerate(await store.sessions(year), 1)
    ]


# ── builders ─────────────────────────────────────────────────────────────────


def _build_race_detail(store: ScoreStore, scored: SessionScore, round_no: int | None) -> RaceDetail:
    session: Session = scored.session
    drivers: list[RaceDriverResult] = []
    for result in scored.results:
        driver = scored.driver(result.driver_number)
        if driver is None:
            continue
        drivers.append(
            RaceDriverResult(
                driver_number=result.driver_number,
                full_name=driver.full_name,
                name_acronym=driver.name_acronym,
                team_name=driver.team_name,
                team_key=team_key(driver.team_name),
                team_colour=driver.team_colour,
                headshot_url=headshots.headshot(driver, scored.session.year),
                race_luck=_round(scored.relative_luck(result.driver_number)),
                race_luck_raw=_round(result.race_luck),
                race_execution=_round(result.race_execution),
                no_stops=result.no_stops,
                insufficient_baseline_data=result.insufficient_baseline_data,
                outcome=scored.outcome(result.driver_number),
                stops=[_stop_detail(s) for s in result.stops],
            )
        )
    drivers.sort(key=lambda d: d.race_luck or 0, reverse=True)

    return RaceDetail(
        session_key=session.session_key,
        round=round_no,
        race_name=store.race_name(session),
        circuit=session.circuit_short_name,
        date=session.date_start.date(),
        total_laps=max(scored.lap_status, default=0),
        baseline_pit_loss=_round(scored.baseline),
        baseline_estimated=scored.baseline_estimated,
        typical_pit_lane=_round(scored.typical_lane),
        insufficient_baseline_data=scored.baseline is None,
        field_average=_round(scored.field_average),
        drivers=drivers,
        events=_extract_events(scored.lap_status),
    )


def _stop_detail(stop: ScoredStop) -> StopDetail:
    return StopDetail(
        lap=stop.lap_number,
        pit_duration=stop.pit_duration,
        status=stop.status,
        time_loss=_round(stop.time_loss),
        luck=_round(stop.luck),
        execution=_round(stop.execution),
        penalty=stop.penalty,
        missed=round(stop.missed, 3),
        missed_status=stop.missed_status,
        missed_lap=stop.missed_lap,
        delta=_round(stop.total),
        note=stop.note,
    )


def _round(value: float | None) -> float | None:
    return round(value, 3) if value is not None else None


def _extract_events(lap_status: dict[int, FlagStatus]) -> list[RaceEvent]:
    events: list[RaceEvent] = []
    prev: FlagStatus | None = None
    for lap in sorted(lap_status):
        status = lap_status[lap]
        if status != prev:
            events.append(RaceEvent(lap=lap, type=status, message=status.value))
            prev = status
    return events


def _rank_drivers(sessions: list[SessionScore], only_team: str | None = None) -> list[SeasonDriver]:
    """Season standings. With `only_team`, just that team's drivers, counting only the races
    they drove for it (mid-season swaps happen)."""
    season_luck: dict[int, float] = defaultdict(float)
    season_execution: dict[int, float] = defaultdict(float)
    races_scored: dict[int, int] = defaultdict(int)
    races_no_stops: dict[int, int] = defaultdict(int)
    latest: dict[int, SeasonDriver] = {}

    for scored in sessions:
        for result in scored.results:
            driver = scored.driver(result.driver_number)
            if driver is None or (only_team and team_key(driver.team_name) != only_team):
                continue
            # Later sessions overwrite earlier ones, so mid-season team swaps show the latest team
            previous = latest.get(result.driver_number)
            # A real portrait from an earlier race beats a remembered or guessed one
            portrait = driver.headshot_url or (previous and previous.headshot_url)
            latest[result.driver_number] = SeasonDriver(
                driver_number=driver.driver_number,
                full_name=driver.full_name,
                name_acronym=driver.name_acronym,
                team_name=driver.team_name,
                team_key=team_key(driver.team_name),
                team_colour=driver.team_colour,
                headshot_url=portrait or headshots.headshot(driver, scored.session.year),
                luck_per_race=0,
                season_luck=0,
                season_execution=0,
                races_scored=0,
                races_no_stops=0,
            )
            relative = scored.relative_luck(result.driver_number)
            if relative is not None:
                season_luck[result.driver_number] += relative
                races_scored[result.driver_number] += 1
            if result.race_execution is not None:
                season_execution[result.driver_number] += result.race_execution
            if result.no_stops:
                races_no_stops[result.driver_number] += 1

    drivers = [
        d.model_copy(
            update={
                "luck_per_race": round(season_luck[dn] / races_scored[dn], 3)
                if races_scored[dn]
                else 0.0,
                "season_luck": round(season_luck[dn], 3),
                "season_execution": round(season_execution[dn], 3),
                "races_scored": races_scored[dn],
                "races_no_stops": races_no_stops[dn],
            }
        )
        for dn, d in latest.items()
    ]
    drivers.sort(key=lambda d: d.luck_per_race, reverse=True)
    return drivers


# ── teams ────────────────────────────────────────────────────────────────────


async def get_team_summary(store: ScoreStore, key: str, year: int) -> TeamSummary | None:
    lineage = team_seasons(key)
    sessions = await store.sessions(year)
    pending = store.ensure_warming(year, sessions)
    scored = [(i, s, sc) for i, s in enumerate(sessions, 1) if (sc := store.cached(s))]
    scores = [sc for _, _, sc in scored]

    races = [r for i, s, sc in scored if (r := _team_race(store, key, i, s, sc)) is not None]
    if not races and year not in lineage:
        return None

    standings = _team_standings(scores)
    rank = next((i for i, t in enumerate(standings, 1) if t.key == key), None)
    lucks = [r.race_luck for r in races if r.race_luck is not None]
    executions = [r.race_execution for r in races if r.race_execution is not None]
    name, colour = _team_identity(scores, key)
    return TeamSummary(
        key=key,
        name=name or lineage.get(year, key),
        team_colour=colour,
        year=year,
        seasons=[TeamSeason(year=y, name=n) for y, n in sorted(lineage.items())],
        progress=Progress(
            rounds_total=len(sessions), rounds_scored=len(scores), complete=not pending
        ),
        rank=rank,
        teams_count=len(standings),
        luck_per_race=round(sum(lucks) / len(lucks), 3) if lucks else 0.0,
        season_luck=round(sum(lucks), 3),
        season_execution=round(sum(executions), 3),
        pit_stops=sum(
            1
            for sc in scores
            for r in sc.results
            if _driver_team(sc, r.driver_number) == key
            for stop in r.stops
            if stop.execution is not None
        ),
        drivers=_rank_drivers(scores, only_team=key),
        races=races,
        standings=standings,
    )


def _driver_team(scored: SessionScore, number: int) -> str | None:
    driver = scored.driver(number)
    return team_key(driver.team_name) if driver else None


def _team_identity(scores: list[SessionScore], key: str) -> tuple[str | None, str | None]:
    """The team's name and colour from its latest race this season."""
    for sc in reversed(scores):
        for d in sc.drivers:
            if team_key(d.team_name) == key:
                return d.team_name, d.team_colour
    return None, None


def _team_race(
    store: ScoreStore, key: str, round_no: int, session: Session, scored: SessionScore
) -> TeamRaceResult | None:
    results = [r for r in scored.results if _driver_team(scored, r.driver_number) == key]
    if not results:
        return None
    lucks = {r.driver_number: scored.relative_luck(r.driver_number) for r in results}
    known = [v for v in lucks.values() if v is not None]
    executions = [r.race_execution for r in results if r.race_execution is not None]
    return TeamRaceResult(
        session_key=session.session_key,
        round=round_no,
        race_name=store.race_name(session),
        circuit=session.circuit_short_name,
        date=session.date_start.date(),
        race_luck=_round(sum(known)) if known else None,
        race_execution=_round(sum(executions)) if executions else None,
        no_stops=all(r.no_stops for r in results),
        insufficient_baseline_data=all(r.insufficient_baseline_data for r in results),
        drivers=[
            TeamRaceDriver(
                driver_number=r.driver_number,
                name_acronym=(d.name_acronym if (d := scored.driver(r.driver_number)) else ""),
                race_luck=_round(lucks[r.driver_number]),
                outcome=scored.outcome(r.driver_number),
            )
            for r in results
        ],
    )


def _team_standings(scores: list[SessionScore]) -> list[TeamStanding]:
    """Teams ranked by combined race luck per race."""
    totals: dict[str, float] = defaultdict(float)
    races: dict[str, int] = defaultdict(int)
    identity: dict[str, tuple[str, str | None]] = {}
    for sc in scores:
        per_team: dict[str, float] = defaultdict(float)
        for r in sc.results:
            driver = sc.driver(r.driver_number)
            relative = sc.relative_luck(r.driver_number)
            if driver is None or relative is None:
                continue
            key = team_key(driver.team_name)
            per_team[key] += relative
            identity[key] = (driver.team_name, driver.team_colour)
        for key, luck in per_team.items():
            totals[key] += luck
            races[key] += 1
    standings = [
        TeamStanding(
            key=key,
            name=identity[key][0],
            team_colour=identity[key][1],
            luck_per_race=round(totals[key] / races[key], 3),
            races_scored=races[key],
        )
        for key in totals
    ]
    standings.sort(key=lambda t: t.luck_per_race, reverse=True)
    return standings
