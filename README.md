# NBA Stat Spot — Player Prop-Bet Analysis (v1)

Lightweight web app to surface suggested NBA player prop bets with transparent rationale.

## Tech Stack

### Backend
- **Framework**: FastAPI 0.115.0 (Python 3.11+)
- **Server**: Uvicorn (ASGI server)
- **Database**: SQLite (default) / PostgreSQL (via `DATABASE_URL` env var)
- **ORM**: SQLAlchemy 2.0.36
- **Migrations**: Alembic 1.13.3
- **Data Processing**: Pandas 2.2.3, NumPy 1.26.4
- **HTTP Client**: httpx 0.27.2
- **Caching**: cachetools 5.5.0 (in-memory), Redis 5.0.7 (optional)
- **Task Queue**: Celery 5.4.0 (optional, for background jobs)
- **Logging**: structlog 24.4.0
- **NBA Data**: nba_api 1.5.0

### Frontend
- **Framework**: React 19.1.1 with TypeScript 5.9.3
- **Build Tool**: Vite 7.1.7
- **Routing**: React Router DOM 6.30.1
- **Data Fetching**: TanStack React Query 5.90.2
- **Charts**: Recharts 3.3.0
- **Styling**: Tailwind CSS 4.1.16
- **Linting**: ESLint 9.36.0

### Infrastructure
- **Containerization**: Docker
- **Orchestration**: Docker Compose
- **Reverse Proxy**: Nginx (production)
- **Database**: SQLite (development) / PostgreSQL (production-ready)

## Quickstart

### Backend
1. Create and activate a virtualenv
```
python3 -m venv .venv && source .venv/bin/activate
```
2. Install deps
```
pip install -r backend/requirements.txt
```
3. Run server
```
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend
```

### Frontend
1. Install deps
```
cd frontend && npm install
```
2. Run dev server
```
npm run dev
```

Backend runs on http://localhost:8000, Frontend on http://localhost:5173

## Project Structure
- backend/: FastAPI app with services for stats, features, projections, suggestions
- frontend/: React app with Good Bets dashboard and player search flow
- docs/: API contracts and ops notes

## Documentation
- **API Contracts**: See `docs/api-contracts.md`
- **Deployment Guide**: See `docs/deployment.md`
- **Operations Runbook**: See `docs/runbook.md`

## Disclaimer
This app provides informational analysis only and is not financial advice.
