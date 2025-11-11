"""
Live Game Service - Fetches live NBA game data
Uses API-NBA as primary source, falls back to ESPN, then nba_api
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import structlog
from .api_nba_service import get_api_nba_service
from .over_under_service import LiveGame
from .cache_service import get_cache_service

logger = structlog.get_logger()


class LiveGameService:
    """Service to fetch live NBA games for over/under analysis"""
    
    def __init__(self):
        self.cache = get_cache_service()
        self.api_nba_service = get_api_nba_service()
    
    def get_todays_games(self) -> List[LiveGame]:
        """
        Fetch all games happening today (live, scheduled, or completed)
        Uses API-NBA as primary source, falls back to ESPN, then nba_api
        
        Returns:
            List of LiveGame objects
        """
        # Try API-NBA first
        try:
            games = self._fetch_from_api_nba()
            if games:
                logger.info("Fetched live games from API-NBA", count=len(games))
                return games
        except Exception as e:
            logger.warning("API-NBA failed, trying ESPN", error=str(e))
        
        # Fallback to ESPN
        try:
            games = self._fetch_from_espn()
            if games:
                logger.info("Fetched live games from ESPN", count=len(games))
                return games
        except Exception as e:
            logger.warning("ESPN failed, trying nba_api", error=str(e))
        
        # Final fallback to nba_api
        try:
            games = self._fetch_from_nba_api()
            if games:
                logger.info("Fetched live games from nba_api", count=len(games))
                return games
        except Exception as e:
            logger.error("All live game sources failed", error=str(e))
        
        return []
    
    def _fetch_from_api_nba(self) -> List[LiveGame]:
        """Fetch live games from API-NBA"""
        api_games = self.api_nba_service.get_live_games()
        live_games = []
        
        for game in api_games:
            try:
                home_team = game.get("home_team", {})
                away_team = game.get("away_team", {})
                
                home_score = home_team.get("score", 0)
                away_score = away_team.get("score", 0)
                period = game.get("period", 0)
                status = game.get("status", "")
                
                is_final = "Final" in status or period == 0
                
                live_game = LiveGame(
                    game_id=game.get("game_id", ""),
                    home_team=home_team.get("code", ""),
                    away_team=away_team.get("code", ""),
                    home_score=int(home_score) if home_score else 0,
                    away_score=int(away_score) if away_score else 0,
                    quarter=period if period > 0 else 1,
                    time_remaining=game.get("time_remaining", "12:00"),
                    is_final=is_final
                )
                live_games.append(live_game)
            except Exception as e:
                logger.warning("Error parsing API-NBA game", error=str(e))
                continue
        
        return live_games
    
    def _fetch_from_espn(self) -> List[LiveGame]:
        """Fetch live games from ESPN API"""
        from .espn_api_service import get_espn_service
        
        espn_service = get_espn_service()
        scoreboard_data = espn_service.get_scoreboard()
        
        if not scoreboard_data:
            return []
        
        events = scoreboard_data.get("events", [])
        live_games = []
        
        for event in events:
            try:
                game_id = event.get("id", "")
                if not game_id:
                    continue
                
                competitions = event.get("competitions", [])
                if not competitions:
                    continue
                
                comp = competitions[0]
                competitors = comp.get("competitors", [])
                status = comp.get("status", {})
                
                home_team = None
                away_team = None
                home_score = 0
                away_score = 0
                
                for competitor in competitors:
                    team = competitor.get("team", {})
                    score = competitor.get("score", "0")
                    is_home = competitor.get("homeAway") == "home"
                    
                    team_abbr = team.get("abbreviation", "")
                    
                    if is_home:
                        home_team = team_abbr
                        home_score = int(score) if score else 0
                    else:
                        away_team = team_abbr
                        away_score = int(score) if score else 0
                
                status_type = status.get("type", {})
                status_id = int(status_type.get("id", 0))
                period = status.get("period", 0)
                clock = status.get("displayClock", "")
                
                is_final = status_id == 3 or status_type.get("name") == "STATUS_FINAL"
                
                if not is_final or period > 0:
                    live_game = LiveGame(
                        game_id=game_id,
                        home_team=home_team or "UNK",
                        away_team=away_team or "UNK",
                        home_score=home_score,
                        away_score=away_score,
                        quarter=period if period > 0 else 1,
                        time_remaining=clock if clock else "12:00",
                        is_final=is_final
                    )
                    live_games.append(live_game)
            except Exception as e:
                logger.warning("Error parsing ESPN game", error=str(e))
                continue
        
        return live_games
    
    def _fetch_from_nba_api(self) -> List[LiveGame]:
        """Fallback: Fetch from nba_api library"""
        from .nba_api_service import NBADataService
        
        games_data = NBADataService.fetch_todays_games()
        live_games = []
        
        for game in games_data:
            try:
                game_id = str(game.get('gameId') or game.get('game_id') or game.get('id', ''))
                if not game_id:
                    continue
                
                home_team_data = game.get('homeTeam') or game.get('home_team') or {}
                away_team_data = game.get('awayTeam') or game.get('away_team') or {}
                
                home_team = self._extract_team_name(home_team_data)
                away_team = self._extract_team_name(away_team_data)
                
                home_score = self._extract_score(home_team_data)
                away_score = self._extract_score(away_team_data)
                
                quarter = game.get('period') or game.get('quarter') or game.get('periodValue', 0)
                time_remaining = game.get('gameClock') or game.get('time_remaining') or game.get('clock', '12:00')
                game_status = game.get('gameStatusText') or game.get('status') or game.get('gameStatus', '')
                
                is_final = (
                    game_status == 'Final' or 
                    game_status == 'Final/OT' or
                    game.get('gameStatus') == 3 or
                    quarter == 0
                )
                
                if not is_final or quarter > 0:
                    live_game = LiveGame(
                        game_id=game_id,
                        home_team=home_team,
                        away_team=away_team,
                        home_score=home_score,
                        away_score=away_score,
                        quarter=quarter if quarter > 0 else 1,
                        time_remaining=time_remaining if time_remaining else '12:00',
                        is_final=is_final
                    )
                    live_games.append(live_game)
            except Exception as e:
                logger.warning("Error parsing nba_api game", error=str(e))
                continue
        
        return live_games
    
    def get_game_by_id(self, game_id: str) -> Optional[LiveGame]:
        """
        Fetch a specific game by ID
        
        Args:
            game_id: Game ID string
            
        Returns:
            LiveGame object or None if not found
        """
        games = self.get_todays_games()
        for game in games:
            if game.game_id == game_id:
                return game
        return None
    
    def _extract_team_name(self, team_data: Dict[str, Any]) -> str:
        """Extract team name from team data structure"""
        if isinstance(team_data, str):
            return team_data
        
        # Try various possible keys
        return (
            team_data.get('teamName') or
            team_data.get('team_name') or
            team_data.get('name') or
            team_data.get('fullName') or
            team_data.get('full_name') or
            team_data.get('teamTricode') or
            team_data.get('tricode') or
            'Unknown'
        )
    
    def _extract_score(self, team_data: Dict[str, Any]) -> int:
        """Extract score from team data structure"""
        if isinstance(team_data, (int, float)):
            return int(team_data)
        
        score = (
            team_data.get('score') or
            team_data.get('points') or
            0
        )
        
        try:
            return int(score)
        except (ValueError, TypeError):
            return 0

