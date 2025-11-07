# API Contracts (v1)

- GET /api/players/search?q= → 200 { items: Array<{ id: number; name: string; team: string }> }
- GET /api/players/{id}/gamelogs → 200 { items: GameLog[] }
- GET /api/teams/{id}/defense → 200 { teamId, pace, defensiveRating, allowed: Record<string, number> }
- GET /api/players/{id}/context → 200 { opponents: Team[], form: object }
- POST /api/props/suggest → 200 { suggestions: PropSuggestion[] }
- GET /api/schedule/upcoming?hours=24 → 200 { games: Game[] }
- POST /api/props/good-bets → 200 { games: Array<{ game: Game; top: PropSuggestion[] }> }

For detailed field definitions, see the Pydantic models in `backend/app/api/` and SQLAlchemy models in `backend/app/models/`.
