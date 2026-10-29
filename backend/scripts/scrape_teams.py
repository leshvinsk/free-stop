"""
Scrapes the current season's team data from formula1.com.
Outputs: frontend/src/data/teams_scraped.json

Usage (from repo root):
    python backend/scripts/scrape_teams.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

# Our internal team keys → formula1.com URL slugs
F1_SLUGS: dict[str, str] = {
    "mercedes": "mercedes",
    "red-bull-racing": "red-bull-racing",
    "ferrari": "ferrari",
    "mclaren": "mclaren",
    "aston-martin": "aston-martin",
    "alpine": "alpine",
    "williams": "williams",
    "racing-bulls": "racing-bulls",
    "haas": "haas",
    "audi": "audi",
    "cadillac": "cadillac",
}

# Longest-match first so "Red Bull Ford" beats "Red Bull"
_PU_MAKERS = [
    "Red Bull Ford",
    "Mercedes-AMG",
    "Mercedes",
    "Ferrari",
    "Honda RBPT",
    "Honda",
    "Renault",
    "Audi",
]

_BASE_URL = "https://www.formula1.com/en/teams"
_HEADERS = {
    "User-Agent": "FreeStop/1.0 (leshvinsk@gmail.com)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}
_DELAY = 2.5  # seconds between requests (polite crawling)


def _extract_pu_maker(full_name: str) -> str:
    """Return just the manufacturer from a full PU name, e.g. "Honda RBPTH003" → "Honda"."""
    for maker in _PU_MAKERS:
        if full_name.lower().startswith(maker.lower()):
            return maker
    # Fallback: leading capitalised words before a digit
    m = re.match(r"^((?:[A-Z][a-zA-Z-]+(?: (?=[A-Z]))?)+)", full_name)
    return m.group(1).strip() if m else full_name


def _bs_parse(html: str) -> dict[str, str]:
    """Primary parser — extracts dt/dd field pairs."""
    soup = BeautifulSoup(html, "lxml")
    out: dict[str, str] = {}
    for dt in soup.find_all("dt"):
        label = dt.get_text(strip=True).lower()
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue
        value = dd.get_text(strip=True)
        if "team chief" in label or "team principal" in label:
            out["principal"] = value
        elif label == "base":
            out["base"] = value
        elif label == "chassis":
            out["chassis"] = value
        elif "power unit" in label:
            out["power_unit"] = _extract_pu_maker(value)
        elif "first team entry" in label:
            out["founded"] = value
    return out


def _regex_parse(html: str) -> dict[str, str]:
    """Fallback parser — used when BeautifulSoup finds nothing."""
    out: dict[str, str] = {}
    pairs = [
        ("principal", r"[Tt]eam\s+[Cc]hief[^>]*>[^<]*<[^>]*>([^<]+)<"),
        ("base", r"<dt[^>]*>\s*Base\s*</dt>\s*<dd[^>]*>([^<]+)<"),
        ("chassis", r"<dt[^>]*>\s*Chassis\s*</dt>\s*<dd[^>]*>([^<]+)<"),
        ("power_unit", r"[Pp]ower\s+[Uu]nit[^>]*>[^<]*<[^>]*>([^<]+)<"),
        ("founded", r"[Ff]irst\s+[Tt]eam\s+[Ee]ntry[^>]*>[^<]*<[^>]*>([^<]+)<"),
    ]
    for key, pattern in pairs:
        m = re.search(pattern, html)
        if m:
            value = m.group(1).strip()
            if key == "power_unit":
                value = _extract_pu_maker(value)
            out[key] = value
    return out


def _scrape_team(client: httpx.Client, key: str, slug: str) -> dict[str, str] | None:
    url = f"{_BASE_URL}/{slug}"
    try:
        r = client.get(url, headers=_HEADERS, follow_redirects=True, timeout=20)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"  HTTP error for {key}: {exc}", file=sys.stderr)
        return None

    data = _bs_parse(r.text)
    if len(data) < 3:
        print(
            f"  Primary parser weak for {key} ({len(data)} fields), trying regex fallback",
            file=sys.stderr,
        )
        fallback = _regex_parse(r.text)
        # Merge: primary fields + any extra from fallback
        data = {**fallback, **data}

    if len(data) < 3:
        print(f"  Both parsers failed for {key} ({len(data)} fields)", file=sys.stderr)
        return None

    print(f"  ✓ {key}: {data.get('chassis', '?')} / {data.get('power_unit', '?')}")
    return data


def scrape() -> dict[str, dict[str, str]]:
    print("Scraping formula1.com team pages…")
    results: dict[str, dict[str, str]] = {}

    with httpx.Client() as client:
        for i, (key, slug) in enumerate(F1_SLUGS.items()):
            if i > 0:
                time.sleep(_DELAY)
            print(f"[{i + 1}/{len(F1_SLUGS)}] {key}")
            data = _scrape_team(client, key, slug)
            if data:
                results[key] = data

    print(f"\nScraped {len(results)}/{len(F1_SLUGS)} teams")
    return results


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent.parent
    out_path = repo_root / "frontend" / "src" / "data" / "teams_scraped.json"

    teams = scrape()

    # Cadillac may not appear yet; require at least 8 of 11. Partial data is never written.
    if len(teams) < 8:
        print(f"ERROR: Only {len(teams)} teams scraped, expected ≥8", file=sys.stderr)
        sys.exit(1)

    year = date.today().year
    if out_path.exists():
        previous = json.loads(out_path.read_text(encoding="utf-8"))
        # The timestamp alone must not produce a change, or every run would open a PR
        if previous.get("year") == year and previous.get("teams") == teams:
            print("No changes ✓")
            return

    output = {"year": year, "scraped_at": datetime.now(UTC).isoformat(), "teams": teams}
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated {out_path} ✓")


if __name__ == "__main__":
    main()
