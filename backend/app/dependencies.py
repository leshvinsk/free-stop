"""
Shared FastAPI dependencies.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app.store import ScoreStore
from app.teams import FIRST_SEASON


async def get_store(request: Request) -> ScoreStore:
    return request.app.state.store  # type: ignore[no-any-return]


Store = Annotated[ScoreStore, Depends(get_store)]


def check_season(year: int) -> int:
    if year < FIRST_SEASON:
        detail = f"Seasons before {FIRST_SEASON} aren't covered."
        raise HTTPException(status_code=404, detail=detail)
    return year
