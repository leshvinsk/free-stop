# Free Stop

[![CI](https://github.com/leshvinsk/free-stop/actions/workflows/ci.yml/badge.svg)](https://github.com/leshvinsk/free-stop/actions/workflows/ci.yml)

A FastAPI + Vue 3 platform that scores F1 pit-stop timing luck across the 2024, 2025 and 2026 seasons. Every stop is benchmarked against the race's green-flag baseline cost — a stop taken under a safety car costs near zero, so it scores as a big saving.

## Table of Contents

- [Overview](#overview)
- [Core Features](#core-features)
- [How Scoring Works](#how-scoring-works)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [Running Checks](#running-checks)
- [Deployment](#deployment)
- [Automated Data](#automated-data)
- [Data Sources](#data-sources)
- [Operational Notes](#operational-notes)
- [Contributing](#contributing)
- [Project Status](#project-status)
- [License](#license)

## Overview

Free Stop answers a simple question after every F1 race: who got lucky in the pits?

Drivers who pit under a safety car or red flag save significant time compared to drivers who pit under green-flag conditions. Free Stop quantifies that difference for every driver at every race, then aggregates it across the season so you can see who has benefited most from pit timing luck versus who has been unlucky.

Race execution — how fast the pit crew actually changed the tyres — is scored separately from timing luck, so the two effects are never conflated.

## Core Features

### Race View
- Full driver ranking by pit-stop timing luck per race
- Stop conditions displayed per driver — SC, VSC, Red Flag, or Green
- Pit crew execution table ranked by time won or lost against the normal stop
- Race timeline showing safety car periods and pit stop moments
- Circuit map, weather summary and race statistics

### Driver View
- Season-long luck and execution breakdown race by race
- Cumulative chart showing luck across the season
- DNF, DNS and DSQ races shown clearly with crew time marked as not applicable

### Team View
- Combined driver luck and crew execution per team
- Season progression chart
- Interactive car diagram with component specifications
- Pit crew performance statistics including best, worst and clean races

### Leaderboard
- Full season ranking for all drivers
- Sortable by luck per race or total season luck

### Methodology
- Step-by-step explanation of how scores are calculated
- Glossary of all labels and values shown in the interface
- Known limitations documented

## How Scoring Works

Each pit stop is classified by the flag condition on the out-lap:

```text
GREEN   — Normal racing. The stop costs the full time lost to the field.
SC      — Safety car. The field slows, so the stop costs far less.
VSC     — Virtual safety car. Cheaper than SC, but less saving.
RED     — Red flag. Everyone stops and changes tyres for free.
```

The luck delta for a single stop is:

```text
stop_delta = baseline_pit_loss − actual_pit_loss_for_this_stop
```

Where `baseline_pit_loss` is the trimmed mean of all green-flag stops in that race (top and bottom 10% removed to exclude outliers such as penalties and damaged cars).

A driver's race luck is the sum of all their stop deltas. The field average is then subtracted so only *relative* luck counts — if every driver was equally lucky, nobody scores.

```text
race_luck(driver) = sum(stop_delta) − field_average
```

Execution is scored separately as the difference between the actual pit lane time and the race's normal stop, independent of flag conditions.

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 · FastAPI · uvicorn |
| Data fetching | httpx · tenacity (retry/backoff) |
| Validation | Pydantic v2 |
| Frontend | Vue 3 · TypeScript · Vite |
| Cache | Redis (primary) · disk pickle (fallback) |
| Hosting | Render (free tier) |
| CI | GitHub Actions |
| Linting | ruff · mypy · ESLint · Prettier |
| Testing | pytest · Vitest |

## Project Structure

```text
free-stop/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── pyproject.toml             # Dependencies, ruff, mypy, pytest config
│   ├── app/
│   │   ├── routers/               # season, race, driver, team endpoints
│   │   ├── openf1/                # OpenF1 API client and Pydantic schemas
│   │   ├── scoring/               # Lap classification, formula, pipeline
│   │   ├── models.py              # API response shapes
│   │   ├── store.py               # Stale-while-revalidate session store
│   │   ├── score_cache.py         # Redis + disk score persistence
│   │   ├── redis_cache.py         # Redis wrapper with graceful fallback
│   │   ├── headshots.py           # Season-accurate driver photo resolution
│   │   └── teams.py               # Team lineages and key mapping
│   └── scripts/
│       └── scrape_teams.py        # formula1.com team data scraper
├── frontend/
│   ├── src/
│   │   ├── views/                 # LeaderboardView, RaceView, DriverView, TeamView
│   │   ├── components/            # TimingTower, CarAnnotated, RaceTimeline, etc.
│   │   ├── composables/           # useApi typed fetch wrapper
│   │   ├── data/                  # teamInfo.ts, teams_scraped.json
│   │   ├── types/                 # TypeScript interfaces matching backend models
│   │   └── utils/                 # format, identity, stories
│   ├── vite.config.ts             # API proxy for local dev
│   └── package.json
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Lint, type-check, test on every push
│       ├── sync-teams.yml         # Daily team data scrape from formula1.com
│       └── keep-warm.yml          # Ping API every 10 min to prevent spin-down
├── render.yaml                    # Render IaC — API, UI and Redis as code
└── .pre-commit-config.yaml
```

## Getting Started

### Prerequisites

- Python 3.12 or newer
- Node 22 or newer
- pip

### Installation

Clone the repository:

```bash
git clone https://github.com/leshvinsk/free-stop.git
cd free-stop
```

Install backend dependencies:

```bash
cd backend
pip install -e ".[dev]"
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

## Environment Variables

The backend reads the following environment variables. None are required for local development — the defaults work out of the box.

```env
# Logging level (DEBUG, INFO, WARNING)
LOG_LEVEL=INFO

# Redis connection string — if unset, the disk cache is used instead
REDIS_URL=redis://localhost:6379

# Contact email sent in Wikimedia Commons HTTP requests (their robot policy requires one)
WIKIMEDIA_CONTACT=your@email.com

# Frontend: base URL of the deployed API (used at build time by Vite)
VITE_API_BASE_URL=http://localhost:8000
```

Create a `.env` file in `backend/` for local overrides. Do not commit real credentials.

## Running the Application

Start the backend:

```bash
cd backend
uvicorn main:app --reload
# API runs at http://localhost:8000
# OpenAPI docs at http://localhost:8000/docs
```

Start the frontend (new terminal):

```bash
cd frontend
npm run dev
# Frontend runs at http://localhost:5173
```

The frontend proxies all `/api` requests to the local backend automatically via `vite.config.ts` — no CORS configuration is needed during development.

## Running Checks

Backend:

```bash
cd backend
ruff check .
ruff format --check .
mypy .
pytest -v
```

Frontend:

```bash
cd frontend
npm run type-check
npm run lint
npm run format -- --check
npm test
npx vite build
```

All checks run automatically on every push via GitHub Actions.

## Deployment

The repository includes a `render.yaml` that defines all three Render services as code:

| Service | Type | Purpose |
|---|---|---|
| `free-stop-api` | Python web service | FastAPI backend |
| `free-stop-ui` | Static site | Vue 3 frontend |
| `free-stop-redis` | Redis | Score cache |

Connect the repository to Render once — every push to `main` triggers an automatic redeploy of both services. The Redis instance and its connection string are wired automatically via `render.yaml`.

## Automated Data

Two GitHub Actions workflows keep the site current without any manual work:

**Sync team data** (`sync-teams.yml`)

Runs daily at 06:00 UTC and hourly on Thursday through Sunday (race weekends). Scrapes all team pages on formula1.com and, when principals, chassis names or power units change, opens a pull request updating `frontend/src/data/teams_scraped.json`. Nothing reaches the live site until a maintainer approves that pull request. Verified values in `teamInfo.ts` always take priority over the scraped data — the scraper only fills in gaps for new seasons or new teams.

If fewer than 8 of 11 teams are scraped successfully, the workflow opens a GitHub issue labelled `data-alert` so the failure does not go unnoticed.

**Keep warm** (`keep-warm.yml`)

Pings `https://free-stop-api.onrender.com/health` every 10 minutes. Render's free tier spins down a service after 15 minutes of inactivity. The 10-minute interval provides a 5-minute safety buffer against scheduling delays.

## Data Sources

| Source | Used for |
|---|---|
| [OpenF1](https://openf1.org) | Pit stops, lap times, race control messages, driver data |
| [formula1.com](https://www.formula1.com/en/teams) | Team principals, chassis, power units, base, founded year |
| Formula 1 media CDN | Driver portraits, team logos, car images, circuit outlines |
| [Jolpica](https://jolpica.com) | Driver nationalities for flag display |

## Operational Notes

- `REDIS_URL` is optional. The backend degrades gracefully to the disk cache if Redis is unavailable.
- Scores for completed races are cached permanently. Only sessions within 24 hours of completion are re-scored on each request.
- The disk cache is ephemeral on Render — it is cleared on every redeploy. Redis survives redeploys.
- `main` is protected by the ruleset in `.github/rulesets/protect-main.json`: pull request only, squash merge, green CI and code owner approval.
- The `sync-teams.yml` workflow needs **Allow GitHub Actions to create and approve pull requests** enabled under Settings → Actions → General.
- Dependabot opens grouped dependency updates every Monday.

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards. Questions and ideas go in [Discussions](https://github.com/leshvinsk/free-stop/discussions).

To report a security vulnerability, follow [SECURITY.md](SECURITY.md). Please don't open a public issue.

## Project Status

Actively developed. The 2024 and 2025 seasons are fully scored. The 2026 season scores live as each race completes.

## License

The source code is released under the [MIT License](LICENSE).

The license covers this project's code only. F1, FORMULA 1 and related marks, and the team logos, driver photos and car images loaded from the Formula 1 media CDN, belong to their respective owners. Free Stop is an unofficial fan project and is not associated with Formula 1 or the FIA.
