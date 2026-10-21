from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query

from app.dependencies import Store, check_season
from app.models import DriverSummary
from app.service import get_driver_summary

router = APIRouter(tags=["driver"])


@router.get("/driver/{driver_number}", response_model=DriverSummary)
async def driver_summary(
    driver_number: int,
    store: Store,
    year: int | None = Query(default=None, description="Season year. Defaults to current year."),
) -> DriverSummary:
    """A driver's luck score per race across a season."""
    year = check_season(year or datetime.now(UTC).year)
    result = await get_driver_summary(store, driver_number, year)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Driver {driver_number} has no scored races in {year} yet.",
        )
    return result
