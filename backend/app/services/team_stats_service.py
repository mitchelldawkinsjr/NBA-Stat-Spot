"""
Team Stats Service - Fetches team season statistics
Uses NBADataService and caches team stats for over/under analysis
"""

from typing import Dict, Optional
from datetime import datetime
import structlog
from ..core.config import current_candidate_season
from .nba_api_service import NBADataService
from .over_under_service import TeamStats
from .cache_service import get_cache_service

logger = structlog.get_logger()

# Try to import nba_api team dashboard endpoint
try:
    from nba_api.stats.endpoints import teamdashboardbygeneralsplits
    NBA_API_AVAILABLE = True
except ImportError:
    NBA_API_AVAILABLE = False
    logger.warning("nba_api teamdashboardbygeneralsplits not available")


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
        
        # Try to fetch actual team stats from NBA API
        if NBA_API_AVAILABLE:
            team_stats = self._fetch_team_stats_from_nba(normalized_name)
            
            if team_stats:
                # Cache successful result
                stats_dict = {
                    'team_name': team_stats.team_name,
                    'ppg': team_stats.ppg,
                    'pace': team_stats.pace,
                    'home_ppg': team_stats.home_ppg,
                    'away_ppg': team_stats.away_ppg
                }
                self.cache.set(cache_key, stats_dict, ttl=86400)  # Cache for 24 hours
                self._team_stats_cache[normalized_name] = team_stats
                logger.info("Fetched team stats from NBA API", team=normalized_name, ppg=team_stats.ppg, pace=team_stats.pace)
                return team_stats
            else:
                logger.debug("NBA API fetch returned None, using defaults", team=normalized_name)
        else:
            logger.debug("NBA API not available, using defaults", team=normalized_name)
        
        # Fallback to default league averages if fetch fails
        logger.warning("Failed to fetch team stats, using defaults", team=normalized_name)
        default_stats = TeamStats(
            team_name=normalized_name,
            ppg=112.5,  # League average PPG
            pace=100.0,  # League average pace
            home_ppg=113.0,
            away_ppg=112.0
        )
        
        # Cache defaults for shorter time (1 hour) since they're fallbacks
        stats_dict = {
            'team_name': default_stats.team_name,
            'ppg': default_stats.ppg,
            'pace': default_stats.pace,
            'home_ppg': default_stats.home_ppg,
            'away_ppg': default_stats.away_ppg
        }
        self.cache.set(cache_key, stats_dict, ttl=3600)
        self._team_stats_cache[normalized_name] = default_stats
        
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
    
    def _get_team_id_from_name(self, team_name: str) -> Optional[int]:
        """Get NBA team ID from team name/abbreviation"""
        try:
            teams = NBADataService.fetch_all_teams()
            if not teams:
                return None
            
            # Try exact match first
            for team in teams:
                if (team.get("abbreviation", "").upper() == team_name.upper() or
                    team.get("full_name", "").upper() == team_name.upper() or
                    team.get("nickname", "").upper() == team_name.upper()):
                    return team.get("id")
            
            return None
        except Exception as e:
            logger.warning("Error fetching teams for ID lookup", error=str(e))
            return None
    
    def _fetch_team_stats_from_nba(self, team_name: str) -> Optional[TeamStats]:
        """
        Fetch actual team statistics from NBA API
        
        Args:
            team_name: Normalized team abbreviation
            
        Returns:
            TeamStats object or None if fetch fails
        """
        if not NBA_API_AVAILABLE:
            return None
        
        try:
            # Get team ID
            team_id = self._get_team_id_from_name(team_name)
            if not team_id:
                logger.debug("Team ID not found", team=team_name)
                return None
            
            # Fetch team dashboard stats
            # Use current season from config
            season = current_candidate_season()
            
            dashboard = teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits(
                team_id=team_id,
                season=season,
                season_type_all_star="Regular Season"
            )
            
            data = dashboard.get_dict()
            result_sets = data.get("resultSets", [])
            
            if not result_sets:
                return None
            
            # Find the overall stats (first result set is usually overall)
            overall_stats = None
            for rs in result_sets:
                if rs.get("name") == "Overall":
                    overall_stats = rs
                    break
            
            if not overall_stats:
                # Try first result set if no "Overall" found
                overall_stats = result_sets[0]
            
            headers = overall_stats.get("headers", [])
            rows = overall_stats.get("rowSet", [])
            
            if not rows or not headers:
                return None
            
            # Get stats from first row
            row = rows[0]
            
            # Find column indices
            try:
                # Try to find PTS_PER_GAME first (more reliable)
                if "PTS_PER_GAME" in headers or "PTS_PG" in headers:
                    ppg_idx = headers.index("PTS_PER_GAME") if "PTS_PER_GAME" in headers else headers.index("PTS_PG")
                    ppg = float(row[ppg_idx]) if ppg_idx < len(row) and row[ppg_idx] else 112.5
                else:
                    # Calculate from total points and games played
                    pts_idx = headers.index("PTS")
                    gp_idx = headers.index("GP") if "GP" in headers else None
                    total_pts = float(row[pts_idx]) if pts_idx < len(row) else 0
                    games_played = float(row[gp_idx]) if gp_idx and gp_idx < len(row) and row[gp_idx] and row[gp_idx] > 0 else 1
                    ppg = total_pts / games_played if games_played > 0 else 112.5
                
                pace_idx = headers.index("PACE") if "PACE" in headers else None
            except (ValueError, IndexError, ZeroDivisionError) as e:
                logger.warning("Required columns not found in team dashboard", headers=headers, error=str(e))
                return None
            
            # Extract pace if available
            pace = float(row[pace_idx]) if pace_idx and pace_idx < len(row) and row[pace_idx] else 100.0
            
            # Try to get home/away splits
            home_ppg = ppg
            away_ppg = ppg
            
            # Look for home/away splits in other result sets
            for rs in result_sets:
                if rs.get("name") in ["Home", "Away"]:
                    split_headers = rs.get("headers", [])
                    split_rows = rs.get("rowSet", [])
                    if split_rows and split_headers:
                        try:
                            split_row = split_rows[0]
                            # Try PTS_PER_GAME first, then calculate from totals
                            if "PTS_PER_GAME" in split_headers or "PTS_PG" in split_headers:
                                split_ppg_idx = split_headers.index("PTS_PER_GAME") if "PTS_PER_GAME" in split_headers else split_headers.index("PTS_PG")
                                split_ppg = float(split_row[split_ppg_idx]) if split_ppg_idx < len(split_row) and split_row[split_ppg_idx] else ppg
                            else:
                                split_pts_idx = split_headers.index("PTS")
                                split_gp_idx = split_headers.index("GP") if "GP" in split_headers else None
                                split_total_pts = float(split_row[split_pts_idx]) if split_pts_idx < len(split_row) else 0
                                split_games = float(split_row[split_gp_idx]) if split_gp_idx and split_gp_idx < len(split_row) and split_row[split_gp_idx] and split_row[split_gp_idx] > 0 else 1
                                split_ppg = split_total_pts / split_games if split_games > 0 else ppg
                            
                            if rs.get("name") == "Home":
                                home_ppg = split_ppg
                            elif rs.get("name") == "Away":
                                away_ppg = split_ppg
                        except (ValueError, IndexError, ZeroDivisionError):
                            pass  # Use overall PPG if split fails
            
            return TeamStats(
                team_name=team_name,
                ppg=ppg,
                pace=pace,
                home_ppg=home_ppg,
                away_ppg=away_ppg
            )
            
        except Exception as e:
            logger.warning("Error fetching team stats from NBA API", team=team_name, error=str(e))
            return None

