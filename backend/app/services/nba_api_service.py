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
    @cached(a_cache, key=lambda: hashkey("players_all_including_rookies"))
    def fetch_all_players_including_rookies() -> List[Dict[str, Any]]:
        """Fetch all players including rookies who may not be marked as active yet."""
        if static_players is None:
            return []
        all_players = static_players.get_players()
        # Include ALL players - don't filter by is_active or team_id
        # This ensures rookies are included even if they don't have team_id set yet
        # or aren't marked as active. The search endpoint will limit results anyway.
        return all_players

    @staticmethod
    def fetch_player_game_log(player_id: int, season: Optional[str]) -> List[Dict[str, Any]]:
        if playergamelog is None:
            return []
        # Default to current season if not provided
        season_to_use = season or "2025-26"
        gl = playergamelog.PlayerGameLog(player_id=player_id, season=season_to_use)
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
        """
        Fetch all games for today, including:
        - Scheduled games (not yet started)
        - Live games (in progress)
        - Recently completed games (finished today)
        """
        if scoreboard is None:
            return []
        try:
            sb = scoreboard.ScoreBoard()
            games = []
            for g in sb.games.get_dict():
                # Include all games for today regardless of status
                # (scheduled, live, or recently finished)
                game_status = g.get("gameStatusText", "").upper()
                game_id = g.get("gameId")
                
                # ScoreBoard includes all games for today, so we include them all
                games.append({
                    "gameId": game_id,
                    "home": g.get("homeTeam", {}).get("teamTricode"),
                    "away": g.get("awayTeam", {}).get("teamTricode"),
                    "gameTimeUTC": g.get("gameTimeUTC"),
                    "status": game_status,  # e.g., "LIVE", "FINAL", "SCHEDULED"
                })
            return games
        except Exception:
            # Return empty list on error rather than crashing
            return []
    
    @staticmethod
    def fetch_games_for_date(target_date) -> List[Dict[str, Any]]:
        """
        Fetch games for a specific date. For now, this uses the same logic as fetch_todays_games
        since the NBA API ScoreBoard typically only returns today's games.
        In the future, this could be enhanced to fetch games for specific dates.
        """
        # For now, return today's games and let the frontend filter by date
        # The NBA API ScoreBoard endpoint typically only returns today's games
        return NBADataService.fetch_todays_games()
