from fastapi import APIRouter, Query
from typing import Optional
from ..services.nba_api_service import NBADataService
from ..services.stats_calculator import StatsCalculator

router = APIRouter(prefix="/api/v1/players", tags=["players_v1"])

@router.get("/search")
def search(q: str = Query(..., min_length=1)):
    """Search for players by name"""
    items = NBADataService.search_players(q)
    return {"items": items}

@router.get("/stat-leaders")
def stat_leaders(season: Optional[str] = None, limit: int = 3):
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

@router.get("/featured")
def featured():
    return {"items": [2544, 201939, 203507, 1629029, 203076]}

@router.get("/{player_id}")
def detail(player_id: int):
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

@router.get("/{player_id}/stats")
def stats(player_id: int, games: int = 10, season: Optional[str] = None):
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

@router.get("/{player_id}/trends")
def trends(player_id: int, stat_type: str = "pts", season: Optional[str] = None):
    season_to_use = season or "2025-26"
    logs = NBADataService.fetch_player_game_log(player_id, season_to_use)
    last = logs[-20:]
    avg10 = StatsCalculator.calculate_rolling_average(last, stat_type, 10)
    avg5 = StatsCalculator.calculate_rolling_average(last, stat_type, 5)
    return {"stat": stat_type, "avg5": avg5, "avg10": avg10, "items": last}

