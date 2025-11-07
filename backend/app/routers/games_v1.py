from fastapi import APIRouter, Query
from typing import Optional
from ..services.nba_api_service import NBADataService

router = APIRouter(prefix="/api/v1/games", tags=["games_v1"])

@router.get("/today")
def today(date: Optional[str] = None):
    """
    Get today's games. If date is provided (YYYY-MM-DD), use that date.
    Otherwise, use server's current date.
    """
    if date:
        # Parse the date and fetch games for that specific date
        from datetime import datetime
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            return {"games": NBADataService.fetch_games_for_date(target_date)}
        except ValueError:
            # Invalid date format, fall back to today
            return {"games": NBADataService.fetch_todays_games()}
    return {"games": NBADataService.fetch_todays_games()}

@router.get("/upcoming")
def upcoming(days: int = 7):
    return {"games": []}

@router.get("/{game_id}")
def game_detail(game_id: str):
    return {"game": {"id": game_id}}
