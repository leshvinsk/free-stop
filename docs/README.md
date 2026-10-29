<p align="center">
  <img src="assets/logo.svg" alt="Free Stop" width="80" />
</p>

# Free Stop

[![CI](https://github.com/leshvinsk/free-stop/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/leshvinsk/free-stop/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../LICENSE)

Free Stop is an analytics platform that measures how much of a Formula 1 driver's race result was shaped by pit stop timing. It covers the 2024, 2025 and 2026 seasons and benchmarks every pit stop against the green flag baseline cost of that race. A stop made under a safety car costs far less than a stop made in normal racing, and Free Stop quantifies that saving for every driver, team and race.

## Table of Contents

- [Overview](#overview)
- [Core Features](#core-features)
- [Scoring Methodology](#scoring-methodology)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [Quality Checks](#quality-checks)
- [Branching and Release Model](#branching-and-release-model)
- [Deployment](#deployment)
- [Automated Workflows](#automated-workflows)
- [Data Sources](#data-sources)
- [Operational Notes](#operational-notes)
- [Contributing](#contributing)
- [Support](#support)
- [Security](#security)
- [Project Status](#project-status)
- [License](#license)

## Overview

Every Formula 1 race raises the same question: which drivers gained or lost time because of when they stopped, rather than how well they raced? Free Stop answers that question with a consistent, data driven method.

A pit stop under green flag conditions costs a driver the full time lost to the field. A pit stop under a safety car, a virtual safety car or a red flag costs considerably less, because the rest of the field is slowed or stopped at the same time. Free Stop calculates that difference for every stop, removes the effect that all drivers shared equally, and aggregates the result across the season.

Pit crew performance is measured separately from timing. The speed of the stop itself is reported as crew execution, so that a fast crew and a fortunate safety car are never confused with one another.

## Core Features

### Race Analysis

- Ranking of every driver by pit stop timing benefit for the selected race
- Stop conditions shown for each driver, separated into safety car, virtual safety car, red flag and green flag stops
- Pit crew execution ranking based on time gained or lost against the normal stop for that race
- Race timeline showing neutralisation periods alongside each pit stop
- Circuit map, weather summary and headline race statistics

### Driver Analysis

- Race by race breakdown of timing benefit and crew execution across the season
- Cumulative season chart
- Clear handling of retirements, non starts and disqualifications, which are excluded from timing scores while their completed stops still count for the crew

### Team Analysis

- Combined timing benefit and crew execution for both cars
- Season progression chart
- Interactive car diagram with component specifications
- Pit crew statistics, including best race, worst race and clean races

### Season Leaderboard

- Full season ranking of all drivers
- Ranking by average time saved per race

### Methodology Guide

- Step by step explanation of how every score is calculated
- Glossary of every label and value shown in the interface
- Documented limitations of the method

## Scoring Methodology

### Stop Classification

Each pit stop is classified by the race condition in force when the driver left the pit lane.

| Condition | Meaning | Effect on stop cost |
|---|---|---|
| GREEN | Normal racing | Full time lost to the field |
| SC | Safety car deployed | Substantially reduced |
| VSC | Virtual safety car deployed | Reduced, but less than under a safety car |
| RED | Race suspended | Tyre change is effectively free |

### Baseline

The baseline for a race is the trimmed mean time lost by all green flag stops in that race. The fastest and slowest 10 percent of stops are removed so that penalties, damage and unusual stops do not distort the result. At least three green flag stops are required for a baseline to be calculated.

### Calculation

The benefit of a single stop is the difference between the baseline and the time that stop actually cost:

```text
stop_benefit = baseline_pit_loss - actual_pit_loss
```

A driver's race score is the sum of their stop benefits, less the field average for that race:

```text
race_score = sum(stop_benefit) - field_average
```

Subtracting the field average ensures that only relative advantage is measured. If every driver benefited equally from a safety car, no driver gains a score from it.

### Accuracy

The inputs are official timing data, accurate to the millisecond, but the cost of each stop is an estimate. It compares a driver's in-lap and out-lap with the pace of the rest of the field at that moment, so traffic, tyre condition and fuel load can move it by fractions of a second. There is no official measure of pit stop luck to validate against, so the scores are the best estimate the timing data allows.

Large differences, such as a stop under a safety car against a stop in normal racing, are worth ten seconds or more and are measured reliably. Drivers a few tenths of a second per race apart should be read as level. Early in a season a single safety car can move a driver's average by a couple of seconds, which is why the luckiest and unluckiest drivers must have been scored in at least a third of the rounds, and at least three.

### Crew Execution

Crew execution is calculated independently as the difference between a stop's pit lane time and the normal pit lane time for that race. Served penalties are excluded, so crews are not penalised for time they were required to wait. Stops completed before a retirement or disqualification still count, because the crew performed them as normal. A stop with no normal pit lane time to compare, such as a tyre change under a red flag, a drive through the pit lane behind the safety car or a repair, has no crew score, and the race page lists the reason.

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Data access | httpx, Tenacity for retry and backoff |
| Validation | Pydantic v2 |
| Frontend | Vue 3, TypeScript, Vite |
| Caching | Upstash Redis as the primary store, local disk as the fallback |
| Hosting | Render |
| Continuous integration | GitHub Actions |
| Code quality | Ruff, mypy, ESLint, Prettier |
| Testing | pytest, Vitest |

## System Architecture

```text
Browser
   |
   v
Vue 3 frontend (Render static site)
   |
   | HTTPS
   v
FastAPI backend (Render web service)
   |
   +--> Redis score cache --> cached result returned
   |
   +--> OpenF1 API --> laps, pit stops, race control
              |
              v
        Scoring pipeline --> result cached and returned
```

Completed races are scored once and cached. Races that finished recently are refreshed until OpenF1 has published complete data.

## Project Structure

```text
free-stop/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                   # Backend and frontend checks
│   │   ├── pr-policy.yml            # Target branch, branch name and title rules
│   │   ├── release-pr.yml           # Promotes approved changes from dev to main
│   │   ├── link-issue.yml           # Fills in the Closes reference from the branch name
│   │   ├── close-issues.yml         # Closes linked issues when a pull request merges into dev
│   │   ├── sync-teams.yml           # Team data synchronisation from formula1.com
│   │   └── keep-warm.yml            # Health check that prevents idle spin down
│   ├── ISSUE_TEMPLATE/              # Bug report, data correction and feature request forms
│   ├── DISCUSSION_TEMPLATE/         # Ideas form
│   ├── rulesets/                    # Branch and tag protection definitions
│   ├── scripts/
│   │   └── sync-with-dev.sh         # Stash, fetch, rebase onto dev, stash pop
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   └── pull_request_template.md
├── applications/
│   ├── render.yaml                  # Render Blueprint for the API, UI and Redis
│   └── .pre-commit-config.yaml      # Optional local formatting hooks
├── backend/
│   ├── main.py                      # FastAPI application entry point
│   ├── pyproject.toml               # Dependencies and tool configuration
│   ├── app/
│   │   ├── routers/                 # Season, race, driver and team endpoints
│   │   ├── openf1/                  # OpenF1 client and schemas
│   │   ├── scoring/                 # Classification, formula and pipeline
│   │   ├── models.py                # API response models
│   │   ├── store.py                 # Session store with background refresh
│   │   ├── score_cache.py           # Score persistence across restarts
│   │   ├── redis_cache.py           # Redis client with graceful fallback
│   │   ├── headshots.py             # Season accurate driver portraits
│   │   └── teams.py                 # Team lineages and identifiers
│   ├── scripts/
│   │   └── scrape_teams.py          # formula1.com team data scraper
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── views/                   # Leaderboard, race, driver, team and methodology pages
│   │   ├── components/              # Shared interface components
│   │   ├── composables/             # Typed API access
│   │   ├── data/                    # Verified and synchronised team data
│   │   ├── types/                   # TypeScript models matching the API
│   │   └── utils/                   # Formatting and identity helpers
│   ├── vite.config.ts
│   └── package.json
├── docs/
│   ├── README.md
│   ├── CONTRIBUTING.md
│   ├── CODE_OF_CONDUCT.md
│   ├── GOVERNANCE.md
│   ├── SECURITY.md
│   └── SUPPORT.md
└── LICENSE
```

## Getting Started

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.12 or later |
| Node.js | 22 or later |
| Git | Any recent version |

### Installation

Clone the repository. The default branch is `dev`, which contains the latest reviewed changes.

```bash
git clone https://github.com/leshvinsk/free-stop.git
cd free-stop
```

Install the backend dependencies:

```bash
cd backend
pip install -e ".[dev]"
```

Install the frontend dependencies:

```bash
cd frontend
npm install
```

## Environment Variables

No environment variables are required for local development. The defaults are suitable for running the application on a single machine.

| Variable | Used by | Purpose | Default |
|---|---|---|---|
| `LOG_LEVEL` | Backend | Logging verbosity: `DEBUG`, `INFO` or `WARNING` | `INFO` |
| `REDIS_URL` | Backend | Redis connection string. When unset, scores are cached on local disk | Not set |
| `WIKIMEDIA_CONTACT` | Backend | Contact address sent to Wikimedia Commons, as required by its robot policy | Maintainer address |
| `VITE_API_BASE_URL` | Frontend | Base URL of the API, applied at build time | Local proxy |

Local overrides may be placed in `backend/.env`. Real credentials must never be committed.

## Running the Application

Start the backend:

```bash
cd backend
uvicorn main:app --reload
```

The API is available at `http://localhost:8000` and its interactive documentation at `http://localhost:8000/docs`.

Start the frontend in a second terminal:

```bash
cd frontend
npm run dev
```

The interface is available at `http://localhost:5173`. Requests to `/api` are forwarded to the local backend by `vite.config.ts`, so no cross origin configuration is needed.

## Quality Checks

The same checks run in continuous integration on every pull request and must pass before any change can be merged.

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

Optional pre-commit hooks apply the formatters automatically before each commit:

```bash
pip install pre-commit
pre-commit install --config applications/.pre-commit-config.yaml
```

## Branching and Release Model

Free Stop uses two long lived branches.

| Branch | Purpose | Receives changes from | Merge method |
|---|---|---|---|
| `dev` | Integration branch and default branch | Contributor branches, one per issue | Squash merge |
| `main` | Production branch, deployed to the live site | `dev` only | Merge commit |

```text
issue #42
   |
   v
feat/42-tyre-compound-timeline  (contributor branch on a fork)
   |
   |  pull request, review, checks, squash merge
   v
dev
   |
   |  release pull request, merged automatically once checks pass
   v
main  -->  deployed to production
```

Every change starts as an issue, is developed on its own branch, and is reviewed in a pull request against `dev`. Once a maintainer approves and merges a pull request into `dev`, a release pull request from `dev` to `main` is opened automatically and merges itself as soon as the checks pass, which deploys the change. The complete process is described in [CONTRIBUTING.md](CONTRIBUTING.md) and the approval rules in [GOVERNANCE.md](GOVERNANCE.md).

## Deployment

`applications/render.yaml` is a Render Blueprint that defines both production services. The cache is an Upstash Redis database in Frankfurt, which keeps its data across restarts.

| Service | Type | Purpose |
|---|---|---|
| `free-stop-api` | Python web service | FastAPI backend |
| `free-stop-ui` | Static site | Vue 3 frontend |

When the Blueprint is created in Render, its path must be set to `applications/render.yaml`. Both web services deploy from `main` only, so changes reach production only through an approved pull request into `dev` followed by the automated release.

## Automated Workflows

| Workflow | Trigger | Purpose |
|---|---|---|
| CI | Every pull request into `dev`, and pushes to `dev` and `main` | Runs all backend and frontend checks |
| PR policy | Every pull request into `dev`, except the data sync's | Verifies the target branch, branch name, title format, and that the branch is rebased on the latest `dev` |
| Release to main | Every change to `dev` | Opens the release pull request from `dev` to `main` and merges it automatically once checks pass |
| Link issue | Every pull request into `dev` | Fills in `Closes #<issue>` from the issue number in the branch name |
| Close linked issues | Every change to `dev` | Closes the issues named by `Closes #<issue>` in each merged pull request |
| Sync team data | Daily at 06:00 UTC, and hourly from Thursday to Sunday | Opens and merges a pull request when formula1.com team data changes and the frontend checks pass |
| Keep warm | Every 10 minutes | Prevents the hosted API from idling |
| Dependabot | Weekly on Monday | Opens grouped dependency updates against `dev` |

### Team Data Synchronisation

The synchronisation workflow reads every team page on formula1.com and compares the result with `frontend/src/data/teams_scraped.json`. When the data has changed, it runs the frontend checks against the new data and opens a pull request against `dev`. If the checks pass, the pull request merges automatically and the release workflow promotes it to `main`. If they fail, the pull request stays open for review and a `data-alert` issue is opened. Verified values in `frontend/src/data/teamInfo.ts` always take precedence over synchronised values.

If fewer than eight of the eleven teams can be read, no data is written and the workflow opens an issue labelled `data-alert` so that the failure is investigated promptly.

### Keep Warm

Render's free tier stops a service after 15 minutes without traffic. The keep warm workflow requests the health endpoint every 10 minutes, which leaves a margin of 5 minutes for scheduling delays.

## Data Sources

| Source | Data provided |
|---|---|
| [OpenF1](https://openf1.org) | Pit stops, lap times, race control messages and driver details |
| [formula1.com](https://www.formula1.com/en/teams) | Team principals, chassis, power units, team bases and first entry years |
| Formula 1 media service | Driver portraits, team logos, car images and circuit outlines |
| [Jolpica](https://jolpica.com) | Driver nationalities |

## Operational Notes

- `REDIS_URL` is optional. If Redis is unavailable, the backend continues to operate using the disk cache.
- Completed races are cached permanently. Races within 24 hours of their finish are refreshed until OpenF1 data is complete.
- The disk cache on Render is cleared on each deployment, whereas Upstash Redis keeps scores, circuit maps, weather and photos for finished races, and the calendars of finished seasons, across deployments and restarts. Each process checks its own memory first, so Redis is only read after a restart.
- Redis keys carry a fingerprint of the code that builds them, so a code change rebuilds them. Every read pushes a key's expiry back 60 days, so entries in use never expire and entries from older code expire on their own. This needs the `GETEX` command on the Redis user; without it, reads still work and keys expire 60 days after they were written.
- `REDIS_URL` is set in the Render dashboard, not in `render.yaml`, because it contains the Upstash password. It must use the `rediss://` scheme.
- If Redis cannot be reached, the backend retries the connection every 60 seconds.
- Branch protection is defined in `.github/rulesets/` and applied through the repository settings.
- The release workflow requires the repository setting that allows GitHub Actions to create and approve pull requests.
- The synchronisation workflow acts as the `free-stop-data-sync` GitHub App, the only actor allowed to bypass review on `dev`. It needs the `DATA_SYNC_APP_CLIENT_ID` repository variable and the `DATA_SYNC_APP_PRIVATE_KEY` repository secret.

## Contributing

Contributions are welcome from everyone. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before starting work, and observe the [Code of Conduct](CODE_OF_CONDUCT.md) in all project spaces. The roles and approval rules of the project are described in [GOVERNANCE.md](GOVERNANCE.md).

## Support

Guidance on asking questions, reporting problems and requesting features is available in [SUPPORT.md](SUPPORT.md).

## Security

Security vulnerabilities must be reported privately as described in [SECURITY.md](SECURITY.md). Please do not disclose them in public issues, discussions or pull requests.

## Project Status

Free Stop is under active development. The 2024 and 2025 seasons are fully scored, and the 2026 season is scored as each race is completed.

## License

The source code is released under the [MIT License](../LICENSE).

The license applies to the source code of this project only. F1, FORMULA 1 and related marks, together with the team logos, driver portraits and car images served by the Formula 1 media service, are the property of their respective owners. Free Stop is an independent, unofficial project and is not affiliated with, endorsed by or associated with Formula 1 or the FIA.
