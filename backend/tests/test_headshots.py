import asyncio

import httpx

from app import headshots
from app.openf1.schemas import Driver


def _driver(headshot_url: str | None = None, **kw: str) -> Driver:
    fields = {
        "full_name": "Franco COLAPINTO",
        "first_name": "Franco",
        "last_name": "Colapinto",
        "team_name": "Alpine",
    }
    return Driver(
        session_key=1,
        driver_number=43,
        name_acronym="COL",
        headshot_url=headshot_url,
        **(fields | kw),
    )


def _resolve(driver: Driver, year: int, available: set[str]) -> str | None:
    """Resolve against a fake image server that only has the photo folders in `available`."""
    headshots._exists.clear()

    def handler(request: httpx.Request) -> httpx.Response:
        found = any(f"/common/f1/{a}/" in str(request.url) for a in available)
        return httpx.Response(200 if found else 404)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            await headshots.resolve(http, [driver], year)

    asyncio.run(run())
    return driver.headshot_url


def test_uses_the_session_portrait_when_present() -> None:
    assert headshots.headshot(_driver("https://x/own.png")) == "https://x/own.png"


def test_year_specific_portrait_preferred() -> None:
    headshots.remember([_driver("https://x/mercedes.png", full_name="Year DRIVER")], year=2024)
    headshots.remember([_driver("https://x/ferrari.png", full_name="Year DRIVER")], year=2025)
    assert (
        headshots.headshot(_driver(full_name="Year DRIVER"), year=2024) == "https://x/mercedes.png"
    )
    assert (
        headshots.headshot(_driver(full_name="Year DRIVER"), year=2025) == "https://x/ferrari.png"
    )


def test_never_borrows_another_seasons_portrait() -> None:
    headshots.remember([_driver("https://x/2025.png", full_name="Other SEASON")], year=2025)
    assert headshots.headshot(_driver(full_name="Other SEASON"), year=2024) is None


def test_uses_the_photo_for_that_season_and_team() -> None:
    old = "https://media.formula1.com/x/drivers/L/LEWHAM01_Lewis_Hamilton/lewham01.png"
    ham = _driver(old, full_name="Lewis HAMILTON", team_name="Mercedes")
    url = _resolve(ham, 2024, {"2024/mercedes/lewham01", "2025/ferrari/lewham01"})
    assert url is not None and "/2024/mercedes/lewham01/" in url


def test_borrows_only_from_a_season_with_the_same_team_name() -> None:
    url = "https://x/drivers/J/JACDOO01_Jack_Doohan/jacdoo01.png"
    doo = _driver(url, full_name="Jack DOOHAN", team_name="Alpine")
    got = _resolve(doo, 2024, {"2025/alpine/jacdoo01"})
    assert got is not None and "/2025/alpine/jacdoo01/" in got

    # RB became Racing Bulls in 2025: a different suit, so OpenF1's link is kept instead
    old = "https://x/drivers/L/LIALAW01_Liam_Lawson/lialaw01.png"
    law = _driver(old, full_name="Liam LAWSON", team_name="RB")
    assert _resolve(law, 2024, {"2025/racingbulls/lialaw01"}) == old


def test_guesses_the_code_when_openf1_has_no_link() -> None:
    col = _driver(None, team_name="Alpine")
    url = _resolve(col, 2025, {"2025/alpine/fracol01"})
    assert url is not None and "/2025/alpine/fracol01/" in url
