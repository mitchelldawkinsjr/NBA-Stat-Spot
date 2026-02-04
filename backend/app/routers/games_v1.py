from fastapi import APIRouter, Query, Path
from typing import Optional, List, Dict, Any
from datetime import date, timedelta, datetime
import structlog
from ..services.live_game_service import LiveGameService
from ..services.espn_api_service import get_espn_service

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/games", tags=["games_v1"])


def _games_from_espn_scoreboard(target_date: date) -> List[Dict[str, Any]]:
    """Fetch games for a date from ESPN scoreboard and map to our game format (gameId, home, away, gameTimeUTC, gameEt, status)."""
    try:
        espn_service = get_espn_service()
        # ESPN expects YYYYMMDD
        date_str = target_date.strftime("%Y%m%d")
        scoreboard_data = espn_service.get_scoreboard(date=date_str)
        if not scoreboard_data or not isinstance(scoreboard_data.get("events"), list):
            return []
        games = []
        for event in scoreboard_data["events"]:
            try:
                game_id = str(event.get("id", ""))
                event_date = event.get("date") or ""
                status_obj = event.get("status") or {}
                status_id = str(status_obj.get("id", "1"))
                status_desc = (status_obj.get("description") or "").upper()
                if status_id == "3" or "FINAL" in status_desc or status_obj.get("completed"):
                    status = "FINAL"
                elif status_id == "2" or "IN PROGRESS" in status_desc or "LIVE" in status_desc:
                    status = "LIVE"
                else:
                    status = "SCHEDULED"
                home_abbr = None
                away_abbr = None
                comps = event.get("competitions") or []
                if comps:
                    for comp in comps:
                        for c in comp.get("competitors") or []:
                            abbr = (c.get("team") or {}).get("abbreviation", "")
                            if (c.get("homeAway") or "").lower() == "home":
                                home_abbr = abbr
                            else:
                                away_abbr = abbr
                if home_abbr is None and away_abbr is None:
                    continue
                games.append({
                    "gameId": game_id,
                    "home": home_abbr or "",
                    "away": away_abbr or "",
                    "gameTimeUTC": event_date,
                    "gameEt": event_date,
                    "status": status,
                })
            except (KeyError, TypeError, IndexError) as e:
                logger.warning("Skip ESPN event", event_id=event.get("id"), error=str(e))
                continue
        return games
    except Exception as e:
        logger.warning("ESPN scoreboard failed", date=str(target_date), error=str(e))
        return []


@router.get(
    "/today",
    summary="Get games for a specific date",
    description="""
    Get all NBA games scheduled for a specific date.
    Uses ESPN scoreboard (live, reliable). Date format: YYYY-MM-DD
    """,
    response_description="List of games for the specified date",
    tags=["games_v1"]
)
def today(
    date_param: Optional[str] = Query(None, description="Date in YYYY-MM-DD format. Defaults to today.", example="2025-01-15", alias="date")
):
    """
    Get today's games. If date is provided (YYYY-MM-DD), use that date.
    Otherwise, use server's current date. Source: ESPN scoreboard only.
    """
    target_date = date.today()
    if date_param:
        try:
            target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    games = _games_from_espn_scoreboard(target_date)
    return {"games": games}

@router.get(
    "/upcoming",
    summary="Get upcoming games",
    description="Get upcoming games within the specified number of days. Uses ESPN scoreboard per day.",
    response_description="List of upcoming games",
    tags=["games_v1"]
)
def upcoming(
    days: int = Query(7, description="Number of days ahead to look for games", example=7, ge=1, le=30)
):
    """Get upcoming games for the next N days (ESPN scoreboard per date)."""
    try:
        all_games = []
        today = date.today()
        for day_offset in range(days + 1):
            target_date = today + timedelta(days=day_offset)
            games_for_date = _games_from_espn_scoreboard(target_date)
            for game in games_for_date:
                status = (game.get("status") or "").upper()
                if status not in ("FINAL", "COMPLETED"):
                    all_games.append(game)
        return {"games": all_games}
    except Exception as e:
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
