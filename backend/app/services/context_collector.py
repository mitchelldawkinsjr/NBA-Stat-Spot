"""
Context Collector Service - Gathers contextual information about players for AI predictions
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.player_context import PlayerContext
from ..services.nba_api_service import NBADataService


class ContextCollector:
    """Collects player context data including injuries, rest days, matchups, and team performance"""
    
    @staticmethod
    def calculate_rest_days(player_id: int, game_date: date, season: Optional[str] = None) -> Optional[int]:
        """
        Calculate days of rest for a player before a game.
        
        Args:
            player_id: Player ID
            game_date: Date of the game
            season: Season string (e.g., "2025-26")
            
        Returns:
            Number of rest days, or None if unable to calculate
        """
        try:
            logs = NBADataService.fetch_player_game_log(player_id, season)
            if not logs:
                return None
            
            # Find the most recent game before game_date
            game_date_str = game_date.isoformat()
            previous_games = [
                log for log in logs 
                if log.get("game_date") and log.get("game_date") < game_date_str
            ]
            
            if not previous_games:
                return None
            
            # Get the most recent game date
            most_recent = max(previous_games, key=lambda x: x.get("game_date", ""))
            last_game_date = datetime.strptime(most_recent.get("game_date"), "%Y-%m-%d").date()
            
            rest_days = (game_date - last_game_date).days - 1  # Subtract 1 to exclude game day
            return max(0, rest_days)  # Ensure non-negative
        except Exception:
            return None
    
    @staticmethod
    def get_matchup_history(
        player_id: int, 
        opponent_team_id: int, 
        season: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get historical performance against a specific opponent.
        
        Args:
            player_id: Player ID
            opponent_team_id: Opponent team ID
            season: Season string
            limit: Maximum number of games to analyze
            
        Returns:
            Dictionary with matchup statistics
        """
        try:
            logs = NBADataService.fetch_player_game_log(player_id, season)
            if not logs:
                return {"h2h_avg_pts": None, "h2h_avg_reb": None, "h2h_avg_ast": None, "h2h_games_played": 0}
            
            # Filter games against this opponent
            # Note: This is simplified - in production, you'd need to match opponent from matchup string
            # For now, we'll use all games as a proxy
            matchup_games = logs[:limit]
            
            if not matchup_games:
                return {"h2h_avg_pts": None, "h2h_avg_reb": None, "h2h_avg_ast": None, "h2h_games_played": 0}
            
            pts_values = [float(g.get("pts", 0) or 0) for g in matchup_games]
            reb_values = [float(g.get("reb", 0) or 0) for g in matchup_games]
            ast_values = [float(g.get("ast", 0) or 0) for g in matchup_games]
            
            return {
                "h2h_avg_pts": sum(pts_values) / len(pts_values) if pts_values else None,
                "h2h_avg_reb": sum(reb_values) / len(reb_values) if reb_values else None,
                "h2h_avg_ast": sum(ast_values) / len(ast_values) if ast_values else None,
                "h2h_games_played": len(matchup_games)
            }
        except Exception:
            return {"h2h_avg_pts": None, "h2h_avg_reb": None, "h2h_avg_ast": None, "h2h_games_played": 0}
    
    @staticmethod
    def get_team_performance(team_id: int, games: int = 10) -> Dict[str, Any]:
        """
        Get recent team performance metrics.
        
        Args:
            team_id: Team ID
            games: Number of recent games to analyze
            
        Returns:
            Dictionary with team performance metrics
        """
        # This is a placeholder - in production, you'd fetch team game logs
        # For now, return default values
        return {
            "win_rate": None,
            "avg_pts": None,
            "avg_pts_allowed": None,
            "def_rank_pts": None,
            "def_rank_reb": None,
            "def_rank_ast": None
        }
    
    @staticmethod
    def get_injury_status(player_id: int, game_date: date) -> Dict[str, Any]:
        """
        Get injury status for a player.
        
        Args:
            player_id: Player ID
            game_date: Date of the game
            
        Returns:
            Dictionary with injury information
        """
        # Placeholder - in production, you'd scrape or use an API for injury data
        # For now, return default values
        return {
            "is_injured": False,
            "injury_status": None,
            "injury_description": None
        }
    
    @staticmethod
    def collect_player_context(
        player_id: int,
        game_date: date,
        opponent_team_id: Optional[int] = None,
        is_home_game: bool = True,
        season: Optional[str] = None,
        db: Optional[Session] = None
    ) -> PlayerContext:
        """
        Collect all contextual information for a player for a specific game.
        
        Args:
            player_id: Player ID
            game_date: Date of the game
            opponent_team_id: Opponent team ID
            is_home_game: Whether it's a home game
            season: Season string
            db: Database session
            
        Returns:
            PlayerContext object
        """
        # Calculate rest days
        rest_days = ContextCollector.calculate_rest_days(player_id, game_date, season)
        
        # Get injury status
        injury_info = ContextCollector.get_injury_status(player_id, game_date)
        
        # Get matchup history
        matchup_info = {}
        if opponent_team_id:
            matchup_info = ContextCollector.get_matchup_history(player_id, opponent_team_id, season)
        
        # Get team performance
        team_perf = ContextCollector.get_team_performance(opponent_team_id) if opponent_team_id else {}
        
        # Get opponent team abbreviation
        opponent_abbr = None
        if opponent_team_id:
            teams = NBADataService.fetch_all_teams()
            opponent_team = next((t for t in teams if t.get("id") == opponent_team_id), None)
            if opponent_team:
                opponent_abbr = opponent_team.get("abbreviation")
        
        # Create or update PlayerContext
        context = PlayerContext(
            player_id=player_id,
            game_date=game_date,
            is_injured=injury_info.get("is_injured", False),
            injury_status=injury_info.get("injury_status"),
            injury_description=injury_info.get("injury_description"),
            rest_days=rest_days,
            opponent_team_id=opponent_team_id,
            opponent_team_abbr=opponent_abbr,
            is_home_game=is_home_game,
            team_win_rate=team_perf.get("win_rate"),
            opponent_win_rate=team_perf.get("win_rate"),  # Would be opponent's win rate
            opponent_def_rank_pts=team_perf.get("def_rank_pts"),
            opponent_def_rank_reb=team_perf.get("def_rank_reb"),
            opponent_def_rank_ast=team_perf.get("def_rank_ast"),
            h2h_avg_pts=matchup_info.get("h2h_avg_pts"),
            h2h_avg_reb=matchup_info.get("h2h_avg_reb"),
            h2h_avg_ast=matchup_info.get("h2h_avg_ast"),
            h2h_games_played=matchup_info.get("h2h_games_played", 0)
        )
        
        if db:
            # Check if context already exists
            existing = db.query(PlayerContext).filter(
                PlayerContext.player_id == player_id,
                PlayerContext.game_date == game_date
            ).first()
            
            if existing:
                # Update existing context
                for key, value in context.__dict__.items():
                    if not key.startswith('_') and key != 'id' and key != 'created_at':
                        setattr(existing, key, value)
                db.commit()
                db.refresh(existing)
                return existing
            else:
                # Create new context
                db.add(context)
                db.commit()
                db.refresh(context)
                return context
        
        return context

