from fastapi import APIRouter, Query
from typing import List
from ..core.models import Player

router = APIRouter(prefix="/api/players", tags=["players"])

@router.get("/search")
def search_players(q: str = Query(..., min_length=1)) -> dict:
    from ..services.stats_service import search_players_api

.get("/search")
def search_players(q: str = Query(..., min_length=1)) -> dict:
    items = search_players_api(q)
    return {"items": items}
