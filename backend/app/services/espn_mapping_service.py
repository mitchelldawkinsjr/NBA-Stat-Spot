"""
ESPN-NBA Mapping Service
Maps between NBA API identifiers and ESPN identifiers (team slugs, player IDs/names)
"""
from __future__ import annotations
from typing import Dict, Optional, List, Any
from difflib import SequenceMatcher
import structlog
from .nba_api_service import NBADataService
from .espn_api_service import get_espn_service
from .cache_service import get_cache_service
from .team_player_service import TeamPlayerService

logger = structlog.get_logger()


class ESPNMappingService:
    """Service to map between NBA API and ESPN identifiers"""
    
    # Static mapping of NBA team IDs to ESPN team slugs
    # This is a fallback if API lookup fails
    NBA_TO_ESPN_TEAM_SLUGS: Dict[int, str] = {
        1610612737: "atl",  # Atlanta Hawks
        1610612738: "bos",  # Boston Celtics
        1610612751: "bkn",  # Brooklyn Nets
        1610612766: "cha",  # Charlotte Hornets
        1610612741: "chi",  # Chicago Bulls
        1610612739: "cle",  # Cleveland Cavaliers
        1610612742: "dal",  # Dallas Mavericks
        1610612743: "den",  # Denver Nuggets
        1610612765: "det",  # Detroit Pistons
        1610612744: "gs",   # Golden State Warriors
        1610612745: "hou",  # Houston Rockets
        1610612754: "ind",  # Indiana Pacers
        1610612746: "lac",  # LA Clippers
        1610612747: "lal",  # Los Angeles Lakers
        1610612763: "mem",  # Memphis Grizzlies
        1610612748: "mia",  # Miami Heat
        1610612749: "mil",  # Milwaukee Bucks
        1610612750: "min",  # Minnesota Timberwolves
        1610612740: "no",   # New Orleans Pelicans
        1610612752: "ny",   # New York Knicks
        1610612760: "okc",  # Oklahoma City Thunder
        1610612753: "orl",  # Orlando Magic
        1610612755: "phi",  # Philadelphia 76ers
        1610612756: "phx",  # Phoenix Suns
        1610612757: "por",  # Portland Trail Blazers
        1610612758: "sac",  # Sacramento Kings
        1610612759: "sa",   # San Antonio Spurs
        1610612761: "tor",  # Toronto Raptors
        1610612762: "uta",  # Utah Jazz
        1610612764: "wsh",  # Washington Wizards
    }
    
    def __init__(self):
        self.cache = get_cache_service()
        self.espn_service = get_espn_service()
        self._team_mapping_cache: Dict[int, Optional[str]] = {}
        self._player_mapping_cache: Dict[int, Optional[str]] = {}
    
    def get_espn_team_slug(self, nba_team_id: int) -> Optional[str]:
        """
        Get ESPN team slug from NBA team ID.
        
        Args:
            nba_team_id: NBA API team ID
            
        Returns:
            ESPN team slug (e.g., "lal") or None if not found
        """
        # Check cache first
        if nba_team_id in self._team_mapping_cache:
            return self._team_mapping_cache[nba_team_id]
        
        # Check static mapping
        if nba_team_id in self.NBA_TO_ESPN_TEAM_SLUGS:
            slug = self.NBA_TO_ESPN_TEAM_SLUGS[nba_team_id]
            self._team_mapping_cache[nba_team_id] = slug
            return slug
        
        # Try to fetch from ESPN API and match by abbreviation
        try:
            cache_key = f"espn:team_mapping:{nba_team_id}:24h"
            cached_slug = self.cache.get(cache_key)
            if cached_slug is not None:
                self._team_mapping_cache[nba_team_id] = cached_slug
                return cached_slug
            
            # Get NBA team info
            teams = NBADataService.fetch_all_teams()
            nba_team = next((t for t in teams if t.get("id") == nba_team_id), None)
            if not nba_team:
                self._team_mapping_cache[nba_team_id] = None
                return None
            
            nba_abbr = nba_team.get("abbreviation", "").lower()
            
            # Get ESPN teams
            espn_teams = self.espn_service.get_teams()
            for espn_team in espn_teams:
                team_data = espn_team.get("team", {})
                espn_abbr = team_data.get("abbreviation", "").lower()
                espn_slug = team_data.get("slug", "")
                
                if espn_abbr == nba_abbr or team_data.get("id") == str(nba_team_id):
                    self._team_mapping_cache[nba_team_id] = espn_slug
                    self.cache.set(cache_key, espn_slug, ttl=86400)  # 24 hours
                    return espn_slug
            
            # If not found, return None
            self._team_mapping_cache[nba_team_id] = None
            return None
        except Exception as e:
            logger.warning("Error mapping team to ESPN slug", nba_team_id=nba_team_id, error=str(e))
            self._team_mapping_cache[nba_team_id] = None
            return None
    
    def get_nba_team_id(self, espn_slug: str) -> Optional[int]:
        """
        Get NBA team ID from ESPN team slug.
        
        Args:
            espn_slug: ESPN team slug (e.g., "lal")
            
        Returns:
            NBA API team ID or None if not found
        """
        # Reverse lookup in static mapping
        for nba_id, slug in self.NBA_TO_ESPN_TEAM_SLUGS.items():
            if slug == espn_slug:
                return nba_id
        
        # Try API lookup
        try:
            cache_key = f"espn:team_reverse_mapping:{espn_slug}:24h"
            cached_id = self.cache.get(cache_key)
            if cached_id is not None:
                return cached_id
            
            espn_teams = self.espn_service.get_teams()
            for espn_team in espn_teams:
                team_data = espn_team.get("team", {})
                if team_data.get("slug") == espn_slug:
                    espn_id = team_data.get("id")
                    if espn_id:
                        # Try to match with NBA teams by abbreviation
                        espn_abbr = team_data.get("abbreviation", "").lower()
                        teams = NBADataService.fetch_all_teams()
                        for nba_team in teams:
                            if nba_team.get("abbreviation", "").lower() == espn_abbr:
                                nba_id = nba_team.get("id")
                                self.cache.set(cache_key, nba_id, ttl=86400)
                                return nba_id
            
            return None
        except Exception as e:
            logger.warning("Error mapping ESPN slug to NBA team ID", espn_slug=espn_slug, error=str(e))
            return None
    
    def _fuzzy_match_name(self, name1: str, name2: str) -> float:
        """
        Calculate similarity ratio between two names.
        
        Args:
            name1: First name
            name2: Second name
            
        Returns:
            Similarity ratio (0.0 to 1.0)
        """
        name1_clean = name1.lower().strip()
        name2_clean = name2.lower().strip()
        return SequenceMatcher(None, name1_clean, name2_clean).ratio()
    
    def match_player_by_name(self, player_name: str, team_id: int) -> Optional[str]:
        """
        Match NBA player by name and team to ESPN player ID.
        
        Args:
            player_name: Player's full name
            team_id: NBA team ID
            
        Returns:
            ESPN player ID or None if not found
        """
        try:
            # Get ESPN team slug
            espn_slug = self.get_espn_team_slug(team_id)
            if not espn_slug:
                return None
            
            cache_key = f"espn:player_mapping:{player_name}:{team_id}:24h"
            cached_id = self.cache.get(cache_key)
            if cached_id is not None:
                return cached_id
            
            # Get ESPN team roster
            roster = self.espn_service.get_team_roster(espn_slug)
            if not roster:
                return None
            
            # Try exact match first
            player_name_lower = player_name.lower().strip()
            for athlete in roster:
                athlete_data = athlete.get("athlete", {})
                espn_name = athlete_data.get("displayName", "") or athlete_data.get("fullName", "")
                if espn_name.lower().strip() == player_name_lower:
                    espn_id = athlete_data.get("id")
                    if espn_id:
                        self.cache.set(cache_key, espn_id, ttl=86400)
                        return espn_id
            
            # Try fuzzy matching
            best_match = None
            best_ratio = 0.7  # Minimum threshold
            
            for athlete in roster:
                athlete_data = athlete.get("athlete", {})
                espn_name = athlete_data.get("displayName", "") or athlete_data.get("fullName", "")
                if not espn_name:
                    continue
                
                ratio = self._fuzzy_match_name(player_name, espn_name)
                if ratio > best_ratio:
                    best_ratio = ratio
                    espn_id = athlete_data.get("id")
                    if espn_id:
                        best_match = espn_id
            
            if best_match:
                self.cache.set(cache_key, best_match, ttl=86400)
                return best_match
            
            return None
        except Exception as e:
            logger.warning("Error matching player by name", player_name=player_name, team_id=team_id, error=str(e))
            return None
    
    def get_espn_player_id(self, nba_player_id: int) -> Optional[str]:
        """
        Get ESPN player ID from NBA player ID.
        
        Args:
            nba_player_id: NBA API player ID
            
        Returns:
            ESPN player ID or None if not found
        """
        # Check cache first
        if nba_player_id in self._player_mapping_cache:
            return self._player_mapping_cache[nba_player_id]
        
        try:
            cache_key = f"espn:player_id_mapping:{nba_player_id}:24h"
            cached_id = self.cache.get(cache_key)
            if cached_id is not None:
                self._player_mapping_cache[nba_player_id] = cached_id
                return cached_id
            
            # Get NBA player info
            all_players = NBADataService.fetch_all_players_including_rookies()
            nba_player = next((p for p in all_players if p.get("id") == nba_player_id), None)
            if not nba_player:
                self._player_mapping_cache[nba_player_id] = None
                return None
            
            player_name = nba_player.get("full_name")
            team_id = TeamPlayerService.get_team_id_for_player(nba_player_id)
            
            if not player_name:
                self._player_mapping_cache[nba_player_id] = None
                return None
            
            # Use name matching
            espn_id = None
            if team_id:
                espn_id = self.match_player_by_name(player_name, team_id)
            
            # If not found with team, try searching all teams (slower)
            if not espn_id:
                espn_teams = self.espn_service.get_teams()
                for espn_team in espn_teams[:5]:  # Limit to avoid too many API calls
                    team_data = espn_team.get("team", {})
                    espn_slug = team_data.get("slug")
                    if espn_slug:
                        roster = self.espn_service.get_team_roster(espn_slug)
                        for athlete in roster:
                            athlete_data = athlete.get("athlete", {})
                            espn_name = athlete_data.get("displayName", "") or athlete_data.get("fullName", "")
                            if self._fuzzy_match_name(player_name, espn_name) > 0.9:
                                espn_id = athlete_data.get("id")
                                if espn_id:
                                    break
                        if espn_id:
                            break
            
            if espn_id:
                self._player_mapping_cache[nba_player_id] = espn_id
                self.cache.set(cache_key, espn_id, ttl=86400)
            
            return espn_id
        except Exception as e:
            logger.warning("Error mapping player ID", nba_player_id=nba_player_id, error=str(e))
            self._player_mapping_cache[nba_player_id] = None
            return None


# Global service instance
_mapping_service: Optional[ESPNMappingService] = None


def get_espn_mapping_service() -> ESPNMappingService:
    """Get or create the global ESPN mapping service instance"""
    global _mapping_service
    if _mapping_service is None:
        _mapping_service = ESPNMappingService()
    return _mapping_service

