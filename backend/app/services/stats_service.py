from __future__ import annotations
from functools import lru_cache
from typing import List, Dict, Any
from cachetools import TTLCache, cached
from cachetools.keys import hashkey

# nba_api imports
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog

from ..core.config import last_season_str

# Simple TTL caches to keep under rate limits
search_cache = TTLCache(maxsize=1024, ttl=3600)
logs_cache = TTLCache(maxsize=2048, ttl=3600)


@cached(search_cache, key=lambda q: hashkey(q.lower()))
def search_players_api(q: str) -> List[Dict[str, Any]]:
    all_players = players.get_players()
    ql = q.lower()
    matches = [p for p in all_players if ql in p.get('full_name', '').lower()]
    # Normalize
    return [
        {"id": int(p["id"]), "name": p["full_name"], "team": p.get("team_id")}
        for p in matches[:20]
    ]


@cached(logs_cache, key=lambda player_id, season: hashkey(player_id, season))
def get_player_gamelogs(player_id: int, season: str | None = None) -> List[Dict[str, Any]]:
    season = season or last_season_str()
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
    return items
