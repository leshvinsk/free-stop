# Free Stop

**Who got lucky in the pits?**

Free Stop scores how much of an F1 driver's race result came from pit-stop timing luck — safety car windows, virtual safety cars, and red flags — versus normal green-flag strategy. Every stop from the 2024, 2025 and 2026 seasons is scored in real time from live OpenF1 data.

[![CI](https://github.com/leshvinsk/free-stop/actions/workflows/ci.yml/badge.svg)](https://github.com/leshvinsk/free-stop/actions/workflows/ci.yml)

---

## How it works

Each pit stop is benchmarked against the race's green-flag baseline cost. A stop taken under a safety car costs near zero — so it scores as a big saving. The field average is subtracted so only *relative* luck counts. Drivers who retired (DNF/DNS/DSQ) are excluded from the field average.

Full methodology is explained on the [Methodology page](https://free-stop-ui.onrender.com/methodology) of the live site.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 · FastAPI · httpx · Pydantic v2 |
| Frontend | Vue 3 · TypeScript · Vite |
| Data | [OpenF1 API](https://openf1.org) (live, no manual pipeline) |
| Cache | Redis (primary) · disk pickle (fallback) |
| Hosting | Render (free tier) |
| CI | GitHub Actions |

---

## Local development

**Prerequisites:** Python 3.12+, Node 22+

```bash
# 1. Clone
git clone https://github.com/leshvinsk/free-stop.git
cd free-stop

# 2. Backend
cd backend
pip install -e ".[dev]"
uvicorn main:app --reload        # http://localhost:8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

The frontend proxies `/api` to the local backend via `vite.config.ts` — no CORS setup needed.

---

## Running checks

```bash
# Backend
cd backend
ruff check . && ruff format --check .
mypy .
pytest -v

# Frontend
cd frontend
npm run type-check
npm run lint
npm run format -- --check
npm test
npx vite build
```

---

## Deployment

The repo includes a `render.yaml` that defines all three Render services:

| Service | Type | Description |
|---|---|---|
| `free-stop-api` | Python web service | FastAPI backend |
| `free-stop-ui` | Static site | Vue 3 frontend |
| `free-stop-redis` | Redis | Score cache |

Connect the repo to Render once — every push to `main` auto-deploys both services.

---

## Automated data

Two GitHub Actions workflows keep data fresh automatically:

- **Sync team data** (`sync-teams.yml`) — scrapes formula1.com daily (hourly on race weekends) and commits updated team principals, chassis names and power units
- **Keep warm** (`keep-warm.yml`) — pings the API health endpoint every 10 minutes to prevent Render free-tier spin-down

---

## Data sources

- **Pit stops, laps, race control:** [OpenF1](https://openf1.org) (open, no key required)
- **Team information:** [formula1.com](https://www.formula1.com/en/teams) (scraped daily)
- **Driver photos:** Formula 1 media CDN
- **Nationality flags:** [Jolpica](https://jolpica.com) (Ergast successor)
