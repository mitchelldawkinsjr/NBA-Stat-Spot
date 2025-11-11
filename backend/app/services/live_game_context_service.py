"""
Live Game Context Service - Extracts real-time game features from ESPN
"""
from __future__ import annotations
from typing import Dict, Optional, Any, List
import structlog
from .espn_api_service import get_espn_service
from .espn_mapping_service import get_espn_mapping_service
from .cache_service import get_cache_service

logger = structlog.get_logger()


class LiveGameContextService:
    """Service to extract live game context from ESPN play-by-play and gamecast"""
    
    def __init__(self):
        self.espn_service = get_espn_service()
        self.mapping_service = get_espn_mapping_service()
        self.cache = get_cache_service()
    
    def extract_live_context(self, game_id: str, player_id: int) -> Dict[str, Any]:
        """
        Extract live game context for a player.
        
        Args:
            game_id: ESPN game ID
            player_id: NBA player ID
            
        Returns:
            Dictionary with live context:
            - current_pace: float
            - player_current_stats: dict
            - player_fouls: int
            - minutes_played: float
            - game_situation: str (close/blowout)
            - projected_minutes_remaining: float
        """
        try:
            cache_key = f"live_context:{game_id}:{player_id}:30s"
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # Get play-by-play
            playbyplay = self.espn_service.get_play_by_play(game_id)
            gamecast = self.espn_service.get_gamecast(game_id)
            summary = self.espn_service.get_game_summary(game_id)
            
            if not playbyplay and not gamecast and not summary:
                return self._get_default_live_context()
            
            # Extract current pace
            current_pace = self._calculate_current_pace(summary, gamecast)
            
            # Extract player stats
            player_stats = self._extract_player_stats(summary, player_id)
            
            # Extract fouls from play-by-play
            player_fouls = self._count_player_fouls(playbyplay, player_id)
            
            # Calculate minutes played
            minutes_played = player_stats.get("minutes", 0.0)
            
            # Determine game situation
            game_situation = self._determine_game_situation(summary, gamecast)
            
            # Project minutes remaining
            projected_minutes = self._project_minutes_remaining(
                minutes_played, game_situation, player_fouls
            )
            
            result = {
                "live_pace": current_pace,
                "player_current_stats": player_stats,
                "player_fouls": player_fouls,
                "minutes_played": minutes_played,
                "game_situation": game_situation,
                "projected_minutes_remaining": projected_minutes,
                "foul_trouble_score": self._calculate_foul_trouble_score(player_fouls),
                "game_flow_score": self._calculate_game_flow_score(game_situation)
            }
            
            self.cache.set(cache_key, result, ttl=30)  # 30 seconds for live data
            return result
            
        except Exception as e:
            logger.warning("Error extracting live context", game_id=game_id, player_id=player_id, error=str(e))
            return self._get_default_live_context()
    
    def get_live_game_features(self, game_id: str) -> Dict[str, Any]:
        """
        Get live game features for over/under analysis.
        
        Args:
            game_id: ESPN game ID
            
        Returns:
            Dictionary with live game features
        """
        try:
            cache_key = f"live_game_features:{game_id}:30s"
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            gamecast = self.espn_service.get_gamecast(game_id)
            summary = self.espn_service.get_game_summary(game_id)
            
            if not gamecast and not summary:
                return self._get_default_game_features()
            
            # Extract features
            current_pace = self._calculate_current_pace(summary, gamecast)
            shooting_efficiency = self._calculate_shooting_efficiency(summary, gamecast)
            turnover_rate = self._calculate_turnover_rate(summary, gamecast)
            free_throw_rate = self._calculate_free_throw_rate(summary, gamecast)
            
            result = {
                "live_pace": current_pace,
                "shooting_efficiency": shooting_efficiency,
                "turnover_rate": turnover_rate,
                "free_throw_rate": free_throw_rate,
                "foul_situation_impact": self._calculate_foul_impact(summary)
            }
            
            self.cache.set(cache_key, result, ttl=30)  # 30 seconds
            return result
            
        except Exception as e:
            logger.warning("Error getting live game features", game_id=game_id, error=str(e))
            return self._get_default_game_features()
    
    def _calculate_current_pace(
        self, 
        summary: Optional[Dict[str, Any]], 
        gamecast: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate current pace (points per 48 minutes)"""
        try:
            if summary:
                competitions = summary.get("header", {}).get("competitions", [])
                if competitions:
                    comp = competitions[0]
                    status = comp.get("status", {})
                    period = status.get("period", 0)
                    clock = status.get("displayClock", "")
                    
                    # Calculate time elapsed
                    time_elapsed = self._parse_time_elapsed(period, clock)
                    
                    # Get current score
                    competitors = comp.get("competitors", [])
                    total_score = sum(
                        int(c.get("score", "0") or 0) 
                        for c in competitors
                    )
                    
                    if time_elapsed > 0:
                        return (total_score / time_elapsed) * 48
            return 0.0
        except Exception:
            return 0.0
    
    def _parse_time_elapsed(self, period: int, clock: str) -> float:
        """Parse time elapsed from period and clock"""
        # Each period is 12 minutes
        period_minutes = (period - 1) * 12 if period > 0 else 0
        
        # Parse clock (MM:SS format)
        clock_minutes = 0.0
        if clock and ":" in clock:
            try:
                parts = clock.split(":")
                minutes = int(parts[0])
                seconds = int(parts[1])
                clock_minutes = minutes + (seconds / 60.0)
            except Exception:
                clock_minutes = 12.0  # Default to full period
        
        return period_minutes + (12.0 - clock_minutes)
    
    def _extract_player_stats(
        self, 
        summary: Optional[Dict[str, Any]], 
        player_id: int
    ) -> Dict[str, Any]:
        """Extract current player stats from game summary"""
        try:
            if not summary:
                return {"pts": 0, "reb": 0, "ast": 0, "minutes": 0.0}
            
            # Get ESPN player ID
            espn_player_id = self.mapping_service.get_espn_player_id(player_id)
            if not espn_player_id:
                return {"pts": 0, "reb": 0, "ast": 0, "minutes": 0.0}
            
            # Search for player in box score
            boxscore = summary.get("boxscore", {})
            players = boxscore.get("players", [])
            
            for player in players:
                athlete = player.get("athlete", {})
                if str(athlete.get("id")) == str(espn_player_id):
                    stats = player.get("statistics", [])
                    stat_dict = {}
                    for stat in stats:
                        stat_dict[stat.get("name", "").lower()] = stat.get("value", 0)
                    
                    return {
                        "pts": stat_dict.get("points", 0),
                        "reb": stat_dict.get("rebounds", 0),
                        "ast": stat_dict.get("assists", 0),
                        "minutes": float(stat_dict.get("minutes", 0))
                    }
            
            return {"pts": 0, "reb": 0, "ast": 0, "minutes": 0.0}
        except Exception:
            return {"pts": 0, "reb": 0, "ast": 0, "minutes": 0.0}
    
    def _count_player_fouls(
        self, 
        playbyplay: Optional[Dict[str, Any]], 
        player_id: int
    ) -> int:
        """Count player fouls from play-by-play"""
        try:
            if not playbyplay:
                return 0
            
            # Get ESPN player ID
            espn_player_id = self.mapping_service.get_espn_player_id(player_id)
            if not espn_player_id:
                return 0
            
            fouls = 0
            periods = playbyplay.get("periods", [])
            
            for period in periods:
                plays = period.get("plays", [])
                for play in plays:
                    # Check if play involves player foul
                    athletes = play.get("athletesInvolved", [])
                    for athlete in athletes:
                        if str(athlete.get("id")) == str(espn_player_id):
                            text = play.get("text", "").lower()
                            if "foul" in text or "personal" in text:
                                fouls += 1
            
            return fouls
        except Exception:
            return 0
    
    def _determine_game_situation(
        self, 
        summary: Optional[Dict[str, Any]], 
        gamecast: Optional[Dict[str, Any]]
    ) -> str:
        """Determine if game is close or blowout"""
        try:
            if summary:
                competitions = summary.get("header", {}).get("competitions", [])
                if competitions:
                    comp = competitions[0]
                    competitors = comp.get("competitors", [])
                    if len(competitors) == 2:
                        scores = [int(c.get("score", "0") or 0) for c in competitors]
                        diff = abs(scores[0] - scores[1])
                        
                        if diff <= 5:
                            return "close"
                        elif diff >= 20:
                            return "blowout"
                        else:
                            return "moderate"
            return "unknown"
        except Exception:
            return "unknown"
    
    def _project_minutes_remaining(
        self, 
        minutes_played: float, 
        game_situation: str, 
        fouls: int
    ) -> float:
        """Project minutes remaining for player"""
        # Base projection: assume player plays ~32 minutes total
        base_minutes = 32.0
        remaining = max(0, base_minutes - minutes_played)
        
        # Adjust for game situation
        if game_situation == "blowout":
            remaining *= 0.7  # Less minutes in blowout
        elif game_situation == "close":
            remaining *= 1.1  # More minutes in close game
        
        # Adjust for foul trouble
        if fouls >= 4:
            remaining *= 0.5  # Significant foul trouble
        elif fouls >= 3:
            remaining *= 0.8  # Some foul trouble
        
        return remaining
    
    def _calculate_foul_trouble_score(self, fouls: int) -> float:
        """Calculate foul trouble score (0-1, higher = more trouble)"""
        if fouls >= 5:
            return 1.0
        elif fouls >= 4:
            return 0.8
        elif fouls >= 3:
            return 0.5
        else:
            return 0.0
    
    def _calculate_game_flow_score(self, game_situation: str) -> float:
        """Calculate game flow score (0-1, higher = more competitive)"""
        if game_situation == "close":
            return 1.0
        elif game_situation == "moderate":
            return 0.6
        elif game_situation == "blowout":
            return 0.2
        else:
            return 0.5
    
    def _calculate_shooting_efficiency(
        self, 
        summary: Optional[Dict[str, Any]], 
        gamecast: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate shooting efficiency"""
        # Would need to extract FG% from summary/gamecast
        # Simplified for now
        return 0.45  # Default 45%
    
    def _calculate_turnover_rate(
        self, 
        summary: Optional[Dict[str, Any]], 
        gamecast: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate turnover rate"""
        # Would need to extract turnovers from summary
        return 0.12  # Default 12%
    
    def _calculate_free_throw_rate(
        self, 
        summary: Optional[Dict[str, Any]], 
        gamecast: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate free throw rate"""
        # Would need to extract FTA from summary
        return 0.20  # Default 20%
    
    def _calculate_foul_impact(self, summary: Optional[Dict[str, Any]]) -> float:
        """Calculate impact of foul situation on scoring"""
        # Simplified - would need team foul counts
        return 0.0
    
    def _get_default_live_context(self) -> Dict[str, Any]:
        """Return default live context"""
        return {
            "live_pace": 0.0,
            "player_current_stats": {"pts": 0, "reb": 0, "ast": 0, "minutes": 0.0},
            "player_fouls": 0,
            "minutes_played": 0.0,
            "game_situation": "unknown",
            "projected_minutes_remaining": 0.0,
            "foul_trouble_score": 0.0,
            "game_flow_score": 0.5
        }
    
    def _get_default_game_features(self) -> Dict[str, Any]:
        """Return default game features"""
        return {
            "live_pace": 0.0,
            "shooting_efficiency": 0.45,
            "turnover_rate": 0.12,
            "free_throw_rate": 0.20,
            "foul_situation_impact": 0.0
        }


# Global service instance
_live_context_service: Optional[LiveGameContextService] = None


def get_live_game_context_service() -> LiveGameContextService:
    """Get or create the global live game context service instance"""
    global _live_context_service
    if _live_context_service is None:
        _live_context_service = LiveGameContextService()
    return _live_context_service

