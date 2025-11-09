"""
Game Status Monitor Service - Tracks game status and invalidates player log caches when games finish
"""
from __future__ import annotations
from typing import List, Set, Dict, Any, Optional
from datetime import datetime, date
from ..services.nba_api_service import NBADataService

# Track which games we've seen as finished (to avoid repeated cache invalidation)
_finished_games_today: Set[str] = set()
_last_check_date: Optional[date] = None


class GameStatusMonitor:
    @staticmethod
    def _reset_daily_tracking():
        """Reset finished games tracking at start of new day."""
        global _finished_games_today, _last_check_date
        today = datetime.now().date()
        if _last_check_date != today:
            _finished_games_today = set()
            _last_check_date = today
    
    @staticmethod
    def check_game_status(game_id: str) -> Optional[str]:
        """
        Check if a game is finished.
        
        Args:
            game_id: NBA game ID
            
        Returns:
            Game status: "FINAL", "LIVE", "SCHEDULED", or None if not found
        """
        try:
            games = NBADataService.fetch_todays_games()
            for game in games:
                if str(game.get("gameId")) == str(game_id):
                    return game.get("status", "SCHEDULED")
        except Exception:
            pass
        return None
    
    @staticmethod
    def get_players_in_game(game_id: str) -> List[int]:
        """
        Get player IDs for players in a specific game.
        This is a simplified implementation - in a full system, you'd fetch lineup data.
        
        Args:
            game_id: NBA game ID
            
        Returns:
            List of player IDs (empty list if unable to determine)
        """
        # Note: This is a placeholder. In a full implementation, you would:
        # 1. Fetch game boxscore/lineup data from NBA API
        # 2. Extract player IDs from both teams
        # For now, return empty list - this can be enhanced later
        return []
    
    @staticmethod
    def invalidate_player_logs_cache(player_ids: List[int]) -> int:
        """
        Invalidate cache for specific player game logs.
        
        Args:
            player_ids: List of player IDs to invalidate
            
        Returns:
            Number of cache entries invalidated
        """
        from ..services.cache_service import get_cache_service
        from datetime import datetime
        
        cache = get_cache_service()
        invalidated = 0
        today_str = datetime.now().date().isoformat()
        
        # Create cache keys for each player to invalidate and remove them
        # Cache keys now use string format: nba_api:player_game_log:{player_id}:{season}:{date}
        for player_id in player_ids:
            # Try different season formats that might be cached
            seasons_to_check = ["2025-26", "2024-25"]  # Current and previous seasons
            for season in seasons_to_check:
                # Generate the cache key that matches what fetch_player_game_log uses
                cache_key = f"nba_api:player_game_log:{player_id}:{season}:{today_str}"
                try:
                    if cache.delete(cache_key):
                        invalidated += 1
                except Exception:
                    continue
        
        return invalidated
    
    @staticmethod
    def check_and_invalidate_finished_games() -> Dict[str, Any]:
        """
        Check today's games for finished games and invalidate player log caches.
        This should be called periodically (e.g., every few minutes during game hours).
        
        Returns:
            Dict with status information about the check
        """
        GameStatusMonitor._reset_daily_tracking()
        
        try:
            games = NBADataService.fetch_todays_games()
            newly_finished = []
            players_to_invalidate = []
            
            for game in games:
                game_id = str(game.get("gameId", ""))
                status = game.get("status", "SCHEDULED")
                
                # Check if game just finished (wasn't in our finished set)
                if status == "FINAL" and game_id and game_id not in _finished_games_today:
                    newly_finished.append(game_id)
                    _finished_games_today.add(game_id)
                    
                    # Get players in this game and add to invalidation list
                    player_ids = GameStatusMonitor.get_players_in_game(game_id)
                    players_to_invalidate.extend(player_ids)
            
            # Invalidate caches for players in newly finished games
            invalidated_count = 0
            if players_to_invalidate:
                # Remove duplicates
                unique_player_ids = list(set(players_to_invalidate))
                invalidated_count = GameStatusMonitor.invalidate_player_logs_cache(unique_player_ids)
            
            return {
                "checked_at": datetime.now().isoformat(),
                "total_games": len(games),
                "newly_finished": len(newly_finished),
                "players_invalidated": len(set(players_to_invalidate)),
                "cache_entries_invalidated": invalidated_count,
                "finished_game_ids": newly_finished
            }
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error("Error checking finished games", error=str(e))
            return {
                "checked_at": datetime.now().isoformat(),
                "error": str(e),
                "total_games": 0,
                "newly_finished": 0,
                "players_invalidated": 0,
                "cache_entries_invalidated": 0
            }
    
    @staticmethod
    def invalidate_cache_for_player(player_id: int) -> bool:
        """
        Manually invalidate cache for a specific player.
        
        Args:
            player_id: Player ID to invalidate
            
        Returns:
            True if cache was invalidated, False otherwise
        """
        count = GameStatusMonitor.invalidate_player_logs_cache([player_id])
        return count > 0

