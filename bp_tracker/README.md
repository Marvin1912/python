# Blood Pressure Tracker

A small standalone Flask app for logging blood pressure readings into Postgres,
with a dashboard chart and stats panel. Lives alongside the YouTube summarizer
in this repo but has its own Dockerfile, dependencies, and database.

## Features

- Entry form: systolic, diastolic, optional pulse, optional measurement timestamp, free-text note.
- AHA-2025 category badge (Normal / Elevated / Stage 1 / Stage 2 / Hypertensive Crisis), color-coded.
- Stats button: average and median for systolic, diastolic, and pulse, plus average MAP and pulse pressure, over a chosen range (7 days / 30 days / all).
- Dashboard: line chart of readings over time (Chart.js).
- Configurable Postgres connection and schema via env vars.

## Quick start (local)

```bash
cd bp_tracker
cp .env.example .env
docker compose up --build
```

The app listens on `http://localhost:5001`. Postgres is exposed on host port `5433` (avoiding any host-installed Postgres on 5432).

Health check:

```bash
curl http://localhost:5001/healthz
```

Inspect the database directly:

```bash
docker compose exec db psql -U bp -d bptracker \
  -c "SELECT * FROM bp.readings ORDER BY measured_at DESC LIMIT 5;"
```

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | HTML UI |
| `POST` | `/api/readings` | Create a reading. Body: `{systolic, diastolic, pulse?, note?, measured_at?}` |
| `GET` | `/api/readings?range=7d\|30d\|all` | List readings (asc by `measured_at`) |
| `GET` | `/api/stats?range=7d\|30d\|all` | Average and median across the range |
| `GET` | `/healthz` | Liveness + DB ping |

## Configuration

All env vars — `BP_DB_*` and `FLASK_PORT` — are listed in `.env.example`.
The schema (`BP_DB_SCHEMA`) and table are bootstrapped on app startup if missing.

## Notes

- Single-user, no auth — intended for local use.
- AHA classification reflects the 2025 AHA/ACC guideline thresholds.
