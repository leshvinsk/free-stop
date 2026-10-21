from fastapi import APIRouter

from app.dependencies import Store, check_season
from app.models import RaceRef, SeasonSummary
from app.service import get_race_index, get_season_summary

router = APIRouter(tags=["season"])


@router.get("/season/{year}", response_model=SeasonSummary)
async def season_summary(year: int, store: Store) -> SeasonSummary:
    """All drivers ranked by season luck. Returns immediately with whatever races are scored
    so far; poll until `progress.complete` is true."""
    return await get_season_summary(store, check_season(year))


@router.get("/season/{year}/races", response_model=list[RaceRef])
async def race_index(year: int, store: Store) -> list[RaceRef]:
    """Ordered list of Grand Prix sessions that have started."""
    return await get_race_index(store, check_season(year))
