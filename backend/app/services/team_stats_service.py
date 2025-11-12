"""
Team Stats Service - Fetches team season statistics
Uses NBADataService and caches team stats for over/under analysis
"""

from typing import Dict, Optional
from datetime import datetime
import structlog
from .nba_api_service import NBADataService
from .over_under_service import TeamStats
from .cache_service import get_cache_service

logger = structlog.get_logger()


class TeamStatsService:
    """Service to fetch and cache team season statistics"""
    
    def __init__(self):
        self.cache = get_cache_service()
        self._team_stats_cache: Dict[str, TeamStats] = {}
    
    def get_team_stats(self, team_name: str) -> TeamStats:
        """
        Get team season statistics for a given team
        
        Args:
            team_name: Team name, abbreviation, or tricode (e.g., "Lakers", "LAL", "Los Angeles Lakers")
            
        Returns:
            TeamStats object with PPG, pace, etc.
            Falls back to league averages if team not found
        """
        # Normalize team name
        normalized_name = self._normalize_team_name(team_name)
        
        # Check cache first
        cache_key = f"team_stats:{normalized_name}"
        cached_stats = self.cache.get(cache_key)
        if cached_stats:
            # Convert dict back to TeamStats object
            if isinstance(cached_stats, dict):
                return TeamStats(
                    team_name=cached_stats.get('team_name', normalized_name),
                    ppg=cached_stats.get('ppg', 112.5),
                    pace=cached_stats.get('pace', 100.0),
                    home_ppg=cached_stats.get('home_ppg', 113.0),
                    away_ppg=cached_stats.get('away_ppg', 112.0)
                )
            return cached_stats
        
        # Check in-memory cache
        if normalized_name in self._team_stats_cache:
            return self._team_stats_cache[normalized_name]
        
        # Try to fetch from NBA API
        # For now, we'll use default league averages
        # In a full implementation, we'd fetch team stats from NBA API
        # This is a placeholder that can be enhanced later
        
        # Default league averages (2024-25 season approximate)
        default_stats = TeamStats(
            team_name=normalized_name,
            ppg=112.5,  # League average PPG
            pace=100.0,  # League average pace
            home_ppg=113.0,
            away_ppg=112.0
        )
        
        # Cache for 24 hours (convert TeamStats to dict for JSON serialization)
        stats_dict = {
            'team_name': default_stats.team_name,
            'ppg': default_stats.ppg,
            'pace': default_stats.pace,
            'home_ppg': default_stats.home_ppg,
            'away_ppg': default_stats.away_ppg
        }
        self.cache.set(cache_key, stats_dict, ttl=86400)
        self._team_stats_cache[normalized_name] = default_stats
        
        logger.info("Using default team stats", team=normalized_name)
        return default_stats
    
    def update_team_stats(self) -> Dict[str, TeamStats]:
        """
        Refresh team statistics from NBA API
        This can be called daily to update team stats
        
        Returns:
            Dictionary mapping team names to TeamStats
        """
        # This is a placeholder for future implementation
        # In a full implementation, we would:
        # 1. Fetch team stats from NBA API (teamdashboardbygeneralsplits endpoint)
        # 2. Calculate PPG, pace, home/away splits
        # 3. Cache the results
        
        logger.info("Team stats update called - using defaults for now")
        
        # For now, return empty dict - will use defaults when get_team_stats is called
        return {}
    
    def _normalize_team_name(self, team_name: str) -> str:
        """
        Normalize team name to a standard format
        
        Args:
            team_name: Team name in various formats
            
        Returns:
            Normalized team name
        """
        if not team_name:
            return "DEFAULT"
        
        # Convert to uppercase for consistency
        normalized = team_name.upper().strip()
        
        # Map common variations to standard abbreviations
        team_mapping = {
            "LAKERS": "LAL",
            "LOS ANGELES LAKERS": "LAL",
            "WARRIORS": "GSW",
            "GOLDEN STATE WARRIORS": "GSW",
            "CELTICS": "BOS",
            "BOSTON CELTICS": "BOS",
            "HEAT": "MIA",
            "MIAMI HEAT": "MIA",
            "NUGGETS": "DEN",
            "DENVER NUGGETS": "DEN",
            "SUNS": "PHX",
            "PHOENIX SUNS": "PHX",
            "SIXERS": "PHI",
            "PHILADELPHIA 76ERS": "PHI",
            "76ERS": "PHI",
            "BUCKS": "MIL",
            "MILWAUKEE BUCKS": "MIL",
            "CLIPPERS": "LAC",
            "LA CLIPPERS": "LAC",
            "LOS ANGELES CLIPPERS": "LAC",
            "MAVERICKS": "DAL",
            "DALLAS MAVERICKS": "DAL",
            "KNICKS": "NYK",
            "NEW YORK KNICKS": "NYK",
            "NETS": "BKN",
            "BROOKLYN NETS": "BKN",
            "BULLS": "CHI",
            "CHICAGO BULLS": "CHI",
            "CAVALIERS": "CLE",
            "CLEVELAND CAVALIERS": "CLE",
            "PISTONS": "DET",
            "DETROIT PISTONS": "DET",
            "PACERS": "IND",
            "INDIANA PACERS": "IND",
            "HAWKS": "ATL",
            "ATLANTA HAWKS": "ATL",
            "HORNETS": "CHA",
            "CHARLOTTE HORNETS": "CHA",
            "WIZARDS": "WAS",
            "WASHINGTON WIZARDS": "WAS",
            "MAGIC": "ORL",
            "ORLANDO MAGIC": "ORL",
            "RAPTORS": "TOR",
            "TORONTO RAPTORS": "TOR",
            "ROCKETS": "HOU",
            "HOUSTON ROCKETS": "HOU",
            "SPURS": "SAS",
            "SAN ANTONIO SPURS": "SAS",
            "GRIZZLIES": "MEM",
            "MEMPHIS GRIZZLIES": "MEM",
            "PELICANS": "NOP",
            "NEW ORLEANS PELICANS": "NOP",
            "THUNDER": "OKC",
            "OKLAHOMA CITY THUNDER": "OKC",
            "TIMBERWOLVES": "MIN",
            "MINNESOTA TIMBERWOLVES": "MIN",
            "JAZZ": "UTA",
            "UTAH JAZZ": "UTA",
            "TRAIL BLAZERS": "POR",
            "PORTLAND TRAIL BLAZERS": "POR",
            "BLAZERS": "POR",
            "KINGS": "SAC",
            "SACRAMENTO KINGS": "SAC",
        }
        
        return team_mapping.get(normalized, normalized)

