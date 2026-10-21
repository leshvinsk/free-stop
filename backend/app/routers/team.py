from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query

from app.dependencies import Store, check_season
from app.models import TeamSummary
from app.service import get_team_summary

router = APIRouter(tags=["team"])


@router.get("/team/{team_key}", response_model=TeamSummary)
async def team_summary(
    team_key: str,
    store: Store,
    year: int | None = Query(default=None, description="Season year. Defaults to current year."),
) -> TeamSummary:
    """A team's luck, pit crew and drivers across a season, plus its name in every season."""
    year = check_season(year or datetime.now(UTC).year)
    result = await get_team_summary(store, team_key, year)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No team '{team_key}' in {year}.")
    return result
