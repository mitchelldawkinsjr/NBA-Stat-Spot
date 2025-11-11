from fastapi import APIRouter, Query, Path
from typing import Optional
from ..services.nba_api_service import NBADataService

router = APIRouter(prefix="/api/v1/games", tags=["games_v1"])

@router.get(
    "/today",
    summary="Get games for a specific date",
    description="""
    Get all NBA games scheduled for a specific date.
    
    If no date is provided, returns games for today (server time).
    Date format: YYYY-MM-DD
    
    Returns game information including:
    - Game ID
    - Home and away teams
    - Game time
    - Status
    """,
    response_description="List of games for the specified date",
    tags=["games_v1"]
)
def today(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format. Defaults to today.", example="2025-01-15")
):
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

@router.get(
    "/upcoming",
    summary="Get upcoming games",
    description="Get upcoming games within the specified number of days. Currently returns empty list - functionality to be implemented.",
    response_description="List of upcoming games",
    tags=["games_v1"]
)
def upcoming(
    days: int = Query(7, description="Number of days ahead to look for games", example=7, ge=1, le=30)
):
    """Get upcoming games"""
    return {"games": []}

@router.get(
    "/{game_id}",
    summary="Get game details",
    description="Get basic information about a specific game by game ID.",
    response_description="Game information",
    tags=["games_v1"]
)
def game_detail(
    game_id: str = Path(..., description="NBA game ID", example="0022400123")
):
    """Get game details"""
    return {"game": {"id": game_id}}
