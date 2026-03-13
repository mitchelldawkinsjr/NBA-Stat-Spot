from fastapi import APIRouter, Query, Request, Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import date
from ..services.nba_api_service import NBADataService
from ..services.stats_calculator import StatsCalculator
from ..services.context_collector import ContextCollector
from ..utils.season import get_current_season, get_previous_season
from ..services.live_game_service import LiveGameService
from ..services.live_game_context_service import get_live_game_context_service
from ..core.rate_limiter import limiter
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/players", tags=["players_v1"])


class PlayerSearchItem(BaseModel):
    """Player search result item"""
    id: int = Field(..., description="Player ID", example=2544)
    name: str = Field(..., description="Player full name", example="LeBron James")
    team: Optional[str] = Field(None, description="Team abbreviation", example="LAL")


class PlayerSearchResponse(BaseModel):
    """Response model for player search"""
    items: List[PlayerSearchItem] = Field(..., description="List of matching players")


@router.get(
    "/search",
    response_model=PlayerSearchResponse,
    summary="Search for players by name",
    description="""
    Search for NBA players by name (full name, first name, or last name).
    
    The search is case-insensitive and matches partial names. Returns players
    from both active rosters and historical players.
    
    **Rate Limit:** 60 requests per minute per IP
    """,
    response_description="List of matching players with ID, name, and team",
    tags=["players_v1"]
)
@limiter.limit("60/minute")  # Rate limit: 60 requests per minute per IP
def search(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query (player name)", example="LeBron")
):
    """Search for players by name"""
    items = NBADataService.search_players(q)
    return {"items": items}

@router.get(
    "/stat-leaders",
    summary="Get league stat leaders",
    description="""
    Get the top players in the league for key statistical categories.
    
    Returns the top N players (default 3) for each category:
    - PTS: Points per game
    - AST: Assists per game
    - REB: Rebounds per game
    - 3PM: Three-pointers made per game
    
    Statistics are calculated as season averages based on game logs.
    """,
    response_description="Stat leaders grouped by category (PTS, AST, REB, 3PM)",
    tags=["players_v1"]
)
def stat_leaders(
    season: Optional[str] = Query(None, description="Season string (e.g., '2025-26'). Defaults to current season.", example="2025-26"),
    limit: int = Query(3, description="Number of top players to return per category", example=3, ge=1, le=20)
):
    """
    Get league-wide stat leaders for points, assists, rebounds, and 3PM.
    Returns top N players by season average for each stat category.
    Returns cached results instantly; data is pre-warmed by the admin/refresh cron.
    """
    from ..services.cache_service import get_cache_service
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from datetime import datetime
    import threading

    cache = get_cache_service()
    today_str = datetime.now().date().isoformat()
    cache_key = f"stat_leaders:{today_str}"

    cached = cache.get(cache_key)
    if cached:
        # Re-slice to requested limit
        for cat in cached.get("items", {}):
            cached["items"][cat] = cached["items"][cat][:limit]
        return cached

    # Cold-start: only use players whose game logs are already cached.
    # Never block the request on slow external API calls.
    season_to_use = season or get_current_season()
    players = NBADataService.fetch_all_players_including_rookies()
    active_players = [p for p in players if p.get("team_id") and p.get("team_id") != 0]

    leaders: Dict[str, list] = {"PTS": [], "AST": [], "REB": [], "3PM": []}
    leaders_lock = threading.Lock()

    def process_player(player):
        try:
            player_id = player.get("id")
            if not player_id:
                return None
            log_key = f"nba_api:player_game_log:{player_id}:{season_to_use}:{today_str}"
            logs = cache.get(log_key)
            if not logs or len(logs) < 5:
                return None
            pts_avg = sum(float(g.get("pts", 0) or 0) for g in logs) / len(logs)
            ast_avg = sum(float(g.get("ast", 0) or 0) for g in logs) / len(logs)
            reb_avg = sum(float(g.get("reb", 0) or 0) for g in logs) / len(logs)
            tpm_avg = sum(float(g.get("tpm", 0) or 0) for g in logs) / len(logs)
            name = player.get("full_name") or (player.get("first_name", "") + " " + player.get("last_name", "")).strip()
            return {
                "playerId": player_id,
                "playerName": name or f"Player {player_id}",
                "PTS": round(pts_avg, 1),
                "AST": round(ast_avg, 1),
                "REB": round(reb_avg, 1),
                "3PM": round(tpm_avg, 1),
            }
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_player, p): p for p in active_players}
        for future in as_completed(futures):
            try:
                result = future.result(timeout=5.0)
                if result:
                    with leaders_lock:
                        for cat in leaders:
                            leaders[cat].append({
                                "playerId": result["playerId"],
                                "playerName": result["playerName"],
                                "value": result[cat],
                            })
            except Exception:
                continue

    for cat in leaders:
        leaders[cat].sort(key=lambda x: x["value"], reverse=True)
        leaders[cat] = leaders[cat][:20]

    result = {"items": leaders}
    if any(leaders[cat] for cat in leaders):
        cache.set(cache_key, result, ttl=86400)
    # Re-slice to requested limit
    for cat in result.get("items", {}):
        result["items"][cat] = result["items"][cat][:limit]
    return result

@router.get(
    "/featured",
    summary="Get featured player IDs",
    description="Returns a list of featured player IDs. These are typically star players or popular players for quick access.",
    response_description="List of featured player IDs",
    tags=["players_v1"]
)
def featured():
    """Get list of featured player IDs"""
    return {"items": [2544, 201939, 203507, 1629029, 203076]}

@router.get(
    "/{player_id}",
    summary="Get player details",
    description="Get basic information about a specific player including name and team.",
    response_description="Player information including ID, name, and team",
    tags=["players_v1"]
)
def detail(
    player_id: int = Path(..., description="NBA player ID", example=2544)
):
    # Attempt to include player name and team from active roster or rookies
    name = None
    team_id = None
    team_name = None
    try:
        players = NBADataService.fetch_all_players_including_rookies() or []
        for p in players:
            pid = p.get("id")
            if pid is not None and int(pid) == int(player_id):
                name = p.get("full_name")
                team_id = p.get("team_id")
                break
        
        # If we have a team_id, get the team name
        if team_id is not None:
            teams = NBADataService.fetch_all_teams() or []
            team = next((t for t in teams if t.get("id") is not None and t.get("id") == team_id), None)
            if team:
                team_name = team.get("full_name")
    except Exception:
        pass
    return {
        "player": {
            "id": player_id,
            "name": name,
            "team_id": team_id,
            "team_name": team_name
        }
    }

@router.get(
    "/{player_id}/stats",
    summary="Get player game statistics",
    description="""
    Get game-by-game statistics for a player.
    
    Returns detailed statistics for each game including:
    - Points, rebounds, assists, steals, blocks
    - Field goal percentage, three-point percentage
    - Minutes played, plus/minus
    - Opponent and game date
    
    Use the `games` parameter to limit the number of recent games returned.
    """,
    response_description="List of game log entries with detailed statistics",
    tags=["players_v1"]
)
def stats(
    player_id: int = Path(..., description="NBA player ID", example=2544),
    games: int = Query(10, description="Number of recent games to return", example=10, ge=1, le=100),
    season: Optional[str] = Query(None, description="Season string (e.g., '2025-26')", example="2025-26"),
    refresh: bool = Query(False, description="If true, bypass cache and fetch fresh data from NBA API (slower)")
):
    try:
        season_to_use = season or get_current_season()
        # Use cache by default so page loads are fast; ?refresh=true for explicit refresh
        logs = NBADataService.fetch_player_game_log(player_id, season_to_use, force_refresh=refresh)
        if logs is None:
            logs = []
        
        # If no logs found, try previous seasons as fallback (use cache for fallbacks too)
        if len(logs) == 0:
            import structlog
            logger = structlog.get_logger()
            logger.info("No logs found for season, trying fallback seasons", player_id=player_id, season=season_to_use)
            logs = NBADataService.fetch_player_game_log(player_id, get_previous_season(season_to_use) or "2024-25", force_refresh=False)
            if logs is None:
                logs = []
            if len(logs) == 0:
                prev2 = get_previous_season(get_previous_season(season_to_use) or "2024-25")
                logs = NBADataService.fetch_player_game_log(player_id, prev2 or "2023-24", force_refresh=False)
                if logs is None:
                    logs = []
        
        return {"items": logs[:games] if games else logs}
    except Exception as e:
        # Log the error but return empty list instead of crashing
        import structlog
        logger = structlog.get_logger()
        logger.error("Failed to fetch player stats", player_id=player_id, season=season, error=str(e), exc_info=True)
        return {"items": []}

@router.get(
    "/{player_id}/live-stats",
    summary="Get live stats for player's current game",
    description="""
    Get live statistics for a player if they are currently playing in a game.
    
    Returns:
    - Live game information (teams, score, quarter, time remaining)
    - Player's current stats (points, rebounds, assists, minutes, etc.)
    - Game context (pace, situation, fouls)
    
    Returns null if player is not currently playing.
    """,
    response_description="Live game stats or null if not playing",
    tags=["players_v1"]
)
@limiter.limit("30/minute")
def live_stats(
    request: Request,
    player_id: int = Path(..., description="NBA player ID", example=2544)
):
    """Get live stats for a player's current game"""
    try:
        # Get player info to find their team
        players = NBADataService.fetch_all_players_including_rookies()
        player = next((p for p in players if p.get("id") == player_id), None)
        
        if not player:
            return {"playing": False, "message": "Player not found"}
        
        team_abbr = player.get("team_abbreviation") or player.get("team")
        if not team_abbr:
            return {"playing": False, "message": "Player team not found"}
        
        # Get today's games
        live_game_service = LiveGameService()
        games = live_game_service.get_todays_games()
        
        # Find game where player's team is playing
        current_game = None
        for game in games:
            if (game.home_team == team_abbr or game.away_team == team_abbr) and not game.is_final:
                current_game = game
                break
        
        if not current_game:
            return {"playing": False, "message": "No active game found"}
        
        # Get live stats from ESPN
        live_context_service = get_live_game_context_service()
        try:
            # Try to get ESPN game ID - might need to convert from API-NBA game ID
            espn_game_id = current_game.game_id
            live_context = live_context_service.extract_live_context(espn_game_id, player_id)
            
            player_stats = live_context.get("player_current_stats", {})
            
            return {
                "playing": True,
                "game": {
                    "game_id": current_game.game_id,
                    "home_team": current_game.home_team,
                    "away_team": current_game.away_team,
                    "home_score": current_game.home_score,
                    "away_score": current_game.away_score,
                    "quarter": current_game.quarter,
                    "time_remaining": current_game.time_remaining,
                    "is_home": current_game.home_team == team_abbr
                },
                "stats": {
                    "pts": player_stats.get("pts", 0),
                    "reb": player_stats.get("reb", 0),
                    "ast": player_stats.get("ast", 0),
                    "minutes": player_stats.get("minutes", 0.0),
                    "fouls": live_context.get("player_fouls", 0)
                },
                "context": {
                    "live_pace": live_context.get("live_pace", 0.0),
                    "game_situation": live_context.get("game_situation", "unknown"),
                    "projected_minutes_remaining": live_context.get("projected_minutes_remaining", 0.0),
                    "foul_trouble_score": live_context.get("foul_trouble_score", 0.0)
                }
            }
        except Exception as e:
            logger.warning("Error fetching live context", player_id=player_id, game_id=current_game.game_id, error=str(e))
            # Return basic game info even if we can't get detailed stats
            return {
                "playing": True,
                "game": {
                    "game_id": current_game.game_id,
                    "home_team": current_game.home_team,
                    "away_team": current_game.away_team,
                    "home_score": current_game.home_score,
                    "away_score": current_game.away_score,
                    "quarter": current_game.quarter,
                    "time_remaining": current_game.time_remaining,
                    "is_home": current_game.home_team == team_abbr
                },
                "stats": None,
                "context": None,
                "message": "Game found but detailed stats unavailable"
            }
            
    except Exception as e:
        logger.error("Error fetching live stats", player_id=player_id, error=str(e))
        return {"playing": False, "message": f"Error: {str(e)}"}

@router.get(
    "/{player_id}/trends",
    summary="Get player statistical trends",
    description="""
    Get rolling average trends for a player's statistics.
    
    Returns:
    - Last 20 games with individual game stats
    - 5-game rolling average
    - 10-game rolling average
    
    Useful for identifying hot streaks, slumps, or consistent performance patterns.
    """,
    response_description="Trend data with rolling averages and recent game logs",
    tags=["players_v1"]
)
def trends(
    player_id: int = Path(..., description="NBA player ID", example=2544),
    stat_type: str = Query("pts", description="Stat type to analyze: pts, reb, ast, tpm, etc.", example="pts"),
    season: Optional[str] = Query(None, description="Season string (e.g., '2025-26')", example="2025-26")
):
    season_to_use = season or get_current_season()
    logs = NBADataService.fetch_player_game_log(player_id, season_to_use)
    last = logs[-20:]
    avg10 = StatsCalculator.calculate_rolling_average(last, stat_type, 10)
    avg5 = StatsCalculator.calculate_rolling_average(last, stat_type, 5)
    heat_index = StatsCalculator.calculate_heat_index(last, stat_type, 10)
    volatility_index = StatsCalculator.calculate_volatility_index(last, stat_type, 10)
    return {
        "stat": stat_type,
        "avg5": avg5,
        "avg10": avg10,
        "heat_index": round(heat_index, 2),
        "volatility_index": volatility_index,
        "items": last,
    }


@router.get(
    "/{player_id}/streaks",
    summary="Get player streak data vs season averages",
    description="Returns how many consecutive games the player has exceeded their season average for PTS, REB, AST, and 3PM.",
    tags=["players_v1"]
)
def get_player_streaks(
    player_id: int = Path(..., description="NBA player ID", example=2544),
    season: Optional[str] = Query(None, description="Season string (e.g., '2025-26')", example="2025-26")
):
    """Return consecutive-game streak data for PTS, REB, AST, 3PM vs season average."""
    season_to_use = season or get_current_season()
    logs = NBADataService.fetch_player_game_log(player_id, season_to_use)
    if len(logs) < 3:
        return {"player_id": player_id, "streaks": {}}

    stats = ["pts", "reb", "ast", "tpm"]
    result: Dict[str, Any] = {}
    for stat in stats:
        season_avg = StatsCalculator.calculate_rolling_average(logs, stat, len(logs))
        if season_avg <= 0:
            continue
        streak_over = StatsCalculator.calculate_streak(logs, stat, season_avg, "over")
        streak_under = StatsCalculator.calculate_streak(logs, stat, season_avg, "under")
        recent5_avg = StatsCalculator.calculate_rolling_average(logs, stat, 5)
        result[stat] = {
            "season_avg": round(season_avg, 1),
            "recent5_avg": round(recent5_avg, 1),
            "streak_over": streak_over,   # consecutive games ABOVE season avg
            "streak_under": streak_under, # consecutive games BELOW season avg
            "hot": streak_over >= 3,
            "cold": streak_under >= 3,
        }
    return {"player_id": player_id, "games_analyzed": len(logs), "streaks": result}

@router.get(
    "/{player_id}/context",
    summary="Get player context for a specific game/opponent",
    description="""
    Get contextual information about a player for a specific game, including:
    - Head-to-head (H2H) averages against the opponent
    - Opponent defensive rankings
    - Injury status
    - Rest days
    - Team performance metrics
    
    This endpoint is useful for analyzing player performance against specific opponents.
    """,
    response_description="Player context including H2H data and opponent analysis",
    tags=["players_v1"]
)
@limiter.limit("30/minute")
def get_player_context(
    request: Request,
    player_id: int = Path(..., description="NBA player ID", example=2544),
    opponent_team_id: Optional[int] = Query(None, description="Opponent team ID", example=1610612747),
    game_date: Optional[str] = Query(None, description="Game date in YYYY-MM-DD format. Defaults to today.", example="2025-01-15"),
    is_home_game: bool = Query(True, description="Whether it's a home game"),
    season: Optional[str] = Query(None, description="Season string (e.g., '2025-26')", example="2025-26")
):
    """Get player context including H2H data for a specific opponent"""
    import structlog
    
    logger = structlog.get_logger()
    
    try:
        # Parse game date
        if game_date:
            try:
                game_date_obj = date.fromisoformat(game_date)
            except ValueError:
                game_date_obj = date.today()
        else:
            game_date_obj = date.today()
        
        # Collect player context
        # The defensive ranks calculation now uses parallel processing with timeouts
        # to prevent hanging. First request may take 1-2 minutes, subsequent requests
        # will use cached data and be much faster.
        context = ContextCollector.collect_player_context(
            player_id=player_id,
            game_date=game_date_obj,
            opponent_team_id=opponent_team_id,
            is_home_game=is_home_game,
            season=season or get_current_season()
        )
        
        # Enrich with full team performance for opponent (def_rank_3pm, offense ranks)
        opponent_defense = {
            "rank_pts": context.opponent_def_rank_pts,
            "rank_reb": context.opponent_def_rank_reb,
            "rank_ast": context.opponent_def_rank_ast,
        }
        opponent_offense = {}
        opponent_defense_vs_position = None
        if context.opponent_team_id:
            try:
                opp_perf = ContextCollector.get_team_performance(
                    context.opponent_team_id, season=season or get_current_season()
                )
                opponent_defense["rank_3pm"] = opp_perf.get("def_rank_3pm")
                opponent_offense = {
                    "rank_pts": opp_perf.get("off_rank_pts"),
                    "rank_reb": opp_perf.get("off_rank_reb"),
                    "rank_ast": opp_perf.get("off_rank_ast"),
                    "rank_3pm": opp_perf.get("off_rank_3pm"),
                }
            except Exception:
                pass
            # Position-based defense: opponent's ranks vs this player's position (PG/SG/SF/PF/C)
            try:
                from ..services.best_picks_service import _normalize_position
                all_players = NBADataService.fetch_all_players_including_rookies() or []
                player = next((p for p in all_players if p.get("id") == player_id), None)
                position = _normalize_position(player.get("position") if player else None)
                if position:
                    pos_ranks = ContextCollector._calculate_position_defensive_ranks(season or get_current_season()) or {}
                    opp_pos_ranks = pos_ranks.get(position, {}).get(int(context.opponent_team_id), {})
                    if opp_pos_ranks:
                        opponent_defense_vs_position = {
                            "position": position,
                            "rank_pts": opp_pos_ranks.get("pts"),
                            "rank_reb": opp_pos_ranks.get("reb"),
                            "rank_ast": opp_pos_ranks.get("ast"),
                            "rank_3pm": opp_pos_ranks.get("3pm"),
                        }
            except Exception:
                pass

        # Matchup advantage score: player season avg − opponent's avg allowed
        matchup_advantage: Dict[str, Any] = {}
        try:
            logs = NBADataService.fetch_player_game_log(player_id, season or get_current_season())
            if logs and context.opponent_team_id:
                def_avgs = ContextCollector.get_defensive_averages(season or get_current_season())
                opp_avgs = def_avgs.get(int(context.opponent_team_id)) or {}
                n = len(logs)
                if n >= 5 and opp_avgs:
                    player_pts = sum(float(g.get("pts", 0) or 0) for g in logs) / n
                    player_reb = sum(float(g.get("reb", 0) or 0) for g in logs) / n
                    player_ast = sum(float(g.get("ast", 0) or 0) for g in logs) / n
                    player_3pm = sum(float(g.get("tpm", 0) or 0) for g in logs) / n
                    matchup_advantage = {
                        "pts": round(player_pts - opp_avgs.get("pts", player_pts), 2),
                        "reb": round(player_reb - opp_avgs.get("reb", player_reb), 2),
                        "ast": round(player_ast - opp_avgs.get("ast", player_ast), 2),
                        "3pm": round(player_3pm - opp_avgs.get("3pm", player_3pm), 2),
                    }
        except Exception:
            pass

        # Return context data
        return {
            "player_id": player_id,
            "game_date": game_date_obj.isoformat(),
            "opponent_team_id": context.opponent_team_id,
            "opponent_team_abbr": context.opponent_team_abbr,
            "is_home_game": context.is_home_game,
            "rest_days": context.rest_days,
            "is_injured": context.is_injured,
            "injury_status": context.injury_status,
            "injury_description": context.injury_description,
            "h2h": {
                "avg_pts": context.h2h_avg_pts,
                "avg_reb": context.h2h_avg_reb,
                "avg_ast": context.h2h_avg_ast,
                "games_played": context.h2h_games_played
            },
            "opponent_defense": opponent_defense,
            "opponent_defense_vs_position": opponent_defense_vs_position,
            "opponent_offense": opponent_offense,
            "matchup_advantage": matchup_advantage,
            "team_performance": {
                "win_rate": context.team_win_rate,
                "conference_rank": context.team_conference_rank,
                "recent_form": context.team_recent_form
            },
            "opponent_performance": {
                "win_rate": context.opponent_win_rate,
                "conference_rank": context.opponent_conference_rank
            }
        }
    except Exception as e:
        logger.error("Failed to fetch player context", player_id=player_id, error=str(e))
        return {
            "player_id": player_id,
            "error": str(e),
            "h2h": {"avg_pts": None, "avg_reb": None, "avg_ast": None, "games_played": 0},
            "opponent_defense": {"rank_pts": None, "rank_reb": None, "rank_ast": None, "rank_3pm": None},
            "opponent_defense_vs_position": None,
            "opponent_offense": {"rank_pts": None, "rank_reb": None, "rank_ast": None, "rank_3pm": None}
        }

