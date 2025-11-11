"""
API-Sports.io Basketball Service
Integration with API-Sports.io Basketball API v1 for live NBA game data.
Documentation: https://api-sports.io/documentation/basketball/v1
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import structlog
from .external_api_client import get_external_api_client
from .external_api_rate_limiter import APIProvider

logger = structlog.get_logger()


class APINBAService:
    """
    Service for API-Sports.io Basketball integration.
    Provides live games, game details, player stats, and team stats.
    """
    
    BASE_URL = "https://v1.basketball.api-sports.io"
    
    def __init__(self):
        self.client = get_external_api_client()
        self.api_key = os.getenv("API_NBA_KEY")
        # Check if using RapidAPI (has X-RapidAPI-Key format) or direct API key
        self.use_rapidapi = os.getenv("API_NBA_USE_RAPIDAPI", "false").lower() == "true"
        
        if not self.api_key:
            logger.warning("API_NBA_KEY not set - API-Sports.io features will be unavailable")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API-Sports.io requests"""
        if self.use_rapidapi:
            # Via RapidAPI
            return {
                "X-RapidAPI-Key": self.api_key or "",
                "X-RapidAPI-Host": "v1.basketball.api-sports.io"
            }
        else:
            # Direct API key
            return {
                "x-apisports-key": self.api_key or ""
            }
    
    def get_live_games(self) -> List[Dict[str, Any]]:
        """
        Get all live NBA games.
        
        Returns:
            List of live game dictionaries
        """
        if not self.api_key:
            logger.warning("API_NBA_KEY not set, cannot fetch live games")
            return []
        
        endpoint = f"{self.BASE_URL}/games"
        params = {
            "live": "all",
            "league": "12"  # NBA league ID
        }
        cache_key = "api_sports:live_games:30s"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.API_NBA,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=30,  # 30 seconds for live data
            headers=self._get_headers(),
            params=params
        )
        
        if not data:
            return []
        
        # Parse API-Sports.io response format
        # Response structure: {"get": "games", "parameters": {}, "errors": [], "results": 0, "response": []}
        games = []
        response_data = data.get("response", [])
        
        for game in response_data:
            try:
                # API-Sports.io game structure
                # Handle flexible response formats
                date_obj = game.get("date", {})
                date_str = date_obj.get("start", "") if isinstance(date_obj, dict) else str(date_obj) if date_obj else ""
                
                status_obj = game.get("status", {})
                status_long = status_obj.get("long", "") if isinstance(status_obj, dict) else ""
                status_clock = status_obj.get("clock", "") if isinstance(status_obj, dict) else ""
                
                periods_obj = game.get("periods", {})
                period_current = periods_obj.get("current", 0) if isinstance(periods_obj, dict) else 0
                
                teams_obj = game.get("teams", {})
                home_team_obj = teams_obj.get("home", {})
                away_team_obj = teams_obj.get("away", {}) or teams_obj.get("visitors", {})
                
                scores_obj = game.get("scores", {})
                home_score = scores_obj.get("home", {})
                away_score = scores_obj.get("away", {}) or scores_obj.get("visitors", {})
                
                game_info = {
                    "game_id": str(game.get("id", "")),
                    "date": date_str,
                    "status": status_long,
                    "period": period_current,
                    "time_remaining": status_clock,
                    "home_team": {
                        "id": str(home_team_obj.get("id", "")) if isinstance(home_team_obj, dict) else "",
                        "name": home_team_obj.get("name", "") if isinstance(home_team_obj, dict) else "",
                        "code": home_team_obj.get("code", "") if isinstance(home_team_obj, dict) else "",
                        "score": home_score.get("points", 0) if isinstance(home_score, dict) else (home_score if isinstance(home_score, (int, float)) else 0)
                    },
                    "away_team": {
                        "id": str(away_team_obj.get("id", "")) if isinstance(away_team_obj, dict) else "",
                        "name": away_team_obj.get("name", "") if isinstance(away_team_obj, dict) else "",
                        "code": away_team_obj.get("code", "") if isinstance(away_team_obj, dict) else "",
                        "score": away_score.get("points", 0) if isinstance(away_score, dict) else (away_score if isinstance(away_score, (int, float)) else 0)
                    }
                }
                games.append(game_info)
            except Exception as e:
                logger.warning("Error parsing API-Sports.io game", error=str(e), game_data=game)
                continue
        
        return games
    
    def get_game_details(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific game.
        
        Args:
            game_id: Game ID
            
        Returns:
            Game details dictionary or None
        """
        if not self.api_key:
            return None
        
        endpoint = f"{self.BASE_URL}/games"
        params = {"id": game_id}
        cache_key = f"api_sports:game:{game_id}:5m"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.API_NBA,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=300,  # 5 minutes
            headers=self._get_headers(),
            params=params
        )
        
        if not data:
            return None
        
        return data.get("response", [{}])[0] if data.get("response") else None
    
    def get_player_stats(
        self, 
        player_id: str, 
        season: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get player statistics.
        
        Args:
            player_id: Player ID
            season: Optional season (e.g., "2024" or "2024-2025")
            
        Returns:
            Player stats dictionary or None
        """
        if not self.api_key:
            return None
        
        endpoint = f"{self.BASE_URL}/players/statistics"
        params = {"player": player_id, "league": "12"}  # 12 is NBA league ID
        if season:
            params["season"] = season
        
        cache_key = f"api_sports:player_stats:{player_id}:{season or 'current'}:1h"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.API_NBA,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=3600,  # 1 hour
            headers=self._get_headers(),
            params=params
        )
        
        if not data:
            return None
        
        return data.get("response", [{}])[0] if data.get("response") else None
    
    def get_team_stats(
        self, 
        team_id: str, 
        season: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get team statistics.
        
        Args:
            team_id: Team ID
            season: Optional season (e.g., "2024" or "2024-2025")
            
        Returns:
            Team stats dictionary or None
        """
        if not self.api_key:
            return None
        
        endpoint = f"{self.BASE_URL}/teams/statistics"
        params = {"team": team_id, "league": "12"}  # 12 is NBA league ID
        if season:
            params["season"] = season
        
        cache_key = f"api_sports:team_stats:{team_id}:{season or 'current'}:1h"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.API_NBA,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=3600,  # 1 hour
            headers=self._get_headers(),
            params=params
        )
        
        if not data:
            return None
        
        return data.get("response", [{}])[0] if data.get("response") else None
    
    def get_team_roster(self, team_id: str) -> List[Dict[str, Any]]:
        """
        Get team roster.
        
        Args:
            team_id: Team ID
            
        Returns:
            List of player dictionaries
        """
        if not self.api_key:
            return []
        
        endpoint = f"{self.BASE_URL}/players"
        params = {"team": team_id, "league": "12"}  # 12 is NBA league ID
        
        cache_key = f"api_sports:team_roster:{team_id}:1h"
        
        data = self.client.get_with_rate_limit(
            provider=APIProvider.API_NBA,
            endpoint=endpoint,
            cache_key=cache_key,
            ttl=3600,  # 1 hour
            headers=self._get_headers(),
            params=params
        )
        
        if not data:
            return []
        
        return data.get("response", [])


# Global service instance
_service: Optional[APINBAService] = None


def get_api_nba_service() -> APINBAService:
    """Get or create the global API-Sports.io Basketball service instance"""
    global _service
    if _service is None:
        _service = APINBAService()
    return _service

