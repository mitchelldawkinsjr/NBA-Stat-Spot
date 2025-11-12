"""
Over/Under Analysis API Router
Provides endpoints for live game over/under analysis
"""

from fastapi import APIRouter, Query, Request
from typing import Optional, List, Dict, Any
import structlog
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError, as_completed
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
        # Normalize team names to ensure consistent lookup keys
        home_stats = team_stats_service.get_team_stats(live_game.home_team)
        away_stats = team_stats_service.get_team_stats(live_game.away_team)
        
        # Log team stats retrieval for debugging
        logger.debug(
            "Team stats retrieved",
            home_team=live_game.home_team,
            home_stats_team=home_stats.team_name,
            home_ppg=home_stats.ppg,
            away_team=live_game.away_team,
            away_stats_team=away_stats.team_name,
            away_ppg=away_stats.ppg,
            expected_pace=home_stats.ppg + away_stats.ppg
        )
        
        # Use normalized team names from stats objects as keys
        # Also store with original names for fallback
        team_stats_lookup[home_stats.team_name] = home_stats
        team_stats_lookup[away_stats.team_name] = away_stats
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


def _analyze_single_game(
    game: LiveGame,
    team_stats_service: TeamStatsService,
    use_ai: bool
) -> Optional[Dict[str, Any]]:
    """
    Helper function to analyze a single game.
    Extracted for parallel processing.
    
    Args:
        game: LiveGame object to analyze
        team_stats_service: TeamStatsService instance
        use_ai: Whether to use AI features
        
    Returns:
        Analysis result dict or None if analysis fails
    """
    try:
        # Build team stats lookup for this game
        # Normalize team names to ensure consistent lookup keys
        team_stats_lookup = {}
        home_stats = team_stats_service.get_team_stats(game.home_team)
        away_stats = team_stats_service.get_team_stats(game.away_team)
        
        # Log team stats retrieval for debugging
        logger.debug(
            "Team stats retrieved for game analysis",
            game_id=game.game_id,
            home_team=game.home_team,
            home_stats_team=home_stats.team_name,
            home_ppg=home_stats.ppg,
            away_team=game.away_team,
            away_stats_team=away_stats.team_name,
            away_ppg=away_stats.ppg,
            expected_pace=home_stats.ppg + away_stats.ppg
        )
        
        # Use normalized team names from stats objects as keys
        # Also store with original names for fallback
        team_stats_lookup[home_stats.team_name] = home_stats
        team_stats_lookup[away_stats.team_name] = away_stats
        team_stats_lookup[game.home_team] = home_stats
        team_stats_lookup[game.away_team] = away_stats
        
        # Check admin AI setting - override use_ai if admin has disabled AI
        ai_enabled = SettingsService.get_ai_enabled()
        effective_use_ai = use_ai and ai_enabled
        
        # Create analyzer
        analyzer = OverUnderAnalyzer(team_stats_lookup)
        
        # Analyze (with optional AI enhancement, gated by admin setting)
        analysis = analyzer.analyze_game(game, live_line=None, use_ai=effective_use_ai)
        
        return {
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
        }
    except Exception as e:
        logger.warning("Error analyzing game", game_id=game.game_id, error=str(e))
        return None


@router.get("/analyze-all")
@limiter.limit("10/minute")
def analyze_all_games(
    request: Request,
    use_ai: bool = Query(False, description="Enable AI features (ML predictions and LLM rationales)")
):
    """
    Analyze all live games for over/under opportunities
    
    Uses parallel processing with 30s overall timeout and 8s per-game timeout.
    Returns partial results if some games complete before timeout.
    
    Args:
        use_ai: Enable AI features (ML predictions and LLM rationales).
                Note: This is gated by the admin AI setting - if AI is disabled
                in admin settings, this parameter will be ignored.
    
    Returns:
        List of analysis results for all live games
    """
    endpoint_start = time.time()
    
    try:
        # Get all live games with timing
        games_fetch_start = time.time()
        live_game_service = LiveGameService()
        games = live_game_service.get_todays_games()
        games_fetch_duration = time.time() - games_fetch_start
        logger.info("Fetched games", duration=round(games_fetch_duration, 2), count=len(games))
        
        # Log details about fetched games for debugging
        if games:
            for g in games:
                logger.debug(
                    "Fetched game",
                    game_id=g.game_id,
                    home=g.home_team,
                    away=g.away_team,
                    quarter=g.quarter,
                    is_final=g.is_final,
                    home_score=g.home_score,
                    away_score=g.away_score
                )
        
        # Very permissive filter - include almost all games
        # Only exclude games that are explicitly final AND have zero scores (likely data errors)
        # This ensures we capture all live games, scheduled games, and recently finished games
        active_games = [
            g for g in games 
            # Include all games except those that are final with zero scores (data errors)
            if not (g.is_final and g.home_score == 0 and g.away_score == 0)
            # Also ensure we have valid team names
            and g.home_team and g.away_team and g.home_team != "UNK" and g.away_team != "UNK"
        ]
        
        # Log why games were filtered out
        filtered_out = [g for g in games if g not in active_games]
        if filtered_out:
            for g in filtered_out:
                logger.debug(
                    "Game filtered out",
                    game_id=g.game_id,
                    home=g.home_team,
                    away=g.away_team,
                    quarter=g.quarter,
                    is_final=g.is_final,
                    home_score=g.home_score,
                    away_score=g.away_score,
                    reason="is_final=True with zero scores" if (g.is_final and g.home_score == 0 and g.away_score == 0) else "is_final=True" if g.is_final else "unknown"
                )
        
        # Log active games summary
        logger.info(
            "Active games summary",
            total_fetched=len(games),
            active_count=len(active_games),
            filtered_out_count=len(filtered_out),
            active_game_ids=[g.game_id for g in active_games[:5]]  # First 5 for debugging
        )
        
        if not active_games:
            logger.info("No active games to analyze", total_games=len(games), filtered_out=len(filtered_out))
            return {"games": []}
        
        logger.info("Analyzing games", active_count=len(active_games))
        
        # Get team stats service
        team_stats_service = TeamStatsService()
        
        # Process games in parallel with overall timeout
        results = []
        failed_games = []
        timed_out_games = []
        
        # Use ThreadPoolExecutor with overall timeout wrapper
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all game analysis tasks
            future_to_game = {
                executor.submit(_analyze_single_game, game, team_stats_service, use_ai): game
                for game in active_games
            }
            
            # Process results as they complete, with per-game timeout
            for future in as_completed(future_to_game, timeout=30.0):
                game = future_to_game[future]
                game_start = time.time()
                
                try:
                    # Wait for result with per-game timeout of 8 seconds
                    result = future.result(timeout=8.0)
                    game_duration = time.time() - game_start
                    
                    if result:
                        results.append(result)
                        logger.info(
                            "Game analysis completed",
                            game_id=game.game_id,
                            duration=round(game_duration, 2)
                        )
                    else:
                        failed_games.append(game.game_id)
                        logger.warning("Game analysis returned None", game_id=game.game_id)
                        
                except FutureTimeoutError:
                    timed_out_games.append(game.game_id)
                    logger.warning(
                        "Game analysis timed out",
                        game_id=game.game_id,
                        duration=round(time.time() - game_start, 2)
                    )
                except Exception as e:
                    failed_games.append(game.game_id)
                    logger.warning(
                        "Game analysis failed",
                        game_id=game.game_id,
                        error=str(e),
                        duration=round(time.time() - game_start, 2)
                    )
        
        total_duration = time.time() - endpoint_start
        logger.info(
            "Analysis complete",
            total_duration=round(total_duration, 2),
            successful=len(results),
            failed=len(failed_games),
            timed_out=len(timed_out_games),
            total_games=len(active_games)
        )
        
        return {"games": results}
        
    except FutureTimeoutError:
        total_duration = time.time() - endpoint_start
        logger.error(
            "Endpoint timed out",
            duration=round(total_duration, 2),
            completed_games=len(results) if 'results' in locals() else 0
        )
        # Return partial results if we have any
        if 'results' in locals() and results:
            logger.info("Returning partial results due to timeout", count=len(results))
            return {"games": results, "partial": True, "timeout": True}
        raise APIError("Analysis timed out after 30 seconds", status_code=504)
        
    except Exception as e:
        total_duration = time.time() - endpoint_start
        logger.error(
            "Error analyzing all games",
            error=str(e),
            duration=round(total_duration, 2)
        )
        raise APIError(f"Failed to analyze games: {str(e)}", status_code=500)

