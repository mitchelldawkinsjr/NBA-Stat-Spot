"""
Team Standings Service - Extracts team context from ESPN standings
"""
from __future__ import annotations
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
import structlog
from .espn_api_service import get_espn_service
from .espn_mapping_service import get_espn_mapping_service
from .cache_service import get_cache_service

logger = structlog.get_logger()


class TeamStandingsService:
    """Service to extract team context from ESPN standings"""
    
    def __init__(self):
        self.espn_service = get_espn_service()
        self.mapping_service = get_espn_mapping_service()
        self.cache = get_cache_service()
    
    def get_team_standings_context(self, team_id: int) -> Dict[str, Any]:
        """
        Get team standings context from ESPN.
        
        Args:
            team_id: NBA team ID
            
        Returns:
            Dictionary with standings context:
            - conference_rank: int
            - division_rank: int
            - win_loss_record: dict with wins, losses
            - recent_form: float (last 10 games win %)
            - home_record: dict
            - away_record: dict
            - playoff_race_pressure: float (0-1)
        """
        try:
            cache_key = f"team_standings:{team_id}:1h"
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # Get ESPN team slug
            espn_slug = self.mapping_service.get_espn_team_slug(team_id)
            if not espn_slug:
                return self._get_default_context()
            
            # Fetch standings
            standings_data = self.espn_service.get_standings()
            if not standings_data:
                return self._get_default_context()
            
            # Parse standings structure
            # ESPN standings structure: children -> [conferences] -> [divisions] -> [teams]
            children = standings_data.get("children", [])
            
            team_info = None
            conference_rank = None
            division_rank = None
            conference_name = None
            division_name = None
            
            # Search through conferences and divisions
            for conference in children:
                conf_name = conference.get("name", "")
                divisions = conference.get("children", [])
                
                for division in divisions:
                    div_name = division.get("name", "")
                    teams = division.get("standings", {}).get("entries", [])
                    
                    for idx, team_entry in enumerate(teams):
                        team_data = team_entry.get("team", {})
                        if team_data.get("slug") == espn_slug:
                            team_info = team_entry
                            division_rank = idx + 1
                            division_name = div_name
                            conference_name = conf_name
                            break
                    
                    if team_info:
                        break
                
                if team_info:
                    # Calculate conference rank
                    all_conf_teams = []
                    for div in conference.get("children", []):
                        all_conf_teams.extend(div.get("standings", {}).get("entries", []))
                    
                    # Sort by win percentage
                    all_conf_teams.sort(
                        key=lambda x: x.get("stats", [{}])[0].get("value", 0) if x.get("stats") else 0,
                        reverse=True
                    )
                    
                    for idx, t in enumerate(all_conf_teams):
                        if t.get("team", {}).get("slug") == espn_slug:
                            conference_rank = idx + 1
                            break
                    break
            
            if not team_info:
                return self._get_default_context()
            
            # Extract stats
            stats = team_info.get("stats", [])
            wins = 0
            losses = 0
            win_pct = 0.0
            
            for stat in stats:
                stat_type = stat.get("name", "")
                stat_value = stat.get("value", 0)
                
                if stat_type == "wins":
                    wins = int(stat_value)
                elif stat_type == "losses":
                    losses = int(stat_value)
                elif stat_type == "winPercent":
                    win_pct = float(stat_value)
            
            # Get recent form from team schedule (last 10 games)
            recent_form = self._calculate_recent_form(espn_slug)
            
            # Calculate playoff race pressure
            playoff_pressure = self._calculate_playoff_pressure(
                conference_rank, win_pct, conference_name
            )
            
            # Get home/away records (if available in stats)
            home_wins = 0
            home_losses = 0
            away_wins = 0
            away_losses = 0
            
            # Try to extract from additional stats
            for stat in stats:
                stat_type = stat.get("name", "")
                stat_value = stat.get("value", 0)
                if "home" in stat_type.lower() and "wins" in stat_type.lower():
                    home_wins = int(stat_value)
                elif "home" in stat_type.lower() and "losses" in stat_type.lower():
                    home_losses = int(stat_value)
                elif "away" in stat_type.lower() and "wins" in stat_type.lower():
                    away_wins = int(stat_value)
                elif "away" in stat_type.lower() and "losses" in stat_type.lower():
                    away_losses = int(stat_value)
            
            result = {
                "conference_rank": conference_rank,
                "division_rank": division_rank,
                "conference_name": conference_name,
                "division_name": division_name,
                "win_loss_record": {
                    "wins": wins,
                    "losses": losses,
                    "win_percentage": win_pct
                },
                "recent_form": recent_form,
                "home_record": {
                    "wins": home_wins,
                    "losses": home_losses
                },
                "away_record": {
                    "wins": away_wins,
                    "losses": away_losses
                },
                "playoff_race_pressure": playoff_pressure
            }
            
            # Cache for 1 hour
            self.cache.set(cache_key, result, ttl=3600)
            return result
            
        except Exception as e:
            logger.warning("Error fetching team standings", team_id=team_id, error=str(e))
            return self._get_default_context()
    
    def _calculate_recent_form(self, espn_slug: str) -> float:
        """
        Calculate recent form (last 10 games win %) from team schedule.
        
        Args:
            espn_slug: ESPN team slug
            
        Returns:
            Win percentage for last 10 games (0.0 to 1.0)
        """
        try:
            schedule = self.espn_service.get_team_schedule(espn_slug)
            if not schedule:
                return 0.5  # Default
            
            # Filter completed games
            completed_games = []
            for event in schedule:
                competitions = event.get("competitions", [])
                if not competitions:
                    continue
                
                comp = competitions[0]
                status = comp.get("status", {})
                status_type = status.get("type", {})
                
                # Check if game is completed
                if status_type.get("id") == 3 or status_type.get("name") == "STATUS_FINAL":
                    completed_games.append(event)
            
            # Get last 10 completed games
            recent_games = completed_games[-10:] if len(completed_games) >= 10 else completed_games
            
            if not recent_games:
                return 0.5  # Default if no games
            
            wins = 0
            for game in recent_games:
                competitions = game.get("competitions", [])
                if not competitions:
                    continue
                
                comp = competitions[0]
                competitors = comp.get("competitors", [])
                
                # Find team's result
                for competitor in competitors:
                    team_data = competitor.get("team", {})
                    if team_data.get("slug") == espn_slug:
                        winner = competitor.get("winner", False)
                        if winner:
                            wins += 1
                        break
            
            return wins / len(recent_games) if recent_games else 0.5
            
        except Exception as e:
            logger.warning("Error calculating recent form", espn_slug=espn_slug, error=str(e))
            return 0.5
    
    def _calculate_playoff_pressure(
        self, 
        conference_rank: Optional[int], 
        win_pct: float, 
        conference_name: Optional[str]
    ) -> float:
        """
        Calculate playoff race pressure score (0-1).
        Higher score = more pressure (fighting for playoff spot).
        
        Args:
            conference_rank: Conference rank (1-15)
            win_pct: Win percentage
            conference_name: Conference name
            
        Returns:
            Pressure score (0.0 to 1.0)
        """
        if conference_rank is None:
            return 0.0
        
        # Higher pressure if:
        # - Rank 7-10 (play-in tournament range)
        # - Rank 11-12 (just outside, fighting to get in)
        # - Rank 5-6 (fighting for home court)
        
        if conference_rank <= 4:
            # Top 4 - secure playoff spot, lower pressure
            return 0.2
        elif conference_rank in [5, 6]:
            # Fighting for home court advantage
            return 0.6
        elif conference_rank in [7, 8, 9, 10]:
            # Play-in tournament range - high pressure
            return 0.9
        elif conference_rank in [11, 12]:
            # Just outside - very high pressure
            return 0.95
        else:
            # Lower ranks - less pressure
            return 0.3
    
    def _get_default_context(self) -> Dict[str, Any]:
        """Return default context when data unavailable"""
        return {
            "conference_rank": None,
            "division_rank": None,
            "conference_name": None,
            "division_name": None,
            "win_loss_record": {
                "wins": 0,
                "losses": 0,
                "win_percentage": 0.0
            },
            "recent_form": 0.5,
            "home_record": {
                "wins": 0,
                "losses": 0
            },
            "away_record": {
                "wins": 0,
                "losses": 0
            },
            "playoff_race_pressure": 0.0
        }


# Global service instance
_standings_service: Optional[TeamStandingsService] = None


def get_team_standings_service() -> TeamStandingsService:
    """Get or create the global team standings service instance"""
    global _standings_service
    if _standings_service is None:
        _standings_service = TeamStandingsService()
    return _standings_service

