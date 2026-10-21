"""
Freely licensed race photos from Wikimedia Commons. Race-day photos from F1's own channels are
copyrighted, so these are the closest legal match: the race weekend's own Commons category when
there is one, otherwise the Grand Prix's general category (other years, same circuit).
Every photo carries its author and licence, which the licences require us to show.
"""

import logging
import os
import re
from html import unescape
from typing import Any

import httpx

from app.models import RacePhoto, RacePhotos
from app.openf1.schemas import Session

logger = logging.getLogger(__name__)

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia's robot policy rejects API clients whose User-Agent has no contact details.
CONTACT = os.getenv("WIKIMEDIA_CONTACT", "leshvinsk@icloud.com")
HEADERS = {"User-Agent": f"FreeStop/1.0 ({CONTACT}) httpx/{httpx.__version__}"}
MAX_PHOTOS = 8
MAX_SUBCATEGORIES = 4
MIN_WIDTH = 1000
MIN_ASPECT = 1.25  # landscape only, to fit the slider
YEAR_PREFIX = re.compile(r"^(19|20)\d\d ")


async def find_photos(race_name: str, session: Session) -> RacePhotos:
    async with httpx.AsyncClient(timeout=15, headers=HEADERS) as http:
        for category, scope in (
            (f"{session.year} {race_name}", "weekend"),
            (race_name, "circuit"),
        ):
            try:
                photos = await _from_category(http, category)
            except httpx.HTTPError:
                logger.warning("Commons lookup failed for %s", category)
                continue
            if photos:
                return RacePhotos(scope=scope, category=category, photos=photos[:MAX_PHOTOS])
    return RacePhotos(scope="none", category=None, photos=[])


async def _from_category(http: httpx.AsyncClient, category: str) -> list[RacePhoto]:
    photos = await _files(http, category)
    if len(photos) < MAX_PHOTOS:
        # Many weekends keep their pictures in sub-categories (by day, team, session…), and a
        # Grand Prix's own category is split by year: newest first, so the photos look current
        subs = await _subcategories(http, category)
        yearly = sorted((c for c in subs if YEAR_PREFIX.match(c)), reverse=True)
        for sub in (yearly or subs)[:MAX_SUBCATEGORIES]:
            photos += await _files(http, sub)
            if len(photos) >= MAX_PHOTOS:
                break
    # The same file can sit in several sub-categories
    return list({p.url: p for p in photos}.values())


async def _query(http: httpx.AsyncClient, params: dict[str, Any]) -> dict[str, Any]:
    response = await http.get(COMMONS_API, params={"action": "query", "format": "json", **params})
    response.raise_for_status()
    return response.json()  # type: ignore[no-any-return]


async def _subcategories(http: httpx.AsyncClient, category: str) -> list[str]:
    data = await _query(
        http,
        {
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmtype": "subcat",
            "cmlimit": 500,
        },
    )
    return [
        m["title"].removeprefix("Category:")
        for m in data.get("query", {}).get("categorymembers", [])
    ]


async def _files(http: httpx.AsyncClient, category: str) -> list[RacePhoto]:
    data = await _query(
        http,
        {
            "generator": "categorymembers",
            "gcmtitle": f"Category:{category}",
            "gcmtype": "file",
            "gcmlimit": 50,
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": 1280,
            "iiextmetadatafilter": "Artist|LicenseShortName|DateTimeOriginal|ObjectName",
        },
    )
    pages = sorted(
        data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("title", "")
    )
    photos: list[RacePhoto] = []
    for page in pages:
        info = (page.get("imageinfo") or [{}])[0]
        width, height = info.get("width", 0), info.get("height", 1)
        if info.get("mime") != "image/jpeg" or width < MIN_WIDTH or width / height < MIN_ASPECT:
            continue
        meta = info.get("extmetadata", {})
        photos.append(
            RacePhoto(
                url=info.get("thumburl") or info["url"],
                page_url=info.get("descriptionurl", ""),
                caption=_caption(page.get("title", ""), meta),
                author=_text(meta, "Artist") or "Unknown",
                license=_text(meta, "LicenseShortName") or "See source",
                taken=(_text(meta, "DateTimeOriginal") or "")[:10] or None,
            )
        )
    return photos


def _text(meta: dict[str, Any], field: str) -> str:
    raw = str(meta.get(field, {}).get("value", ""))
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", raw))).strip()


def _caption(title: str, meta: dict[str, Any]) -> str:
    name = _text(meta, "ObjectName") or title.removeprefix("File:").rsplit(".", 1)[0]
    # Camera serials like "(028A7885)" or "DSC_0123" add nothing
    name = re.sub(r"\s*\((?:[0-9A-Z_]{5,}|\d{6,})\)", "", name)
    return re.sub(r"\s+", " ", name.replace("_", " ")).strip()
