from __future__ import annotations
from typing import Any, Dict, List, Optional
from cachetools import TTLCache, cached
from cachetools.keys import hashkey

try:
    from nba_api.stats.static import teams as static_teams
    from nba_api.stats.static import players as static_players
    from nba_api.stats.endpoints import playergamelog
    from nba_api.live.nba.endpoints import scoreboard
except Exception:  # pragma: no cover
    static_teams = None
    static_players = None
    playergamelog = None
    scoreboard = None


a_cache = TTLCache(maxsize=1024, ttl=3600)


class NBADataService:
    @staticmethod
    @cached(a_cache, key=lambda: hashkey("teams"))
    def fetch_all_teams() -> List[Dict[str, Any]]:
        if static_teams is None:
            return []
        return static_teams.get_teams()

    @staticmethod
    @cached(a_cache, key=lambda: hashkey("players_active"))
    def fetch_active_players() -> List[Dict[str, Any]]:
        if static_players is None:
            return []
        return [p for p in static_players.get_players() if p.get("is_active")]

    @staticmethod
    def fetch_player_game_log(player_id: int, season: Optional[str]) -> List[Dict[str, Any]]:
        if playergamelog is None:
            return []
        gl = playergamelog.PlayerGameLog(player_id=player_id, season=season)
        df = gl.get_data_frames()[0]
        items: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            items.append({
                "game_id": str(row.get("Game_ID")),
                "game_date": str(row.get("GAME_DATE")),
                "matchup": str(row.get("MATCHUP")),
                "pts": float(row.get("PTS", 0) or 0),
                "reb": float(row.get("REB", 0) or 0),
                "ast": float(row.get("AST", 0) or 0),
                "tpm": float(row.get("FG3M", 0) or 0),
            })
        return items

    @staticmethod
    def fetch_todays_games() -> List[Dict[str, Any]]:
        if scoreboard is None:
            return []
        sb = scoreboard.ScoreBoard()
        games = []
        for g in sb.games.get_dict():
            games.append({
                "gameId": g.get("gameId"),
                "home": g.get("homeTeam", {}).get("teamTricode"),
                "away": g.get("awayTeam", {}).get("teamTricode"),
                "gameTimeUTC": g.get("gameTimeUTC"),
            })
        return games
