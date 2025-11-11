"""
ESPN API Service
Integration with ESPN's unofficial API endpoints for NBA data.
All endpoints from endpoints-enhanced-hidden-espn.md
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime
import structlog
from .external_api_client import get_external_api_client
from .external_api_rate_limiter import APIProvider

logger = structlog.get_logger()


class ESPNService:
    """
    Service for ESPN API integration.
    Provides scoreboard, box scores, play-by-play, teams, standings, news, injuries, transactions.
    """
    
    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
    WEB_BASE_URL = "https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba"
    
    def __init__(self):
        self.client = get_external_api_client()
    
    def get_scoreboard(self, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get scoreboard with all games for a date.
        
        Args:
            date: Optional date in YYYYMMDD format (default: today)
            
        Returns:
            Scoreboard data dictionary or None
        """
        endpoint = f"{self.BASE_URL}/scoreboard"
        params = {}
        if date:
            params["dates"] = date
        
        cache_key = f"espn:scoreboard:{date or 'today'}:30s"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.ESPN,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=30,  # 30 seconds for live data
            params=params,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
        )
        
        return data
    
    def get_game_summary(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        Get game summary/box score for a specific game.
        
        Args:
            game_id: Game/event ID
            
        Returns:
            Game summary dictionary or None
        """
        endpoint = f"{self.WEB_BASE_URL}/summary"
        params = {"event": game_id}
        
        cache_key = f"espn:game_summary:{game_id}:5m"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.ESPN,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=300,  # 5 minutes
            params=params,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
        )
        
        return data
    
    def get_play_by_play(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        Get play-by-play data for a specific game.
        
        Args:
            game_id: Game/event ID
            
        Returns:
            Play-by-play data dictionary or None
        """
        endpoint = f"{self.WEB_BASE_URL}/playbyplay"
        params = {"event": game_id}
        
        cache_key = f"espn:playbyplay:{game_id}:30s"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.ESPN,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=30,  # 30 seconds for live data
            params=params,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
        )
        
        return data
    
    def get_gamecast(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        Get gamecast data (advanced game data).
        
        Args:
            game_id: Game/event ID
            
        Returns:
            Gamecast data dictionary or None
        """
        endpoint = f"https://cdn.espn.com/core/nba/gamecast"
        params = {"gameId": game_id, "xhr": "1"}
        
        cache_key = f"espn:gamecast:{game_id}:30s"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.ESPN,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=30,  # 30 seconds for live data
            params=params,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
        )
        
        return data
    
    def get_teams(self) -> List[Dict[str, Any]]:
        """
        Get all NBA teams.
        
        Returns:
            List of team dictionaries
        """
        endpoint = f"{self.BASE_URL}/teams"
        cache_key = "espn:teams:1h"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.ESPN,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=3600,  # 1 hour for static data
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
        )
        
        if not data:
            return []
        
        return data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
    
    def get_team_info(self, team_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific team.
        
        Args:
            team_id: Team slug (e.g., "lal", "bos")
            
        Returns:
            Team info dictionary or None
        """
        endpoint = f"{self.BASE_URL}/teams/{team_id}"
        cache_key = f"espn:team_info:{team_id}:1h"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.ESPN,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=3600,  # 1 hour
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
        )
        
        return data
    
    def get_team_roster(self, team_id: str) -> List[Dict[str, Any]]:
        """
        Get team roster.
        
        Args:
            team_id: Team slug (e.g., "lal", "bos")
            
        Returns:
            List of player dictionaries
        """
        endpoint = f"{self.BASE_URL}/teams/{team_id}/roster"
        cache_key = f"espn:team_roster:{team_id}:1h"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.ESPN,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=3600,  # 1 hour
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
        )
        
        if not data:
            return []
        
        return data.get("athletes", [])
    
    def get_team_schedule(self, team_id: str) -> List[Dict[str, Any]]:
        """
        Get team schedule (upcoming and past games).
        
        Args:
            team_id: Team slug (e.g., "lal", "bos")
            
        Returns:
            List of game dictionaries
        """
        endpoint = f"{self.BASE_URL}/teams/{team_id}/schedule"
        cache_key = f"espn:team_schedule:{team_id}:1h"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.ESPN,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=3600,  # 1 hour
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
        )
        
        if not data:
            return []
        
        return data.get("events", [])
    
    def get_player_info(self, player_id: str) -> Optional[Dict[str, Any]]:
        """
        Get player information.
        
        Args:
            player_id: Player ID
            
        Returns:
            Player info dictionary or None
        """
        endpoint = f"{self.BASE_URL}/players/{player_id}"
        cache_key = f"espn:player_info:{player_id}:1h"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.ESPN,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=3600,  # 1 hour
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
        )
        
        return data
    
    def get_standings(self) -> Optional[Dict[str, Any]]:
        """
        Get league and conference standings.
        
        Returns:
            Standings data dictionary or None
        """
        endpoint = f"{self.BASE_URL}/standings"
        cache_key = "espn:standings:1h"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.ESPN,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=3600,  # 1 hour for standings
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
        )
        
        return data
    
    def get_news(self) -> List[Dict[str, Any]]:
        """
        Get NBA news feed.
        
        Returns:
            List of news article dictionaries
        """
        endpoint = f"{self.BASE_URL}/news"
        cache_key = "espn:news:15m"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.ESPN,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=900,  # 15 minutes
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
        )
        
        if not data:
            return []
        
        return data.get("articles", [])
    
    def get_injuries(self) -> Optional[Dict[str, Any]]:
        """
        Get injury reports per team.
        
        Returns:
            Injuries data dictionary or None
        """
        endpoint = f"{self.BASE_URL}/injuries"
        cache_key = "espn:injuries:15m"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.ESPN,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=900,  # 15 minutes
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
        )
        
        return data
    
    def get_transactions(self) -> List[Dict[str, Any]]:
        """
        Get recent trades and signings.
        
        Returns:
            List of transaction dictionaries
        """
        endpoint = f"{self.BASE_URL}/transactions"
        cache_key = "espn:transactions:15m"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.ESPN,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=900,  # 15 minutes
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
        )
        
        if not data:
            return []
        
        return data.get("transactions", [])


# Global service instance
_service: Optional[ESPNService] = None


def get_espn_service() -> ESPNService:
    """Get or create the global ESPN service instance"""
    global _service
    if _service is None:
        _service = ESPNService()
    return _service

