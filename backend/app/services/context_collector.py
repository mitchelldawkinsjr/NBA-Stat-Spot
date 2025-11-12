"""
Context Collector Service - Gathers contextual information about players for AI predictions
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
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
import threading

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
            # Check cache first
            cache = get_cache_service()
            season_to_use = season or "2025-26"
            cache_key = f"h2h:{player_id}:{opponent_team_id}:{season_to_use}:{limit}:6h"
            
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug("Returning cached H2H data", player_id=player_id, opponent_team_id=opponent_team_id, season=season_to_use)
                return cached_result
            
            # Get player's team
            player_team_id = TeamPlayerService.get_team_id_for_player(player_id)
            if not player_team_id:
                result = {"h2h_avg_pts": None, "h2h_avg_reb": None, "h2h_avg_ast": None, "h2h_games_played": 0}
                # Cache even empty results for a shorter time (1 hour)
                cache.set(f"h2h:{player_id}:{opponent_team_id}:{season_to_use}:{limit}:1h", result, ttl=3600)
                return result
            
            # Get ESPN team slugs
            mapping_service = get_espn_mapping_service()
            player_espn_slug = mapping_service.get_espn_team_slug(player_team_id)
            opponent_espn_slug = mapping_service.get_espn_team_slug(opponent_team_id)
            
            if not player_espn_slug or not opponent_espn_slug:
                # Fallback to NBA API game logs
                logs = NBADataService.fetch_player_game_log(player_id, season_to_use)
                if not logs:
                    result = {"h2h_avg_pts": None, "h2h_avg_reb": None, "h2h_avg_ast": None, "h2h_games_played": 0}
                    cache.set(cache_key, result, ttl=21600)  # 6 hours
                    return result
                matchup_games = logs[:limit]
                pts_values = [float(g.get("pts", 0) or 0) for g in matchup_games]
                reb_values = [float(g.get("reb", 0) or 0) for g in matchup_games]
                ast_values = [float(g.get("ast", 0) or 0) for g in matchup_games]
                result = {
                    "h2h_avg_pts": sum(pts_values) / len(pts_values) if pts_values else None,
                    "h2h_avg_reb": sum(reb_values) / len(reb_values) if reb_values else None,
                    "h2h_avg_ast": sum(ast_values) / len(ast_values) if ast_values else None,
                    "h2h_games_played": len(matchup_games)
                }
                cache.set(cache_key, result, ttl=21600)  # 6 hours
                return result
            
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
            logs = NBADataService.fetch_player_game_log(player_id, season_to_use)
            if not logs:
                result = {"h2h_avg_pts": None, "h2h_avg_reb": None, "h2h_avg_ast": None, "h2h_games_played": 0}
                cache.set(cache_key, result, ttl=21600)  # 6 hours
                return result
            
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
            
            result = {
                "h2h_avg_pts": sum(pts_values) / len(pts_values) if pts_values else None,
                "h2h_avg_reb": sum(reb_values) / len(reb_values) if reb_values else None,
                "h2h_avg_ast": sum(ast_values) / len(ast_values) if ast_values else None,
                "h2h_games_played": len(matchup_games),
                "opponent_back_to_back": opponent_back_to_back
            }
            # Cache for 6 hours
            cache.set(cache_key, result, ttl=21600)
            return result
        except Exception as e:
            logger.warning("Error getting matchup history", player_id=player_id, opponent_team_id=opponent_team_id, error=str(e))
            result = {"h2h_avg_pts": None, "h2h_avg_reb": None, "h2h_avg_ast": None, "h2h_games_played": 0, "opponent_back_to_back": False}
            # Cache error result for shorter time (1 hour)
            cache = get_cache_service()
            season_to_use = season or "2025-26"
            cache_key = f"h2h:{player_id}:{opponent_team_id}:{season_to_use}:{limit}:1h"
            cache.set(cache_key, result, ttl=3600)
            return result
    
    @staticmethod
    def _calculate_defensive_ranks(season: Optional[str] = None) -> Dict[int, Dict[str, int]]:
        """
        Calculate defensive rankings for all teams based on what opponents score against them.
        Uses parallel processing to avoid blocking the endpoint.
        
        Args:
            season: Season string (e.g., "2025-26")
            
        Returns:
            Dictionary mapping team_id to defensive ranks: {team_id: {"pts": rank, "reb": rank, "ast": rank}}
        """
        try:
            cache = get_cache_service()
            season_to_use = season or "2025-26"
            cache_key = f"defensive_ranks:{season_to_use}:24h"
            
            # Check cache first
            cached_ranks = cache.get(cache_key)
            if cached_ranks is not None:
                return cached_ranks
            
            # Get all teams
            teams = NBADataService.fetch_all_teams()
            if not teams:
                return {}
            
            # Create team lookup by abbreviation
            teams_by_abbr = {t.get("abbreviation", "").upper(): t for t in teams if t.get("abbreviation")}
            
            # Dictionary to store what each team allows (opponent stats)
            # Structure: {team_id: {"pts": [list of opponent pts], "reb": [...], "ast": [...]}}
            team_defensive_stats: Dict[int, Dict[str, List[float]]] = {}
            stats_lock = threading.Lock()
            
            # Initialize for all teams
            for team in teams:
                team_id = team.get("id")
                if team_id:
                    team_defensive_stats[team_id] = {"pts": [], "reb": [], "ast": []}
            
            # Sample size: 3 players per team, 15 games per player for better coverage
            players_per_team = 3
            games_per_player = 15
            all_players = NBADataService.fetch_all_players_including_rookies()
            
            # Group players by team - get more players for better coverage
            players_by_team: Dict[int, List[Dict[str, Any]]] = {}
            for player in all_players:
                team_id = player.get("team_id")
                if team_id:
                    if team_id not in players_by_team:
                        players_by_team[team_id] = []
                    if len(players_by_team[team_id]) < players_per_team:
                        players_by_team[team_id].append(player)
            
            logger.info("Grouped players by team", teams_with_players=len(players_by_team), players_per_team=players_per_team, total_teams=len(teams))
            
            # Log teams without players for debugging
            teams_without_players = [t.get("id") for t in teams if t.get("id") and t.get("id") not in players_by_team]
            if teams_without_players:
                logger.warning("Teams without players found", count=len(teams_without_players), team_ids=teams_without_players[:10])
            
            def process_team_player(args):
                """Process a single team-player combination to get defensive stats"""
                team_id, player_id, season_str = args
                try:
                    # Get player's game logs
                    logs = NBADataService.fetch_player_game_log(player_id, season_str)
                    if not logs:
                        return []
                    
                    game_stats = []
                    games_processed = 0
                    games_with_stats = 0
                    
                    # Process up to games_per_player games
                    for game_log in logs[:games_per_player]:
                        games_processed += 1
                        matchup = game_log.get("matchup", "")
                        if not matchup:
                            continue
                        
                        matchup_upper = matchup.upper().strip()
                        
                        # Parse opponent from matchup - handle various formats
                        # Formats: "LAL vs. BOS", "LAL @ BOS", "LAL VS BOS", "LAL v BOS", etc.
                        opponent_abbr = None
                        
                        # Try different patterns - be more flexible with whitespace
                        patterns = [
                            (" VS. ", " VS. "),
                            (" VS ", " VS "),
                            (" V ", " V "),
                            (" @ ", " @ "),
                            (" VS.", " VS."),
                            (" VS", " VS"),
                        ]
                        
                        for pattern, split_pattern in patterns:
                            if pattern in matchup_upper:
                                parts = matchup_upper.split(split_pattern)
                                if len(parts) == 2:
                                    opponent_abbr = parts[1].strip()
                                    break
                        
                        # If still no match, try regex-like approach
                        if not opponent_abbr:
                            import re
                            # Match pattern like "TEAM1 vs TEAM2" or "TEAM1 @ TEAM2"
                            match = re.search(r'([A-Z]{2,4})\s+(?:VS\.?|@|V\.?)\s+([A-Z]{2,4})', matchup_upper)
                            if match:
                                # Get the second team (opponent)
                                opponent_abbr = match.group(2)
                        
                        if not opponent_abbr:
                            continue
                        
                        # Clean up abbreviation (remove any trailing dots or spaces)
                        opponent_abbr = opponent_abbr.strip(' .')
                        
                        # Find opponent team - try exact match first
                        opponent_team = teams_by_abbr.get(opponent_abbr)
                        
                        # If not found, try partial match (for cases like "LAL" vs "L.A.")
                        if not opponent_team:
                            for abbr, team in teams_by_abbr.items():
                                if abbr.startswith(opponent_abbr[:2]) or opponent_abbr.startswith(abbr[:2]):
                                    opponent_team = team
                                    break
                        
                        if not opponent_team:
                            continue
                        
                        opponent_team_id = opponent_team.get("id")
                        if not opponent_team_id:
                            continue
                        
                        game_date = game_log.get("game_date")
                        if not game_date:
                            continue
                        
                        # Get stats from multiple opponent players for better accuracy
                        # Use up to 2 opponent players to get a better sample
                        opponent_players = players_by_team.get(opponent_team_id, [])
                        if not opponent_players:
                            continue
                        
                        # Sum stats from multiple opponent players
                        opp_pts_total = 0.0
                        opp_reb_total = 0.0
                        opp_ast_total = 0.0
                        players_found = 0
                        
                        # Try to get stats from up to 2 opponent players
                        for opponent_player in opponent_players[:2]:
                            opponent_player_id = opponent_player.get("id")
                            if not opponent_player_id:
                                continue
                            
                            try:
                                opponent_logs = NBADataService.fetch_player_game_log(opponent_player_id, season_str)
                                if not opponent_logs:
                                    continue
                                
                                matching_game = next(
                                    (g for g in opponent_logs if g.get("game_date") == game_date),
                                    None
                                )
                                
                                if matching_game:
                                    opp_pts_total += float(matching_game.get("pts", 0) or 0)
                                    opp_reb_total += float(matching_game.get("reb", 0) or 0)
                                    opp_ast_total += float(matching_game.get("ast", 0) or 0)
                                    players_found += 1
                            except Exception:
                                continue
                        
                        # Only add if we found at least one opponent player's stats
                        if players_found > 0:
                            games_with_stats += 1
                            game_stats.append({
                                "team_id": team_id,
                                "opp_pts": opp_pts_total,
                                "opp_reb": opp_reb_total,
                                "opp_ast": opp_ast_total
                            })
                    
                    # Log per-player stats for debugging (only for first few players to avoid spam)
                    if player_id % 100 == 0:  # Log every 100th player
                        logger.debug("Processed player", player_id=player_id, games_processed=games_processed, games_with_stats=games_with_stats, stats_collected=len(game_stats))
                    
                    return game_stats
                except Exception:
                    return []
            
            # Prepare arguments for parallel processing
            tasks = []
            for team_id, team_players in players_by_team.items():
                if not team_players:
                    continue
                for player in team_players[:players_per_team]:
                    player_id = player.get("id")
                    if player_id:
                        tasks.append((team_id, player_id, season_to_use))
            
            if not tasks:
                logger.warning("No tasks to process for defensive ranks calculation")
                return {}
            
            # Process in parallel with ThreadPoolExecutor
            # Use 10 workers to balance speed vs API rate limits
            logger.info("Starting defensive ranks calculation", total_tasks=len(tasks), season=season_to_use)
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                # Submit all tasks
                future_to_task = {
                    executor.submit(process_team_player, task): task 
                    for task in tasks
                }
                
                # Collect results as they complete
                completed = 0
                try:
                    for future in as_completed(future_to_task, timeout=120.0):  # 2 minute overall timeout
                        try:
                            game_stats = future.result(timeout=5.0)  # 5 second timeout per task
                            if game_stats:
                                with stats_lock:
                                    for stat in game_stats:
                                        team_id = stat["team_id"]
                                        if team_id in team_defensive_stats:
                                            team_defensive_stats[team_id]["pts"].append(stat["opp_pts"])
                                            team_defensive_stats[team_id]["reb"].append(stat["opp_reb"])
                                            team_defensive_stats[team_id]["ast"].append(stat["opp_ast"])
                            completed += 1
                        except FutureTimeoutError:
                            logger.warning("Task timed out in defensive ranks calculation")
                            continue
                        except Exception as e:
                            logger.warning("Error processing task in defensive ranks", error=str(e))
                            continue
                except FutureTimeoutError:
                    logger.warning("Overall timeout reached in defensive ranks calculation", completed=completed, total=len(tasks))
                    # Continue with whatever data we've collected so far
            
            logger.info("Completed defensive ranks calculation", completed=completed, total=len(tasks))
            
            # Log how much data we collected
            total_data_points = sum(len(stats["pts"]) for stats in team_defensive_stats.values())
            teams_with_data = sum(1 for stats in team_defensive_stats.values() if stats["pts"])
            logger.info("Defensive stats collected", total_data_points=total_data_points, teams_with_data=teams_with_data, total_teams=len(team_defensive_stats))
            
            # Calculate averages for each team
            team_averages: Dict[int, Dict[str, float]] = {}
            for team_id, stats in team_defensive_stats.items():
                # Require at least 1 data point for a valid ranking
                if stats["pts"] and len(stats["pts"]) >= 1:
                    pts_avg = sum(stats["pts"]) / len(stats["pts"])
                    reb_avg = sum(stats["reb"]) / len(stats["reb"]) if stats["reb"] else 0
                    ast_avg = sum(stats["ast"]) / len(stats["ast"]) if stats["ast"] else 0
                    
                    team_averages[team_id] = {
                        "pts": pts_avg,
                        "reb": reb_avg,
                        "ast": ast_avg
                    }
            
            logger.info("Team averages calculated", teams_ranked=len(team_averages), min_data_points=1)
            
            # Rank teams (lower average = better defense = lower rank number)
            pts_ranked = sorted(team_averages.items(), key=lambda x: x[1]["pts"])
            reb_ranked = sorted(team_averages.items(), key=lambda x: x[1]["reb"])
            ast_ranked = sorted(team_averages.items(), key=lambda x: x[1]["ast"])
            
            # Create rank dictionaries
            defensive_ranks: Dict[int, Dict[str, int]] = {}
            
            for rank, (team_id, _) in enumerate(pts_ranked, start=1):
                if team_id not in defensive_ranks:
                    defensive_ranks[team_id] = {}
                defensive_ranks[team_id]["pts"] = rank
            
            for rank, (team_id, _) in enumerate(reb_ranked, start=1):
                if team_id not in defensive_ranks:
                    defensive_ranks[team_id] = {}
                defensive_ranks[team_id]["reb"] = rank
            
            for rank, (team_id, _) in enumerate(ast_ranked, start=1):
                if team_id not in defensive_ranks:
                    defensive_ranks[team_id] = {}
                defensive_ranks[team_id]["ast"] = rank
            
            # Cache for 24 hours
            cache.set(cache_key, defensive_ranks, ttl=86400)
            
            logger.info("Defensive ranks calculation complete", teams_ranked=len(defensive_ranks))
            return defensive_ranks
        except Exception as e:
            logger.warning("Error calculating defensive ranks", season=season, error=str(e))
            return {}
    
    @staticmethod
    def get_team_performance(team_id: int, games: int = 10, season: Optional[str] = None) -> Dict[str, Any]:
        """
        Get recent team performance metrics from ESPN standings.
        
        Args:
            team_id: Team ID
            games: Number of recent games to analyze
            season: Season string (e.g., "2025-26")
            
        Returns:
            Dictionary with team performance metrics
        """
        try:
            # Check cache first for team performance data
            cache = get_cache_service()
            season_to_use = season or "2025-26"
            cache_key = f"team_performance:{team_id}:{season_to_use}:6h"
            
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug("Returning cached team performance", team_id=team_id, season=season_to_use)
                return cached_result
            
            logger.debug("Team performance cache miss, calculating", team_id=team_id, season=season_to_use)
            standings_service = get_team_standings_service()
            standings_context = standings_service.get_team_standings_context(team_id)
            
            win_loss = standings_context.get("win_loss_record", {})
            recent_form = standings_context.get("recent_form", 0.5)
            
            # Get defensive ranks (this is already cached at league level for 24 hours)
            # This should return instantly if cached, or take 1-2 minutes on first calculation
            defensive_ranks = ContextCollector._calculate_defensive_ranks(season_to_use)
            team_ranks = defensive_ranks.get(team_id, {})
            
            # Log if defensive ranks are missing for debugging (only log once per team to avoid spam)
            if not team_ranks and len(defensive_ranks) > 0:
                logger.debug("No defensive ranks found for team", team_id=team_id, season=season_to_use, total_ranks=len(defensive_ranks))
            elif not team_ranks and len(defensive_ranks) == 0:
                logger.warning("Defensive ranks calculation returned empty - may still be calculating", team_id=team_id, season=season_to_use)
            
            result = {
                "win_rate": win_loss.get("win_percentage", 0.0),
                "recent_form": recent_form,
                "conference_rank": standings_context.get("conference_rank"),
                "division_rank": standings_context.get("division_rank"),
                "playoff_race_pressure": standings_context.get("playoff_race_pressure", 0.0),
                "avg_pts": None,  # Would need to calculate from game logs
                "avg_pts_allowed": None,  # Would need to calculate from game logs
                "def_rank_pts": team_ranks.get("pts"),
                "def_rank_reb": team_ranks.get("reb"),
                "def_rank_ast": team_ranks.get("ast")
            }
            
            # Log the result for debugging
            logger.debug("Team performance retrieved", team_id=team_id, def_rank_pts=result["def_rank_pts"], def_rank_reb=result["def_rank_reb"], def_rank_ast=result["def_rank_ast"])
            
            # Cache for 6 hours (same as H2H)
            cache.set(cache_key, result, ttl=21600)
            return result
        except Exception as e:
            logger.warning("Error fetching team performance", team_id=team_id, error=str(e))
        result = {
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
        # Cache error result for shorter time (1 hour)
        if team_id:
            cache = get_cache_service()
            season_to_use = season or "2025-26"
            cache_key = f"team_performance:{team_id}:{season_to_use}:1h"
            cache.set(cache_key, result, ttl=3600)
        return result
    
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
            # Cache for 4 hours since injuries typically only change 1-2 times per day
            cache_key = f"injury_status:{player_id}:{game_date.isoformat()}:4h"
            
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
            
            # Get ESPN team slug and player ID for better matching
            espn_slug = mapping_service.get_espn_team_slug(team_id) if team_id else None
            espn_player_id = mapping_service.get_espn_player_id(player_id)
            
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
                cache.set(cache_key, result, ttl=14400)  # 4 hours - injuries change infrequently
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
            
            # Helper function for better name matching
            def normalize_name(name):
                """Normalize name for matching"""
                if not name:
                    return ""
                # Remove common suffixes and normalize
                name = name.lower().strip()
                # Remove common suffixes
                for suffix in [" jr.", " sr.", " iii", " ii", " iv"]:
                    if name.endswith(suffix):
                        name = name[:-len(suffix)].strip()
                return name
            
            def names_match(nba_name, espn_name):
                """Check if two names match with fuzzy logic"""
                if not nba_name or not espn_name:
                    return False
                
                nba_norm = normalize_name(nba_name)
                espn_norm = normalize_name(espn_name)
                
                # Exact match after normalization
                if nba_norm == espn_norm:
                    return True
                
                # Check if one contains the other (for cases like "Anthony Davis" vs "A. Davis")
                if nba_norm in espn_norm or espn_norm in nba_norm:
                    return True
                
                # Check first and last name separately
                nba_parts = nba_norm.split()
                espn_parts = espn_norm.split()
                if len(nba_parts) >= 2 and len(espn_parts) >= 2:
                    # Match if both first and last names match
                    if nba_parts[0] == espn_parts[0] and nba_parts[-1] == espn_parts[-1]:
                        return True
                    # Match if last names match and first initial matches
                    if nba_parts[-1] == espn_parts[-1] and (nba_parts[0][0] == espn_parts[0][0] or espn_parts[0][0] == nba_parts[0][0]):
                        return True
                
                return False
            
            # Search for player in injury reports
            # ESPN injuries structure: teams -> athletes -> injuries
            teams = injuries_data.get("teams", [])
            
            # First, try to find in player's team (more efficient)
            for team in teams:
                team_data = team.get("team", {})
                if espn_slug and team_data.get("slug") != espn_slug:
                    continue
                
                athletes = team.get("athletes", [])
                for athlete in athletes:
                    athlete_data = athlete.get("athlete", {})
                    athlete_espn_id = athlete_data.get("id")
                    espn_name = athlete_data.get("displayName", "") or athlete_data.get("fullName", "")
                    
                    # Try ESPN ID match first (most accurate)
                    if espn_player_id and athlete_espn_id and str(espn_player_id) == str(athlete_espn_id):
                        # Found by ID, check injuries
                        injuries = athlete.get("injuries", [])
                        if injuries:
                            return ContextCollector._parse_injury_data(injuries[0], injury_status_map, cache_key)
                    
                    # Fall back to name matching
                    if player_name and espn_name and names_match(player_name, espn_name):
                        # Found player, check injuries
                        injuries = athlete.get("injuries", [])
                        if injuries:
                            logger.info("Found injury by name match", player_id=player_id, player_name=player_name, espn_name=espn_name)
                            return ContextCollector._parse_injury_data(injuries[0], injury_status_map, cache_key)
            
            # If not found in player's team, search all teams (fallback)
            if espn_slug:  # Only do fallback if we have team info
                for team in teams:
                    team_data = team.get("team", {})
                    if team_data.get("slug") == espn_slug:
                        continue  # Already checked this team
                    
                    athletes = team.get("athletes", [])
                    for athlete in athletes:
                        athlete_data = athlete.get("athlete", {})
                        athlete_espn_id = athlete_data.get("id")
                        espn_name = athlete_data.get("displayName", "") or athlete_data.get("fullName", "")
                        
                        # Try ESPN ID match
                        if espn_player_id and athlete_espn_id and str(espn_player_id) == str(athlete_espn_id):
                            injuries = athlete.get("injuries", [])
                            if injuries:
                                logger.info("Found injury by ID in fallback search", player_id=player_id)
                                return ContextCollector._parse_injury_data(injuries[0], injury_status_map, cache_key)
                        
                        # Try name matching
                        if player_name and espn_name and names_match(player_name, espn_name):
                            injuries = athlete.get("injuries", [])
                            if injuries:
                                logger.info("Found injury by name in fallback search", player_id=player_id, player_name=player_name, espn_name=espn_name)
                                return ContextCollector._parse_injury_data(injuries[0], injury_status_map, cache_key)
            
            # Log if player not found for debugging
            logger.debug("Player not found in injury reports", player_id=player_id, player_name=player_name, espn_slug=espn_slug, espn_player_id=espn_player_id)
            
            # No injury found
            result = {
                "is_injured": False,
                "injury_status": None,
                "injury_description": None,
                "injury_date": None
            }
            # Cache "not injured" for 4 hours - injuries change infrequently (1-2 times per day)
            cache.set(cache_key, result, ttl=14400)  # 4 hours
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
    def _parse_injury_data(latest_injury: Dict[str, Any], injury_status_map: Dict[str, str], cache_key: str) -> Dict[str, Any]:
        """Helper function to parse injury data from ESPN response"""
        cache = get_cache_service()
        
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
        # Cache injury data for 4 hours - injuries typically only change 1-2 times per day
        cache.set(cache_key, result, ttl=14400)  # 4 hours
        return result
    
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
        team_perf = ContextCollector.get_team_performance(player_team_id, season=season) if player_team_id else {}
        
        # Get opponent team performance
        opponent_perf = ContextCollector.get_team_performance(opponent_team_id, season=season) if opponent_team_id else {}
        
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

