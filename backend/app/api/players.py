from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/api/players", tags=["players"])

@router.get("/search")
def search_players(q: str = Query(..., min_length=1)) -> dict:
    from ..services.stats_service import search_players_api
    items = search_players_api(q)
    return {"items": items}

@router.get("/{player_id}/gamelogs")
def player_gamelogs(player_id: int, season: Optional[str] = None, lastN: Optional[int] = None) -> dict:
    from ..services.stats_service import get_player_gamelogs
    logs = get_player_gamelogs(player_id=player_id, season=season)
    if lastN:
        logs = logs[: lastN]
    return {"items": logs}
