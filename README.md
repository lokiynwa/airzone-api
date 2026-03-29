# Airzone

Airzone is a local-first aircraft search app for exploring live civil flights around a chosen location and radius. It pairs a FastAPI backend with a React frontend, requires authenticated access for search features, and merges publicly available aviation data sources on a best-effort basis.

## Repository layout

- `backend/` FastAPI service, database, providers, and tests
- `frontend/` React client

## Features

- Secure signup, login, logout, and `/auth/me` session bootstrap
- Protected location geocoding and aircraft search endpoints
- Live aircraft search from OpenSky with exact radius filtering
- Public callsign route enrichment via ADSBDB, with optional aviationstack enhancement when configured
- Map-first local UI with search suggestions, aircraft cards, and partial-data badges

## Local setup

### 1. Configure the backend

```bash
cd backend
uv sync
cp .env.example .env
./.venv/bin/alembic upgrade head
```

Optional: seed a demo user after the migration runs.

```bash
cd backend
./.venv/bin/python -m app.scripts.seed_demo_user --email demo@airzone.local --password demo-pass-123
```

Key backend env vars:

- `DATABASE_URL`: defaults to local SQLite
- `AVIATIONSTACK_API_KEY`: optional, enables route and ETA enrichment
- `OPENSKY_CLIENT_ID` / `OPENSKY_CLIENT_SECRET`: optional, enables authenticated OpenSky access
- `CORS_ALLOW_ORIGINS`: comma-separated frontend origins

### 2. Configure the frontend

```bash
cd frontend
npm install
cp .env.example .env
```

### 3. Run the app locally

Backend:

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173`.

## Testing and verification

Backend checks:

```bash
cd backend
./.venv/bin/ruff check .
./.venv/bin/pytest
```

Frontend checks:

```bash
cd frontend
npm test
npm run build
```

## Data-source notes

- OpenSky provides live aircraft state vectors and spatial filtering.
- ADSBDB provides public airline and route enrichment for many live callsigns without requiring a key.
- aviationstack enrichment is optional; when it is missing or rate-limited, Airzone falls back to ADSBDB route data and best-effort ETA estimation.
- Nominatim powers the location lookup used by the local frontend search box.
