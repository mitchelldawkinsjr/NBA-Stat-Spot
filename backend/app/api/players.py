from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/players", tags=["players"])

@router.get("/search")
def search_players(q: str = Query(..., min_length=1)) -> dict:
    """
    DEPRECATED: This endpoint is deprecated. Use /api/v1/players/search instead.
    This endpoint will be removed in a future version.
    """
    logger.warning("Legacy endpoint accessed", endpoint="/api/players/search", query=q)
    from ..services.nba_api_service import NBADataService
    items = NBADataService.search_players(q)
    return {"items": items, "deprecated": True, "message": "Use /api/v1/players/search instead"}

@router.get("/{player_id}/gamelogs")
def player_gamelogs(player_id: int, season: Optional[str] = None, lastN: Optional[int] = None) -> dict:
    """
    DEPRECATED: This endpoint is deprecated. Use /api/v1/players/{player_id}/stats instead.
    This endpoint will be removed in a future version.
    """
    logger.warning("Legacy endpoint accessed", endpoint=f"/api/players/{player_id}/gamelogs", player_id=player_id)
    from ..services.nba_api_service import NBADataService
    logs = NBADataService.fetch_player_game_log(player_id=player_id, season=season)
    if lastN:
        logs = logs[:lastN]
    return {"items": logs, "deprecated": True, "message": f"Use /api/v1/players/{player_id}/stats instead"}
