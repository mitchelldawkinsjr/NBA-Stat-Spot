# API Contracts (v1)

**Purpose**: Reference documentation for all API endpoints, request/response formats, and data structures.

**Use this guide when**:
- Integrating with the API from external applications
- Understanding request/response formats
- Building frontend components that call the backend
- Debugging API issues

---

## Core API Endpoints

### Players
- GET /api/players/search?q= → 200 { items: Array<{ id: number; name: string; team: string }> }
- GET /api/players/{id}/gamelogs → 200 { items: GameLog[] }
- GET /api/players/{id}/context → 200 { opponents: Team[], form: object }

### Teams
- GET /api/teams/{id}/defense → 200 { teamId, pace, defensiveRating, allowed: Record<string, number> }

### Props & Suggestions
- POST /api/props/suggest → 200 { suggestions: PropSuggestion[] }
- POST /api/props/good-bets → 200 { games: Array<{ game: Game; top: PropSuggestion[] }> }

### Schedule
- GET /api/schedule/upcoming?hours=24 → 200 { games: Game[] }

## ESPN Integration Endpoints (`/api/v1/espn`)

All ESPN endpoints are rate-limited (30 requests/minute) and return cached data when available.

### Games & Scoreboard
- GET /api/v1/espn/scoreboard?date=YYYYMMDD → 200 { events: Game[], ... }
- GET /api/v1/espn/games/{game_id}/summary → 200 { header: {...}, boxscore: {...}, ... }
- GET /api/v1/espn/games/{game_id}/playbyplay → 200 { periods: Period[], ... }
- GET /api/v1/espn/games/{game_id}/gamecast → 200 { gamecast data }

### Teams
- GET /api/v1/espn/teams → 200 { sports: [{ leagues: [{ teams: Team[] }] }] }
- GET /api/v1/espn/teams/{team_id} → 200 { team: TeamInfo, ... }
- GET /api/v1/espn/teams/{team_id}/roster → 200 { roster: Player[] }
- GET /api/v1/espn/teams/{team_id}/schedule → 200 { schedule: Game[] }

### Players
- GET /api/v1/espn/players/{player_id} → 200 { player: PlayerInfo, ... }

### League Data
- GET /api/v1/espn/standings → 200 { children: Conference[], ... }
- GET /api/v1/espn/news → 200 { articles: Article[] }
- GET /api/v1/espn/injuries → 200 { teams: [{ athletes: [{ injuries: Injury[] }] }] }
- GET /api/v1/espn/transactions → 200 { transactions: Transaction[] }

**Note**: ESPN endpoints use unofficial public APIs. No authentication required. Rate limits and caching are handled automatically.

For detailed field definitions, see the Pydantic models in `backend/app/api/` and SQLAlchemy models in `backend/app/models/`.
