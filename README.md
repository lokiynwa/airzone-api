# Airzone

Airzone is a local-first monorepo for exploring live civil aircraft around a location and radius. The backend is built with FastAPI, and the frontend will be a React app that talks to the API over authenticated requests.

## Repository layout

- `backend/` FastAPI service, database, providers, and tests
- `frontend/` React client

## Backend quick start

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

Run tests with:

```bash
cd backend
uv run pytest
```

## Environment

Copy `backend/.env.example` to `backend/.env` and adjust values as needed.

