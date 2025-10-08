# NBA Stat Spot — Player Prop-Bet Analysis (v1)

Lightweight web app to surface suggested NBA player prop bets with transparent rationale.

## Stack
- Backend: FastAPI (Python)
- Frontend: React + Vite (TypeScript)
- Caching: In-memory (MVP)

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

## API (v1)
See docs/api-contracts.md.

## Disclaimer
This app provides informational analysis only and is not financial advice.
