from fastapi import APIRouter
from ..services.nba_api_service import NBADataService

router = APIRouter(prefix="/api/v1/games", tags=["games_v1"])

@router.get("/today")
def today():
    return {"games": NBADataService.fetch_todays_games()}

@router.get("/upcoming")
def upcoming(days: int = 7):
    return {"games": []}

@router.get("/{game_id}")
def game_detail(game_id: str):
    return {"game": {"id": game_id}}
