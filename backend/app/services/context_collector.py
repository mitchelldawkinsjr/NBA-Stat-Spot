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
from ..services.espn_api_service import get_espn_service
from ..services.espn_mapping_service import get_espn_mapping_service
from ..services.team_player_service import TeamPlayerService
from ..services.team_standings_service import get_team_standings_service
from ..services.news_context_service import get_news_context_service
from ..services.cache_service import get_cache_service
import structlog

logger = structlog.get_logger()


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
        Get historical performance against a specific opponent using ESPN schedules.
        
        Args:
            player_id: Player ID
            opponent_team_id: Opponent team ID
            season: Season string
            limit: Maximum number of games to analyze
            
        Returns:
            Dictionary with matchup statistics
        """
        try:
            # Get player's team
            player_team_id = TeamPlayerService.get_team_id_for_player(player_id)
            if not player_team_id:
                return {"h2h_avg_pts": None, "h2h_avg_reb": None, "h2h_avg_ast": None, "h2h_games_played": 0}
            
            # Get ESPN team slugs
            mapping_service = get_espn_mapping_service()
            player_espn_slug = mapping_service.get_espn_team_slug(player_team_id)
            opponent_espn_slug = mapping_service.get_espn_team_slug(opponent_team_id)
            
            if not player_espn_slug or not opponent_espn_slug:
                # Fallback to NBA API game logs
                logs = NBADataService.fetch_player_game_log(player_id, season)
                if not logs:
                    return {"h2h_avg_pts": None, "h2h_avg_reb": None, "h2h_avg_ast": None, "h2h_games_played": 0}
                matchup_games = logs[:limit]
                pts_values = [float(g.get("pts", 0) or 0) for g in matchup_games]
                reb_values = [float(g.get("reb", 0) or 0) for g in matchup_games]
                ast_values = [float(g.get("ast", 0) or 0) for g in matchup_games]
                return {
                    "h2h_avg_pts": sum(pts_values) / len(pts_values) if pts_values else None,
                    "h2h_avg_reb": sum(reb_values) / len(reb_values) if reb_values else None,
                    "h2h_avg_ast": sum(ast_values) / len(ast_values) if ast_values else None,
                    "h2h_games_played": len(matchup_games)
                }
            
            # Get opponent's schedule from ESPN
            espn_service = get_espn_service()
            opponent_schedule = espn_service.get_team_schedule(opponent_espn_slug)
            
            # Find games where opponent played player's team
            h2h_game_ids = []
            for event in opponent_schedule:
                competitions = event.get("competitions", [])
                if not competitions:
                    continue
                
                comp = competitions[0]
                competitors = comp.get("competitors", [])
                
                # Check if player's team is in this game
                for competitor in competitors:
                    team_data = competitor.get("team", {})
                    if team_data.get("slug") == player_espn_slug:
                        # This is a H2H game
                        event_id = event.get("id")
                        if event_id:
                            h2h_game_ids.append(event_id)
                        break
            
            # Get player's game logs and match by date/game
            logs = NBADataService.fetch_player_game_log(player_id, season)
            if not logs:
                return {"h2h_avg_pts": None, "h2h_avg_reb": None, "h2h_avg_ast": None, "h2h_games_played": 0}
            
            # Match H2H games with player logs (simplified - would need better matching)
            # For now, use recent games and filter by opponent if possible
            matchup_games = []
            for log in logs:
                # Try to match by opponent abbreviation in matchup string
                matchup = log.get("matchup", "").lower()
                opponent_abbr = None
                teams = NBADataService.fetch_all_teams()
                opponent_team = next((t for t in teams if t.get("id") == opponent_team_id), None)
                if opponent_team:
                    opponent_abbr = opponent_team.get("abbreviation", "").lower()
                
                if opponent_abbr and opponent_abbr in matchup:
                    matchup_games.append(log)
                    if len(matchup_games) >= limit:
                        break
            
            # If no H2H games found, use recent games as fallback
            if not matchup_games:
                matchup_games = logs[:limit]
            
            pts_values = [float(g.get("pts", 0) or 0) for g in matchup_games]
            reb_values = [float(g.get("reb", 0) or 0) for g in matchup_games]
            ast_values = [float(g.get("ast", 0) or 0) for g in matchup_games]
            
            # Check if opponent is on back-to-back
            opponent_back_to_back = False
            if opponent_schedule:
                # Get last two games
                recent_games = [g for g in opponent_schedule if g.get("date")]
                if len(recent_games) >= 2:
                    recent_games.sort(key=lambda x: x.get("date", ""), reverse=True)
                    last_game_date = recent_games[0].get("date", "")
                    prev_game_date = recent_games[1].get("date", "")
                    if last_game_date and prev_game_date:
                        try:
                            from datetime import datetime
                            last = datetime.fromisoformat(last_game_date.replace("Z", "+00:00"))
                            prev = datetime.fromisoformat(prev_game_date.replace("Z", "+00:00"))
                            days_diff = (last - prev).days
                            opponent_back_to_back = days_diff == 1
                        except Exception:
                            pass
            
            return {
                "h2h_avg_pts": sum(pts_values) / len(pts_values) if pts_values else None,
                "h2h_avg_reb": sum(reb_values) / len(reb_values) if reb_values else None,
                "h2h_avg_ast": sum(ast_values) / len(ast_values) if ast_values else None,
                "h2h_games_played": len(matchup_games),
                "opponent_back_to_back": opponent_back_to_back
            }
        except Exception as e:
            logger.warning("Error getting matchup history", player_id=player_id, opponent_team_id=opponent_team_id, error=str(e))
            return {"h2h_avg_pts": None, "h2h_avg_reb": None, "h2h_avg_ast": None, "h2h_games_played": 0, "opponent_back_to_back": False}
    
    @staticmethod
    def get_team_performance(team_id: int, games: int = 10) -> Dict[str, Any]:
        """
        Get recent team performance metrics from ESPN standings.
        
        Args:
            team_id: Team ID
            games: Number of recent games to analyze
            
        Returns:
            Dictionary with team performance metrics
        """
        try:
            standings_service = get_team_standings_service()
            standings_context = standings_service.get_team_standings_context(team_id)
            
            win_loss = standings_context.get("win_loss_record", {})
            recent_form = standings_context.get("recent_form", 0.5)
            
            return {
                "win_rate": win_loss.get("win_percentage", 0.0),
                "recent_form": recent_form,
                "conference_rank": standings_context.get("conference_rank"),
                "division_rank": standings_context.get("division_rank"),
                "playoff_race_pressure": standings_context.get("playoff_race_pressure", 0.0),
                "avg_pts": None,  # Would need to calculate from game logs
                "avg_pts_allowed": None,  # Would need to calculate from game logs
                "def_rank_pts": None,  # Would need defensive stats
                "def_rank_reb": None,
                "def_rank_ast": None
            }
        except Exception as e:
            logger.warning("Error fetching team performance", team_id=team_id, error=str(e))
        return {
            "win_rate": None,
                "recent_form": None,
                "conference_rank": None,
                "division_rank": None,
                "playoff_race_pressure": None,
            "avg_pts": None,
            "avg_pts_allowed": None,
            "def_rank_pts": None,
            "def_rank_reb": None,
            "def_rank_ast": None
        }
    
    @staticmethod
    def get_injury_status(player_id: int, game_date: date) -> Dict[str, Any]:
        """
        Get injury status for a player from ESPN API.
        
        Args:
            player_id: Player ID
            game_date: Date of the game
            
        Returns:
            Dictionary with injury information
        """
        try:
            cache = get_cache_service()
            cache_key = f"injury_status:{player_id}:{game_date.isoformat()}:15m"
            
            # Check cache first
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # Get player info
            all_players = NBADataService.fetch_all_players_including_rookies()
            player = next((p for p in all_players if p.get("id") == player_id), None)
            if not player:
                return {
                    "is_injured": False,
                    "injury_status": None,
                    "injury_description": None,
                    "injury_date": None
                }
            
            player_name = player.get("full_name")
            team_id = TeamPlayerService.get_team_id_for_player(player_id)
            
            # Get ESPN mapping service
            mapping_service = get_espn_mapping_service()
            espn_service = get_espn_service()
            
            # Get ESPN team slug
            espn_slug = mapping_service.get_espn_team_slug(team_id) if team_id else None
            
            # Fetch injuries from ESPN
            injuries_data = espn_service.get_injuries()
            if not injuries_data:
                # Return default if no injury data available
                result = {
                    "is_injured": False,
                    "injury_status": None,
                    "injury_description": None,
                    "injury_date": None
                }
                cache.set(cache_key, result, ttl=900)  # 15 minutes
                return result
            
            # Parse injury data - structure varies, try common patterns
            injury_status_map = {
                "probable": "probable",
                "questionable": "questionable",
                "doubtful": "doubtful",
                "out": "out",
                "day-to-day": "questionable",
                "dtd": "questionable"
            }
            
            # Search for player in injury reports
            # ESPN injuries structure: teams -> athletes -> injuries
            teams = injuries_data.get("teams", [])
            
            for team in teams:
                team_data = team.get("team", {})
                if espn_slug and team_data.get("slug") != espn_slug:
                    continue
                
                athletes = team.get("athletes", [])
                for athlete in athletes:
                    athlete_data = athlete.get("athlete", {})
                    espn_name = athlete_data.get("displayName", "") or athlete_data.get("fullName", "")
                    
                    # Match by name (fuzzy match if needed)
                    if player_name and espn_name:
                        # Simple name matching
                        if player_name.lower() in espn_name.lower() or espn_name.lower() in player_name.lower():
                            # Found player, check injuries
                            injuries = athlete.get("injuries", [])
                            if injuries:
                                # Get most recent injury
                                latest_injury = injuries[0]  # Usually sorted by date
                                
                                status_text = latest_injury.get("status", "").lower()
                                injury_status = None
                                for key, value in injury_status_map.items():
                                    if key in status_text:
                                        injury_status = value
                                        break
                                
                                # If no match, try to infer from status text
                                if not injury_status:
                                    if "out" in status_text or "inactive" in status_text:
                                        injury_status = "out"
                                    elif "probable" in status_text:
                                        injury_status = "probable"
                                    elif "questionable" in status_text or "doubtful" in status_text:
                                        injury_status = "questionable"
                                
                                description = latest_injury.get("description", "") or latest_injury.get("comment", "")
                                
                                # Try to parse injury date
                                injury_date = None
                                date_str = latest_injury.get("date", "") or latest_injury.get("startDate", "")
                                if date_str:
                                    try:
                                        # Try various date formats
                                        from datetime import datetime
                                        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"]:
                                            try:
                                                injury_date = datetime.strptime(date_str[:10], fmt).date()
                                                break
                                            except ValueError:
                                                continue
                                    except Exception:
                                        pass
                                
                                result = {
                                    "is_injured": injury_status is not None and injury_status != "probable",
                                    "injury_status": injury_status,
                                    "injury_description": description,
                                    "injury_date": injury_date
                                }
                                cache.set(cache_key, result, ttl=900)  # 15 minutes
                                return result
            
            # No injury found
            result = {
                "is_injured": False,
                "injury_status": None,
                "injury_description": None,
                "injury_date": None
            }
            cache.set(cache_key, result, ttl=900)  # 15 minutes
            return result
            
        except Exception as e:
            logger.warning("Error fetching injury status from ESPN", player_id=player_id, error=str(e))
            # Return default on error
        return {
            "is_injured": False,
            "injury_status": None,
                "injury_description": None,
                "injury_date": None
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
        
        # Get ESPN identifiers
        mapping_service = get_espn_mapping_service()
        team_id = TeamPlayerService.get_team_id_for_player(player_id)
        espn_team_slug = mapping_service.get_espn_team_slug(team_id) if team_id else None
        espn_player_id = mapping_service.get_espn_player_id(player_id)
        
        # Get matchup history
        matchup_info = {}
        if opponent_team_id:
            matchup_info = ContextCollector.get_matchup_history(player_id, opponent_team_id, season)
        
        # Get team performance for player's team
        player_team_id = TeamPlayerService.get_team_id_for_player(player_id)
        team_perf = ContextCollector.get_team_performance(player_team_id) if player_team_id else {}
        
        # Get opponent team performance
        opponent_perf = ContextCollector.get_team_performance(opponent_team_id) if opponent_team_id else {}
        
        # Get news context
        news_service = get_news_context_service()
        player_news = news_service.get_player_news_context(player_id, days=7)
        team_news = news_service.get_team_news_context(player_team_id, days=7) if player_team_id else {}
        
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
            espn_team_slug=espn_team_slug,
            espn_player_id=espn_player_id,
            is_injured=injury_info.get("is_injured", False),
            injury_status=injury_info.get("injury_status"),
            injury_description=injury_info.get("injury_description"),
            injury_date=injury_info.get("injury_date"),
            rest_days=rest_days,
            opponent_team_id=opponent_team_id,
            opponent_team_abbr=opponent_abbr,
            is_home_game=is_home_game,
            team_win_rate=team_perf.get("win_rate"),
            opponent_win_rate=opponent_perf.get("win_rate"),
            team_conference_rank=team_perf.get("conference_rank"),
            opponent_conference_rank=opponent_perf.get("conference_rank"),
            team_recent_form=team_perf.get("recent_form"),
            playoff_race_pressure=team_perf.get("playoff_race_pressure"),
            opponent_def_rank_pts=opponent_perf.get("def_rank_pts"),
            opponent_def_rank_reb=opponent_perf.get("def_rank_reb"),
            opponent_def_rank_ast=opponent_perf.get("def_rank_ast"),
            h2h_avg_pts=matchup_info.get("h2h_avg_pts"),
            h2h_avg_reb=matchup_info.get("h2h_avg_reb"),
            h2h_avg_ast=matchup_info.get("h2h_avg_ast"),
            h2h_games_played=matchup_info.get("h2h_games_played", 0),
            news_sentiment=player_news.get("news_sentiment", 0.0) or team_news.get("news_sentiment", 0.0),
            has_recent_transaction=team_news.get("has_recent_transaction", False)
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

