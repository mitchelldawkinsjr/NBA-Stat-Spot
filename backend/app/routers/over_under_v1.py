"""
Over/Under Analysis API Router
Provides endpoints for live game over/under analysis
"""

from fastapi import APIRouter, Query, Request
from typing import Optional, List
import structlog
from ..services.over_under_service import OverUnderAnalyzer, LiveGame
from ..services.live_game_service import LiveGameService
from ..services.team_stats_service import TeamStatsService
from ..services.settings_service import SettingsService
from ..core.rate_limiter import limiter
from ..core.error_handler import APIError

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/over-under", tags=["over_under_v1"])


@router.get("/live-games")
@limiter.limit("30/minute")
def get_live_games(request: Request):
    """
    Get all live games happening today
    
    Returns:
        List of live games with current scores and status
    """
    try:
        live_game_service = LiveGameService()
        games = live_game_service.get_todays_games()
        
        # Convert LiveGame objects to dictionaries
        games_data = []
        for game in games:
            games_data.append({
                "game_id": game.game_id,
                "home_team": game.home_team,
                "away_team": game.away_team,
                "home_score": game.home_score,
                "away_score": game.away_score,
                "quarter": game.quarter,
                "time_remaining": game.time_remaining,
                "is_final": game.is_final,
                "current_total": game.home_score + game.away_score
            })
        
        return {"games": games_data}
        
    except Exception as e:
        logger.error("Error fetching live games", error=str(e))
        raise APIError(f"Failed to fetch live games: {str(e)}", status_code=500)


@router.get("/analyze/{game_id}")
@limiter.limit("30/minute")
def analyze_game(
    request: Request,
    game_id: str,
    live_line: Optional[float] = Query(None, description="Current over/under betting line"),
    use_ai: bool = Query(False, description="Enable AI features (ML predictions and LLM rationales)")
):
    """
    Analyze a specific game for over/under betting opportunities
    
    Args:
        game_id: Game ID to analyze
        live_line: Optional current betting line
        use_ai: Enable AI features (ML predictions and LLM rationales).
                Note: This is gated by the admin AI setting - if AI is disabled
                in admin settings, this parameter will be ignored.
        
    Returns:
        Analysis results with recommendation, confidence, and reasoning
    """
    try:
        # Get live game data
        live_game_service = LiveGameService()
        live_game = live_game_service.get_game_by_id(game_id)
        
        if not live_game:
            raise APIError(f"Game {game_id} not found", status_code=404)
        
        # Get team stats
        team_stats_service = TeamStatsService()
        team_stats_lookup = {}
        
        # Build team stats lookup
        home_stats = team_stats_service.get_team_stats(live_game.home_team)
        away_stats = team_stats_service.get_team_stats(live_game.away_team)
        
        team_stats_lookup[live_game.home_team] = home_stats
        team_stats_lookup[live_game.away_team] = away_stats
        
        # Check admin AI setting - override use_ai if admin has disabled AI
        ai_enabled = SettingsService.get_ai_enabled()
        effective_use_ai = use_ai and ai_enabled
        
        # Create analyzer with team stats
        analyzer = OverUnderAnalyzer(team_stats_lookup)
        
        # Perform analysis (with optional AI enhancement, gated by admin setting)
        analysis = analyzer.analyze_game(live_game, live_line, use_ai=effective_use_ai)
        
        # Return analysis results
        return {
            "game_id": game_id,
            "game": {
                "home_team": live_game.home_team,
                "away_team": live_game.away_team,
                "home_score": live_game.home_score,
                "away_score": live_game.away_score,
                "quarter": live_game.quarter,
                "time_remaining": live_game.time_remaining,
                "is_final": live_game.is_final
            },
            "analysis": analysis.to_dict()
        }
        
    except APIError:
        raise
    except Exception as e:
        logger.error("Error analyzing game", game_id=game_id, error=str(e))
        raise APIError(f"Failed to analyze game: {str(e)}", status_code=500)


@router.get("/analyze-all")
@limiter.limit("10/minute")
def analyze_all_games(
    request: Request,
    use_ai: bool = Query(False, description="Enable AI features (ML predictions and LLM rationales)")
):
    """
    Analyze all live games for over/under opportunities
    
    Args:
        use_ai: Enable AI features (ML predictions and LLM rationales).
                Note: This is gated by the admin AI setting - if AI is disabled
                in admin settings, this parameter will be ignored.
    
    Returns:
        List of analysis results for all live games
    """
    try:
        # Get all live games
        live_game_service = LiveGameService()
        games = live_game_service.get_todays_games()
        
        # Filter to only in-progress games (not final)
        active_games = [g for g in games if not g.is_final and g.quarter > 0]
        
        if not active_games:
            return {"games": []}
        
        # Get team stats service
        team_stats_service = TeamStatsService()
        
        results = []
        
        for game in active_games:
            try:
                # Build team stats lookup for this game
                team_stats_lookup = {}
                home_stats = team_stats_service.get_team_stats(game.home_team)
                away_stats = team_stats_service.get_team_stats(game.away_team)
                
                team_stats_lookup[game.home_team] = home_stats
                team_stats_lookup[game.away_team] = away_stats
                
                # Check admin AI setting - override use_ai if admin has disabled AI
                ai_enabled = SettingsService.get_ai_enabled()
                effective_use_ai = use_ai and ai_enabled
                
                # Create analyzer
                analyzer = OverUnderAnalyzer(team_stats_lookup)
                
                # Analyze (with optional AI enhancement, gated by admin setting)
                analysis = analyzer.analyze_game(game, live_line=None, use_ai=effective_use_ai)
                
                results.append({
                    "game_id": game.game_id,
                    "game": {
                        "home_team": game.home_team,
                        "away_team": game.away_team,
                        "home_score": game.home_score,
                        "away_score": game.away_score,
                        "quarter": game.quarter,
                        "time_remaining": game.time_remaining,
                        "is_final": game.is_final
                    },
                    "analysis": analysis.to_dict()
                })
                
            except Exception as e:
                logger.warning("Error analyzing game", game_id=game.game_id, error=str(e))
                continue
        
        return {"games": results}
        
    except Exception as e:
        logger.error("Error analyzing all games", error=str(e))
        raise APIError(f"Failed to analyze games: {str(e)}", status_code=500)

