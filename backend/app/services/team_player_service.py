"""
Team-Player Connection Service - Handles the relationship between teams and players
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Set
from .nba_api_service import NBADataService


class TeamPlayerService:
    """Service for managing team-player relationships"""
    
    @staticmethod
    def normalize_team_id(team_id: Any) -> Optional[int]:
        """
        Normalize team_id to integer, handling None, string, and int types.
        
        Args:
            team_id: Team ID in any format (None, string, int)
            
        Returns:
            Normalized team ID as int, or None if invalid
        """
        if team_id is None:
            return None
        
        try:
            # Try to convert to int
            if isinstance(team_id, str):
                # Remove any whitespace
                team_id = team_id.strip()
                if not team_id or team_id.lower() in ('none', 'null', ''):
                    return None
            return int(team_id)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def get_players_for_team(team_id: int) -> List[Dict[str, Any]]:
        """
        Get all players for a specific team.
        
        Args:
            team_id: Team ID to filter by
            
        Returns:
            List of player dictionaries with id, name, position, jersey_number
        """
        all_players = NBADataService.fetch_all_players_including_rookies()
        if not all_players:
            return []
        
        # Normalize the requested team_id
        target_team_id = TeamPlayerService.normalize_team_id(team_id)
        if target_team_id is None:
            return []
        
        players = []
        for p in all_players:
            player_team_id = TeamPlayerService.normalize_team_id(p.get("team_id"))
            
            # Only include players with matching team_id
            if player_team_id is not None and player_team_id == target_team_id:
                players.append({
                    "id": p.get("id"),
                    "name": p.get("full_name"),
                    "position": p.get("position"),
                    "jersey_number": p.get("jersey_number"),
                })
        
        return players
    
    @staticmethod
    def get_team_id_for_player(player_id: int) -> Optional[int]:
        """
        Get the team_id for a specific player.
        
        Args:
            player_id: Player ID to look up
            
        Returns:
            Team ID as int, or None if player not found or has no team
        """
        all_players = NBADataService.fetch_all_players_including_rookies()
        
        for p in all_players:
            if p.get("id") == player_id:
                return TeamPlayerService.normalize_team_id(p.get("team_id"))
        
        return None
    
    @staticmethod
    def get_players_for_teams(team_ids: Set[int]) -> Dict[int, List[Dict[str, Any]]]:
        """
        Get players for multiple teams at once.
        
        Args:
            team_ids: Set of team IDs to filter by
            
        Returns:
            Dictionary mapping team_id to list of players
        """
        all_players = NBADataService.fetch_all_players_including_rookies()
        if not all_players:
            return {tid: [] for tid in team_ids}
        
        # Normalize all team_ids
        normalized_team_ids = {TeamPlayerService.normalize_team_id(tid) for tid in team_ids}
        normalized_team_ids.discard(None)  # Remove None values
        
        # Group players by team_id
        players_by_team: Dict[int, List[Dict[str, Any]]] = {tid: [] for tid in normalized_team_ids}
        
        for p in all_players:
            player_team_id = TeamPlayerService.normalize_team_id(p.get("team_id"))
            
            if player_team_id is not None and player_team_id in normalized_team_ids:
                players_by_team[player_team_id].append({
                    "id": p.get("id"),
                    "name": p.get("full_name"),
                    "position": p.get("position"),
                    "jersey_number": p.get("jersey_number"),
                })
        
        return players_by_team
    
    @staticmethod
    def get_all_team_ids_with_players() -> Set[int]:
        """
        Get all team IDs that have at least one player.
        
        Returns:
            Set of team IDs that have players
        """
        all_players = NBADataService.fetch_all_players_including_rookies()
        if not all_players:
            return set()
        
        team_ids = set()
        for p in all_players:
            team_id = TeamPlayerService.normalize_team_id(p.get("team_id"))
            if team_id is not None:
                team_ids.add(team_id)
        
        return team_ids
    
    @staticmethod
    def validate_team_player_connection(team_id: int, player_id: int) -> bool:
        """
        Validate that a player belongs to a specific team.
        
        Args:
            team_id: Team ID to check
            player_id: Player ID to check
            
        Returns:
            True if player belongs to team, False otherwise
        """
        player_team_id = TeamPlayerService.get_team_id_for_player(player_id)
        target_team_id = TeamPlayerService.normalize_team_id(team_id)
        
        return player_team_id is not None and target_team_id is not None and player_team_id == target_team_id

