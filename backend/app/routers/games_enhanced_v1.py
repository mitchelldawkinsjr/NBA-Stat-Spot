"""
Enhanced Games Router
Provides enhanced game features using both API-NBA and ESPN data
"""
from fastapi import APIRouter, Query, Request
from typing import Optional
import structlog
from ..services.api_nba_service import get_api_nba_service
from ..services.espn_api_service import get_espn_service
from ..core.rate_limiter import limiter
from ..core.error_handler import APIError

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/games/enhanced", tags=["games_enhanced_v1"])


@router.get("/live")
@limiter.limit("30/minute")
def get_live_games_enhanced(request: Request):
    """
    Get live games with enhanced data from both API-NBA and ESPN.
    
    Returns:
        Enhanced live games data
    """
    try:
        api_nba_service = get_api_nba_service()
        espn_service = get_espn_service()
        
        # Get data from both sources
        api_nba_games = api_nba_service.get_live_games()
        espn_scoreboard = espn_service.get_scoreboard()
        
        # Combine and enhance data
        enhanced_games = []
        
        # Use ESPN as primary structure, enhance with API-NBA data
        if espn_scoreboard:
            events = espn_scoreboard.get("events", [])
            for event in events:
                game_id = event.get("id", "")
                
                # Try to find matching API-NBA game
                api_nba_game = None
                for game in api_nba_games:
                    if game.get("game_id") == game_id:
                        api_nba_game = game
                        break
                
                enhanced_game = {
                    "game_id": game_id,
                    "espn_data": event,
                    "api_nba_data": api_nba_game
                }
                enhanced_games.append(enhanced_game)
        
        return {"games": enhanced_games}
    except Exception as e:
        logger.error("Error fetching enhanced live games", error=str(e))
        raise APIError(f"Failed to fetch enhanced live games: {str(e)}", status_code=500)


@router.get("/{game_id}/details")
@limiter.limit("30/minute")
def get_game_details_enhanced(request: Request, game_id: str):
    """
    Get enhanced game details combining API-NBA and ESPN data.
    
    Args:
        game_id: Game ID
        
    Returns:
        Enhanced game details
    """
    try:
        api_nba_service = get_api_nba_service()
        espn_service = get_espn_service()
        
        # Fetch from both sources
        api_nba_details = api_nba_service.get_game_details(game_id)
        espn_summary = espn_service.get_game_summary(game_id)
        espn_playbyplay = espn_service.get_play_by_play(game_id)
        
        return {
            "game_id": game_id,
            "api_nba": api_nba_details,
            "espn_summary": espn_summary,
            "espn_playbyplay": espn_playbyplay
        }
    except Exception as e:
        logger.error("Error fetching enhanced game details", game_id=game_id, error=str(e))
        raise APIError(f"Failed to fetch enhanced game details: {str(e)}", status_code=500)


@router.get("/{game_id}/boxscore")
@limiter.limit("30/minute")
def get_boxscore_enhanced(request: Request, game_id: str):
    """
    Get enhanced box score combining API-NBA and ESPN data.
    
    Args:
        game_id: Game ID
        
    Returns:
        Enhanced box score data
    """
    try:
        api_nba_service = get_api_nba_service()
        espn_service = get_espn_service()
        
        # Get box score from ESPN (more detailed)
        espn_summary = espn_service.get_game_summary(game_id)
        
        # Get game details from API-NBA
        api_nba_details = api_nba_service.get_game_details(game_id)
        
        return {
            "game_id": game_id,
            "espn_boxscore": espn_summary,
            "api_nba_details": api_nba_details
        }
    except Exception as e:
        logger.error("Error fetching enhanced box score", game_id=game_id, error=str(e))
        raise APIError(f"Failed to fetch enhanced box score: {str(e)}", status_code=500)


@router.get("/{game_id}/stats")
@limiter.limit("30/minute")
def get_game_stats_enhanced(request: Request, game_id: str):
    """
    Get enhanced game statistics from both sources.
    
    Args:
        game_id: Game ID
        
    Returns:
        Enhanced game statistics
    """
    try:
        api_nba_service = get_api_nba_service()
        espn_service = get_espn_service()
        
        # Get stats from both sources
        api_nba_details = api_nba_service.get_game_details(game_id)
        espn_summary = espn_service.get_game_summary(game_id)
        
        # Extract and combine stats
        stats = {
            "game_id": game_id,
            "api_nba_stats": api_nba_details,
            "espn_stats": espn_summary.get("boxscore", {}) if espn_summary else {}
        }
        
        return stats
    except Exception as e:
        logger.error("Error fetching enhanced game stats", game_id=game_id, error=str(e))
        raise APIError(f"Failed to fetch enhanced game stats: {str(e)}", status_code=500)

