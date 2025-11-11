# NBA Stat Spot — Player Prop-Bet Analysis (v1)

Lightweight web app to surface suggested NBA player prop bets with transparent rationale, enhanced with real-time ESPN data integration.

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
- **ESPN Integration**: Real-time injury data, standings, news, and live game context

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
```bash
python3 -m venv .venv && source .venv/bin/activate
# On Windows: .venv\Scripts\activate
```

2. Install dependencies
```bash
pip install -r backend/requirements.txt
```

3. (Optional) Run database migrations
```bash
cd backend
alembic upgrade head
```

4. Run server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend
```

**Note**: The backend now includes ESPN data integration. No additional API keys are required for ESPN endpoints (they use public unofficial endpoints).

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

### Verify Setup
After installing dependencies, verify the backend is properly configured:
```bash
cd backend && python3 verify_setup.py
```

## Key Features

### Enhanced Predictions with ESPN Data
- **Real Injury Status**: Live injury reports from ESPN (probable/questionable/doubtful/out)
- **Team Standings**: Conference rankings, recent form, and playoff race pressure
- **News & Transactions**: Sentiment analysis and transaction impact on player performance
- **Live Game Context**: Real-time pace, foul trouble, and game situation for in-game props
- **Enhanced Matchups**: Actual head-to-head history using ESPN team schedules

### Core Capabilities
- **Player Prop Analysis**: AI-powered suggestions for points, rebounds, assists, 3PM, and PRA
- **ML Predictions**: Machine learning models for confidence scoring and line prediction
- **Over/Under Analysis**: Live game total predictions with pace adjustments
- **Parlay Builder**: Multi-leg parlay construction with confidence calculations
- **Bet Tracking**: Track your bets and analyze performance

## Project Structure
- backend/: FastAPI app with services for stats, features, projections, suggestions, and ESPN integration
- frontend/: React app with Good Bets dashboard and player search flow
- docs/: API contracts and ops notes

## Documentation

All documentation is located in the `docs/` directory. See [docs/README.md](docs/README.md) for a complete index.

**Quick Links**:
- 📖 [Documentation Index](docs/README.md) - Overview of all guides
- 🚀 [Deployment Guide](docs/deployment.md) - How to deploy the application
- 📡 [API Contracts](docs/api-contracts.md) - API endpoint reference
- 🔧 [Operations Runbook](docs/runbook.md) - Operations and troubleshooting
- 🌐 [GitHub Pages Deployment](docs/github-pages-deployment.md) - Frontend-only deployment
- 🎨 [Theme Setup](docs/theme-setup.md) - Sliced Pro theme configuration
- 🏀 [ESPN API Configuration](docs/external-api-configuration.md) - ESPN data integration setup

## Disclaimer
This app provides informational analysis only and is not financial advice.
