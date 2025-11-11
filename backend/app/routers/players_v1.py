from fastapi import APIRouter, Query, Request, Path
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from ..services.nba_api_service import NBADataService
from ..services.stats_calculator import StatsCalculator
from ..core.rate_limiter import limiter

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
    """
    season_to_use = season or "2025-26"
    players = NBADataService.fetch_all_players_including_rookies()
    
    # We'll compute season averages for a sample of active players
    # For performance, limit to players with team_id (active roster players)
    active_players = [p for p in players if p.get("team_id") is not None][:30]  # Reduced to 30 for faster response
    
    leaders = {
        "PTS": [],
        "AST": [],
        "REB": [],
        "3PM": []
    }
    
    # Process players in parallel for better performance
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading
    
    # Use locks to safely append to leaders
    leaders_lock = threading.Lock()
    
    def process_player_for_leaders(player):
        """Process a single player and return leader data"""
        try:
            player_id = player.get("id")
            if not player_id:
                return None
                
            logs = NBADataService.fetch_player_game_log(player_id, season_to_use)
            if not logs or len(logs) < 5:  # Need at least 5 games
                return None
                
            # Calculate season averages
            pts_avg = sum(float(g.get("pts", 0) or 0) for g in logs) / len(logs)
            ast_avg = sum(float(g.get("ast", 0) or 0) for g in logs) / len(logs)
            reb_avg = sum(float(g.get("reb", 0) or 0) for g in logs) / len(logs)
            tpm_avg = sum(float(g.get("tpm", 0) or 0) for g in logs) / len(logs)
            
            player_name = player.get("full_name") or player.get("first_name", "") + " " + player.get("last_name", "")
            if not player_name or player_name.strip() == "":
                player_name = f"Player {player_id}"
            
            return {
                "playerId": player_id,
                "playerName": player_name.strip(),
                "PTS": round(pts_avg, 1),
                "AST": round(ast_avg, 1),
                "REB": round(reb_avg, 1),
                "3PM": round(tpm_avg, 1)
            }
        except Exception:
            return None
    
    # Process players in parallel (max 6 concurrent workers for faster response)
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_player = {
            executor.submit(process_player_for_leaders, player): player 
            for player in active_players
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_player):
            try:
                result = future.result(timeout=2.0)  # 2 second timeout per player (reduced)
                if result:
                    with leaders_lock:
                        leaders["PTS"].append({"playerId": result["playerId"], "playerName": result["playerName"], "value": result["PTS"]})
                        leaders["AST"].append({"playerId": result["playerId"], "playerName": result["playerName"], "value": result["AST"]})
                        leaders["REB"].append({"playerId": result["playerId"], "playerName": result["playerName"], "value": result["REB"]})
                        leaders["3PM"].append({"playerId": result["playerId"], "playerName": result["playerName"], "value": result["3PM"]})
            except Exception:
                continue
    
    # Sort and take top N for each category
    for cat in leaders:
        leaders[cat].sort(key=lambda x: x["value"], reverse=True)
        leaders[cat] = leaders[cat][:limit]
    
    return {"items": leaders}

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
            if int(p.get("id")) == int(player_id):
                name = p.get("full_name")
                team_id = p.get("team_id")
                break
        
        # If we have a team_id, get the team name
        if team_id:
            teams = NBADataService.fetch_all_teams()
            team = next((t for t in teams if t.get("id") == team_id), None)
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
    season: Optional[str] = Query(None, description="Season string (e.g., '2025-26')", example="2025-26")
):
    try:
        season_to_use = season or "2025-26"
        logs = NBADataService.fetch_player_game_log(player_id, season_to_use)
        if logs is None:
            logs = []
        return {"items": logs[:games] if games else logs}
    except Exception as e:
        # Log the error but return empty list instead of crashing
        import structlog
        logger = structlog.get_logger()
        logger.error("Failed to fetch player stats", player_id=player_id, season=season, error=str(e))
        return {"items": []}

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
    season_to_use = season or "2025-26"
    logs = NBADataService.fetch_player_game_log(player_id, season_to_use)
    last = logs[-20:]
    avg10 = StatsCalculator.calculate_rolling_average(last, stat_type, 10)
    avg5 = StatsCalculator.calculate_rolling_average(last, stat_type, 5)
    return {"stat": stat_type, "avg5": avg5, "avg10": avg10, "items": last}

