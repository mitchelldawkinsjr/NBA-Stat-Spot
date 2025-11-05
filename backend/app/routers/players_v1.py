from fastapi import APIRouter, Query
from typing import Optional
from ..services.nba_api_service import NBADataService
from ..services.stats_calculator import StatsCalculator

router = APIRouter(prefix="/api/v1/players", tags=["players_v1"])

@router.get("/search")
def search(q: str = Query(..., min_length=1)):
    items = NBADataService.fetch_active_players()
    ql = q.lower()
    filtered = [
        {"id": p.get("id"), "name": p.get("full_name"), "team": p.get("team_id")}
        for p in items if ql in p.get("full_name", "").lower()
    ][:20]
    return {"items": filtered}

@router.get("/{player_id}")
def detail(player_id: int):
    return {"player": {"id": player_id}}

@router.get("/{player_id}/stats")
def stats(player_id: int, games: int = 10, season: Optional[str] = None):
    logs = NBADataService.fetch_player_game_log(player_id, season)
    return {"items": logs[:games] if games else logs}

@router.get("/{player_id}/trends")
def trends(player_id: int, stat_type: str = "pts", season: Optional[str] = None):
    logs = NBADataService.fetch_player_game_log(player_id, season)
    last = logs[-20:]
    avg10 = StatsCalculator.calculate_rolling_average(last, stat_type, 10)
    avg5 = StatsCalculator.calculate_rolling_average(last, stat_type, 5)
    return {"stat": stat_type, "avg5": avg5, "avg10": avg10, "items": last}

@router.get("/featured")
def featured():
    return {"items": [2544, 201939, 203507, 1629029, 203076]}
