import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.routers import driver, race, season, team
from app.store import ScoreStore

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(), format="%(levelname)s:  %(name)s %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    http = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    store = ScoreStore(http)
    app.state.store = store
    # Start scoring the current season immediately so the first visitor isn't the one waiting
    warmup = asyncio.create_task(store.warm_year(datetime.now(UTC).year))
    yield
    warmup.cancel()
    await store.aclose()
    await http.aclose()


app = FastAPI(
    title="Free Stop API",
    description="Scores how much of an F1 driver's race result came from pit-stop timing luck.",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.exception_handler(httpx.HTTPError)
async def upstream_error(_: Request, exc: httpx.HTTPError) -> JSONResponse:
    logging.getLogger("openf1").warning("Upstream failure: %r", exc)
    return JSONResponse(
        status_code=502, content={"detail": "OpenF1 is unavailable right now, try again shortly."}
    )


app.include_router(season.router, prefix="/api")
app.include_router(race.router, prefix="/api")
app.include_router(driver.router, prefix="/api")
app.include_router(team.router, prefix="/api")


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
