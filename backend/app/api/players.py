from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/api/players", tags=["players"])

@router.get("/search")
def search_players(q: str = Query(..., min_length=1)) -> dict:
    """Search for players by name (legacy endpoint - use /api/v1/players/search instead)"""
    from ..services.nba_api_service import NBADataService
    items = NBADataService.search_players(q)
    return {"items": items}

@router.get("/{player_id}/gamelogs")
def player_gamelogs(player_id: int, season: Optional[str] = None, lastN: Optional[int] = None) -> dict:
    """Get player game logs (legacy endpoint - use /api/v1/players/{player_id}/stats instead)"""
    from ..services.nba_api_service import NBADataService
    logs = NBADataService.fetch_player_game_log(player_id=player_id, season=season)
    if lastN:
        logs = logs[:lastN]
    return {"items": logs}
