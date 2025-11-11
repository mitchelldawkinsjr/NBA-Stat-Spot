from __future__ import annotations
from typing import List, Dict, Any

# nba_api imports
from nba_api.stats.endpoints import playergamelog

from ..core.config import last_season_str
from .nba_api_service import NBADataService
from .cache_service import get_cache_service

# DEPRECATED: Use NBADataService.search_players() instead
# This function is kept for backward compatibility but should be removed
def search_players_api(q: str) -> List[Dict[str, Any]]:
    """
    DEPRECATED: Use NBADataService.search_players() instead.
    This function will be removed in a future version.
    """
    return NBADataService.search_players(q)


def get_player_gamelogs(player_id: int, season: str | None = None) -> List[Dict[str, Any]]:
    """
    Get player game logs with caching via CacheService.
    DEPRECATED: Use NBADataService.fetch_player_game_log() instead.
    """
    season = season or "2025-26"  # Default to 2025-26 season
    cache = get_cache_service()
    cache_key = f"stats_service:player_gamelogs:{player_id}:{season}"
    
    # Check cache
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    # Fetch from API
    gl = playergamelog.PlayerGameLog(player_id=player_id, season=season)
    df = gl.get_data_frames()[0]
    # Map to minimal fields
    items: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        items.append(
            {
                "date": str(row["GAME_DATE"]),
                "opponent": str(row["MATCHUP"]).split(" ")[-1],
                "home": "vs" in str(row["MATCHUP"]),
                "minutes": float(row.get("MIN", 0) or 0),
                "pts": float(row.get("PTS", 0) or 0),
                "reb": float(row.get("REB", 0) or 0),
                "ast": float(row.get("AST", 0) or 0),
                "tpm": float(row.get("FG3M", 0) or 0),
            }
        )
    
    # Cache for 1 hour (3600 seconds)
    cache.set(cache_key, items, ttl=3600)
    return items
