from fastapi import APIRouter, Query, Path
from typing import Optional
from datetime import date, timedelta
from ..services.nba_api_service import NBADataService
from ..services.live_game_service import LiveGameService
from ..services.espn_api_service import get_espn_service

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
    description="Get upcoming games within the specified number of days. Fetches games from today through the specified number of days ahead.",
    response_description="List of upcoming games",
    tags=["games_v1"]
)
def upcoming(
    days: int = Query(7, description="Number of days ahead to look for games", example=7, ge=1, le=30)
):
    """Get upcoming games for the next N days"""
    try:
        all_games = []
        today = date.today()
        
        # Fetch games for each day from today through the specified number of days
        for day_offset in range(days + 1):  # Include today
            target_date = today + timedelta(days=day_offset)
            games_for_date = NBADataService.fetch_games_for_date(target_date)
            
            # Filter to only scheduled/upcoming games (not completed)
            for game in games_for_date:
                status = game.get("status", "").upper()
                # Only include scheduled or live games (not final)
                if status in ["SCHEDULED", "LIVE", "IN_PROGRESS"] or status not in ["FINAL", "COMPLETED"]:
                    all_games.append(game)
        
        return {"games": all_games}
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.error("Failed to fetch upcoming games", days=days, error=str(e))
    return {"games": []}

@router.get(
    "/{game_id}",
    summary="Get game details",
    description="Get detailed information about a specific game including teams, scores, status, and timing.",
    response_description="Game information with teams, scores, and status",
    tags=["games_v1"]
)
def game_detail(
    game_id: str = Path(..., description="NBA game ID", example="0022400123")
):
    """Get detailed game information"""
    try:
        # Try to get from today's games first
        live_game_service = LiveGameService()
        game = live_game_service.get_game_by_id(game_id)
        
        if game:
            return {
                "game": {
                    "id": game.game_id,
                    "home_team": game.home_team,
                    "away_team": game.away_team,
                    "home_score": game.home_score,
                    "away_score": game.away_score,
                    "quarter": game.quarter,
                    "time_remaining": game.time_remaining,
                    "status": "FINAL" if game.is_final else ("LIVE" if game.quarter else "SCHEDULED"),
                    "is_final": game.is_final
                }
            }
        
        # If not found in today's games, try to fetch from ESPN
        try:
            espn_service = get_espn_service()
            summary = espn_service.get_game_summary(game_id)
            
            if summary:
                # Extract game info from ESPN summary
                competitions = summary.get("header", {}).get("competitions", [])
                if competitions:
                    comp = competitions[0]
                    competitors = comp.get("competitors", [])
                    
                    home_team = None
                    away_team = None
                    home_score = 0
                    away_score = 0
                    
                    for competitor in competitors:
                        team_data = competitor.get("team", {})
                        team_abbr = team_data.get("abbreviation", "")
                        score = competitor.get("score", 0)
                        is_home = competitor.get("homeAway") == "home"
                        
                        if is_home:
                            home_team = team_abbr
                            home_score = score
                        else:
                            away_team = team_abbr
                            away_score = score
                    
                    status_obj = comp.get("status", {})
                    status_type = status_obj.get("type", {})
                    status_id = status_type.get("id", 1)
                    
                    game_status = "SCHEDULED"
                    if status_id == 2:
                        game_status = "LIVE"
                    elif status_id == 3:
                        game_status = "FINAL"
                    
                    return {
                        "game": {
                            "id": game_id,
                            "home_team": home_team,
                            "away_team": away_team,
                            "home_score": home_score,
                            "away_score": away_score,
                            "status": game_status,
                            "is_final": status_id == 3
                        }
                    }
        except Exception:
            pass
        
        # Fallback: return basic info
        return {"game": {"id": game_id, "status": "UNKNOWN"}}
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.error("Failed to fetch game details", game_id=game_id, error=str(e))
        return {"game": {"id": game_id, "status": "ERROR", "error": str(e)}}
