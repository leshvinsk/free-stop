"""
Team identity across seasons. OpenF1 only gives a team's name for that season, and several
teams were renamed: RB → Racing Bulls, Kick Sauber → Audi. Each
lineage gets one stable key so a team page can step through its seasons.
"""

import re

# Free Stop covers 2024 onwards
FIRST_SEASON = 2024

# Key → the name the team raced under each season
LINEAGES: dict[str, dict[int, str]] = {
    "red-bull-racing": {y: "Red Bull Racing" for y in (2024, 2025, 2026)},
    "mercedes": {y: "Mercedes" for y in (2024, 2025, 2026)},
    "ferrari": {y: "Ferrari" for y in (2024, 2025, 2026)},
    "mclaren": {y: "McLaren" for y in (2024, 2025, 2026)},
    "aston-martin": {y: "Aston Martin" for y in (2024, 2025, 2026)},
    "alpine": {y: "Alpine" for y in (2024, 2025, 2026)},
    "williams": {y: "Williams" for y in (2024, 2025, 2026)},
    "haas": {y: "Haas F1 Team" for y in (2024, 2025, 2026)},
    "racing-bulls": {2024: "RB", 2025: "Racing Bulls", 2026: "Racing Bulls"},
    "audi": {2024: "Kick Sauber", 2025: "Kick Sauber", 2026: "Audi"},
    "cadillac": {2026: "Cadillac"},
}

_BY_NAME = {name: key for key, seasons in LINEAGES.items() for name in seasons.values()}


def team_key(team_name: str) -> str:
    """Stable key for a team name. Unknown names (a future team) get a slug of their own."""
    return _BY_NAME.get(team_name) or re.sub(r"[^a-z0-9]+", "-", team_name.lower()).strip("-")


def seasons(key: str) -> dict[int, str]:
    return LINEAGES.get(key, {})
