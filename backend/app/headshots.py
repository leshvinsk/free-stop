"""
Driver portraits.

OpenF1 links every driver to one photo in F1's old image library (drivers/L/LEWHAM01_.../
lewham01.png), and F1 swaps that file for the driver's latest photo. So Hamilton's 2024
Mercedes races would show him in Ferrari red. F1's newer image server keeps a photo per season
and team (common/f1/2024/mercedes/lewham01/...), so each driver is resolved in this order:

1. the photo for this season and team;
2. the nearest season in which the team raced under the same name (Doohan's one 2024 race has
   no photo, so he gets his 2025 Alpine one). RB and Racing Bulls never borrow from each other;
3. otherwise OpenF1's link.

OpenF1 also leaves headshot_url empty for some drivers in some sessions (Colapinto in 2025), so
every portrait seen is remembered per (name, year), and a missing photo code is guessed from
F1's naming scheme.
"""

import asyncio
import re
import unicodedata

import httpx

from app import teams
from app.openf1.schemas import Driver

_F1_CLOUD = "https://media.formula1.com/image/upload"
# Head-and-shoulders crop matching the old library's framing. A fixed format and quality
# means one cached copy on F1's servers rather than one per browser.
_CROP = "c_thumb,g_face,w_432,h_432,z_0.55/f_webp/q_80"
_VERSION = "v1740000000"

# Team name as OpenF1 sends it → folder on F1's image server
_TEAM_SLUGS: dict[str, str] = {
    "Red Bull Racing": "redbullracing",
    "Mercedes": "mercedes",
    "Ferrari": "ferrari",
    "McLaren": "mclaren",
    "Aston Martin": "astonmartin",
    "Alpine": "alpine",
    "Williams": "williams",
    "Haas F1 Team": "haasf1team",
    "RB": "rb",
    "Racing Bulls": "racingbulls",
    "Kick Sauber": "kicksauber",
    "Audi": "audi",
    "Cadillac": "cadillac",
}

_CODE = re.compile(r"/([a-z]{6}\d{2})\.png")

# (normalised_name, year) → url
_known: dict[tuple[str, int], str] = {}
# Photo URL → whether F1 has it, shared by every session being scored
_exists: dict[str, asyncio.Task[bool]] = {}


def _key(driver: Driver) -> str:
    return _ascii(driver.full_name).upper()


def _ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def _slug(team_name: str, year: int) -> str | None:
    # F1 filed Haas's 2024 photos under a shorter name
    if team_name == "Haas F1 Team" and year == 2024:
        return "haas"
    return _TEAM_SLUGS.get(team_name)


def _code(driver: Driver) -> str | None:
    """F1's photo code, e.g. lewham01. Taken from OpenF1's link, else guessed from the name."""
    match = _CODE.search(driver.headshot_url or "")
    if match:
        return match.group(1)
    first = _ascii(driver.first_name or "").strip()
    last = _ascii(driver.last_name or "").strip()
    if len(first) < 3 or len(last) < 3:
        return None
    return f"{first[:3]}{last[:3]}01".lower()


def _season_photo(year: int, slug: str, code: str, crop: str) -> str:
    folder = f"common/f1/{year}/{slug}/{code}"
    return f"{_F1_CLOUD}/{crop}/{_VERSION}/{folder}/{year}{slug}{code}right.webp"


def candidates(driver: Driver, year: int) -> list[tuple[int, str]]:
    """(season, folder) pairs to try, nearest season first, all under the same team name."""
    lineage = teams.seasons(teams.team_key(driver.team_name)) or {year: driver.team_name}
    same_name = [y for y, name in lineage.items() if name == driver.team_name] or [year]
    out: list[tuple[int, str]] = []
    for y in sorted(same_name, key=lambda y: (abs(y - year), y < year)):
        slug = _slug(driver.team_name, y)
        if slug:
            out.append((y, slug))
    return out


async def _has(http: httpx.AsyncClient, url: str) -> bool:
    async def check() -> bool:
        try:
            res = await http.head(url, timeout=10)
        except httpx.HTTPError:
            return False
        return res.status_code == 200

    if url not in _exists:
        _exists[url] = asyncio.ensure_future(check())
    return await _exists[url]


async def _resolve(http: httpx.AsyncClient, driver: Driver, year: int) -> None:
    code = _code(driver)
    if not code:
        return
    for y, slug in candidates(driver, year):
        if await _has(http, _season_photo(y, slug, code, "q_auto")):
            driver.headshot_url = _season_photo(y, slug, code, _CROP)
            return


async def resolve(http: httpx.AsyncClient, drivers: list[Driver], year: int) -> None:
    """Point each driver at their photo for this season and team, then remember it."""
    await asyncio.gather(*(_resolve(http, d, year) for d in drivers))
    remember(drivers, year)


def remember(drivers: list[Driver], year: int) -> None:
    for d in drivers:
        if d.headshot_url:
            _known[(_key(d), year)] = d.headshot_url


def headshot(driver: Driver, year: int | None = None) -> str | None:
    """The driver's portrait, borrowing one seen in another session of the same season.
    Never from another season: that could be a different team's suit."""
    if driver.headshot_url:
        return driver.headshot_url
    return _known.get((_key(driver), year)) if year is not None else None
