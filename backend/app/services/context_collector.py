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
from ..core.config import current_candidate_season
import structlog
import threading

logger = structlog.get_logger()


def _normalize_rank_keys(ranks: Dict[Any, Dict[str, int]]) -> Dict[int, Dict[str, int]]:
    """Ensure rank dict keys are int (JSON round-trip turns them into strings)."""
    if not ranks:
        return {}
    return {int(k): v for k, v in ranks.items()}

# Minutes threshold: treat as "did not play" if minutes is 0 or missing (DNP)
MIN_MINUTES_PLAYED_THRESHOLD = 0.5
# If most recent game or last 2 games have no minutes, infer possible injury
RECENT_GAMES_TO_CHECK = 2
# Below this ratio of "normal" minutes → treat as potentially hurt (e.g. half minutes = 0.5)
HALF_NORMAL_MINUTES_RATIO = 0.55
# Minimum games with real minutes needed to compute "normal" baseline (excludes DNPs)
MIN_GAMES_FOR_BASELINE_MINUTES = 5
# When computing baseline, only use games with at least this many minutes (exclude DNPs and garbage time)
MIN_MINUTES_TO_COUNT_FOR_BASELINE = 5.0


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
            
            # Check cache first (JSON round-trip may have string keys; normalize to int)
            cached_ranks = cache.get(cache_key)
            if cached_ranks is not None:
                return _normalize_rank_keys(cached_ranks)
            
            # Get all teams
            teams = NBADataService.fetch_all_teams()
            if not teams:
                return {}
            
            # Create team lookup by abbreviation
            teams_by_abbr = {t.get("abbreviation", "").upper(): t for t in teams if t.get("abbreviation")}
            
            # Dictionary to store what each team allows (opponent stats)
            # Structure: {team_id: {"pts": [...], "reb": [...], "ast": [...], "3pm": [...]}}
            team_defensive_stats: Dict[int, Dict[str, List[float]]] = {}
            stats_lock = threading.Lock()
            
            # Initialize for all teams
            for team in teams:
                team_id = team.get("id")
                if team_id:
                    team_defensive_stats[team_id] = {"pts": [], "reb": [], "ast": [], "3pm": []}
            
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
                        opp_3pm_total = 0.0
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
                                    opp_3pm_total += float(matching_game.get("tpm", 0) or 0)
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
                                "opp_ast": opp_ast_total,
                                "opp_3pm": opp_3pm_total,
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
            # Use 10 workers to balance speed vs API rate limits; allow enough time for all 30 teams (90 tasks)
            logger.info("Starting defensive ranks calculation", total_tasks=len(tasks), season=season_to_use)
            overall_timeout = 600.0  # 10 minutes so all teams can complete (was 120s, often stopped at ~10 teams)
            per_task_timeout = 15.0  # per-task timeout for slow API

            with ThreadPoolExecutor(max_workers=10) as executor:
                # Submit all tasks
                future_to_task = {
                    executor.submit(process_team_player, task): task
                    for task in tasks
                }
                completed = 0
                try:
                    for future in as_completed(future_to_task, timeout=overall_timeout):
                        try:
                            game_stats = future.result(timeout=per_task_timeout)
                            if game_stats:
                                with stats_lock:
                                    for stat in game_stats:
                                        team_id = stat["team_id"]
                                        if team_id in team_defensive_stats:
                                            team_defensive_stats[team_id]["pts"].append(stat["opp_pts"])
                                            team_defensive_stats[team_id]["reb"].append(stat["opp_reb"])
                                            team_defensive_stats[team_id]["ast"].append(stat["opp_ast"])
                                            team_defensive_stats[team_id]["3pm"].append(stat.get("opp_3pm", 0.0))
                            completed += 1
                        except FutureTimeoutError:
                            logger.warning("Task timed out in defensive ranks calculation")
                            continue
                        except Exception as e:
                            logger.warning("Error processing task in defensive ranks", error=str(e))
                            continue
                except FutureTimeoutError:
                    logger.warning(
                        "Overall timeout reached in defensive ranks calculation",
                        completed=completed, total=len(tasks), timeout_sec=overall_timeout,
                    )
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
                    threepm_avg = sum(stats["3pm"]) / len(stats["3pm"]) if stats["3pm"] else 0.0
                    
                    team_averages[team_id] = {
                        "pts": pts_avg,
                        "reb": reb_avg,
                        "ast": ast_avg,
                        "3pm": threepm_avg,
                    }
            
            logger.info("Team averages calculated", teams_ranked=len(team_averages), min_data_points=1)
            
            # Rank teams (lower average = better defense = lower rank number)
            pts_ranked = sorted(team_averages.items(), key=lambda x: x[1]["pts"])
            reb_ranked = sorted(team_averages.items(), key=lambda x: x[1]["reb"])
            ast_ranked = sorted(team_averages.items(), key=lambda x: x[1]["ast"])
            threepm_ranked = sorted(team_averages.items(), key=lambda x: x[1]["3pm"])
            
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
            
            for rank, (team_id, _) in enumerate(threepm_ranked, start=1):
                if team_id not in defensive_ranks:
                    defensive_ranks[team_id] = {}
                defensive_ranks[team_id]["3pm"] = rank
            
            # If we have fewer than 30 teams (e.g. due to earlier timeout or API gaps), fill missing from fallback
            all_team_ids = {t.get("id") for t in teams if t.get("id")}
            if all_team_ids and len(defensive_ranks) < len(all_team_ids):
                try:
                    def_fb, _ = ContextCollector._calculate_team_ranks_from_player_stats(season_to_use)
                    for tid in all_team_ids:
                        tid_int = int(tid)
                        if tid_int not in defensive_ranks and tid_int in def_fb:
                            defensive_ranks[tid_int] = def_fb[tid_int]
                    logger.info("Filled missing defensive ranks from fallback", added=len(defensive_ranks) - len(team_averages), total_now=len(defensive_ranks))
                except Exception as fb_err:
                    logger.warning("Could not fill missing defensive ranks from fallback", error=str(fb_err))

            # Cache for 24 hours
            cache.set(cache_key, defensive_ranks, ttl=86400)
            # Also cache raw averages for matchup advantage score computation
            cache.set(f"defensive_avgs:{season_to_use}:24h", team_averages, ttl=86400)

            logger.info("Defensive ranks calculation complete", teams_ranked=len(defensive_ranks))
            return defensive_ranks
        except Exception as e:
            logger.warning("Error calculating defensive ranks", season=season, error=str(e))
            return {}

    @staticmethod
    def _calculate_offensive_ranks(season: Optional[str] = None) -> Dict[int, Dict[str, int]]:
        """
        Calculate offensive rankings for all teams based on what they score (from player game logs).
        Higher scoring = better offense = rank 1. Cached 24h.
        Returns: {team_id: {"pts": rank, "reb": rank, "ast": rank, "3pm": rank}}
        """
        try:
            cache = get_cache_service()
            season_to_use = season or "2025-26"
            cache_key = f"offensive_ranks:{season_to_use}:24h"
            cached = cache.get(cache_key)
            if cached is not None:
                return _normalize_rank_keys(cached)

            teams = NBADataService.fetch_all_teams()
            if not teams:
                return {}

            # Per-team per-game totals: team_id -> game_date -> {pts, reb, ast, 3pm}
            team_game_totals: Dict[int, Dict[str, Dict[str, float]]] = {}
            for t in teams:
                tid = t.get("id")
                if tid:
                    team_game_totals[tid] = {}

            players_per_team = 5
            games_per_player = 20
            all_players = NBADataService.fetch_all_players_including_rookies()
            players_by_team: Dict[int, List[Dict[str, Any]]] = {}
            for p in all_players:
                team_id = p.get("team_id")
                if team_id:
                    if team_id not in players_by_team:
                        players_by_team[team_id] = []
                    if len(players_by_team[team_id]) < players_per_team:
                        players_by_team[team_id].append(p)

            for team_id, team_players in players_by_team.items():
                if team_id not in team_game_totals:
                    continue
                for player in team_players:
                    player_id = player.get("id")
                    if not player_id:
                        continue
                    try:
                        logs = NBADataService.fetch_player_game_log(player_id, season_to_use)
                    except Exception:
                        continue
                    for g in logs[:games_per_player]:
                        gd = g.get("game_date")
                        if not gd:
                            continue
                        if gd not in team_game_totals[team_id]:
                            team_game_totals[team_id][gd] = {"pts": 0.0, "reb": 0.0, "ast": 0.0, "3pm": 0.0}
                        team_game_totals[team_id][gd]["pts"] += float(g.get("pts", 0) or 0)
                        team_game_totals[team_id][gd]["reb"] += float(g.get("reb", 0) or 0)
                        team_game_totals[team_id][gd]["ast"] += float(g.get("ast", 0) or 0)
                        team_game_totals[team_id][gd]["3pm"] += float(g.get("tpm", 0) or 0)

            # Averages per team (one value per game, then average)
            team_averages: Dict[int, Dict[str, float]] = {}
            for team_id, games in team_game_totals.items():
                if not games:
                    continue
                n = len(games)
                team_averages[team_id] = {
                    "pts": sum(x["pts"] for x in games.values()) / n,
                    "reb": sum(x["reb"] for x in games.values()) / n,
                    "ast": sum(x["ast"] for x in games.values()) / n,
                    "3pm": sum(x["3pm"] for x in games.values()) / n,
                }

            # Rank: higher average = better = rank 1 (reverse sort)
            pts_ranked = sorted(team_averages.items(), key=lambda x: -x[1]["pts"])
            reb_ranked = sorted(team_averages.items(), key=lambda x: -x[1]["reb"])
            ast_ranked = sorted(team_averages.items(), key=lambda x: -x[1]["ast"])
            threepm_ranked = sorted(team_averages.items(), key=lambda x: -x[1]["3pm"])

            offensive_ranks: Dict[int, Dict[str, int]] = {}
            for rank, (tid, _) in enumerate(pts_ranked, start=1):
                if tid not in offensive_ranks:
                    offensive_ranks[tid] = {}
                offensive_ranks[tid]["pts"] = rank
            for rank, (tid, _) in enumerate(reb_ranked, start=1):
                if tid not in offensive_ranks:
                    offensive_ranks[tid] = {}
                offensive_ranks[tid]["reb"] = rank
            for rank, (tid, _) in enumerate(ast_ranked, start=1):
                if tid not in offensive_ranks:
                    offensive_ranks[tid] = {}
                offensive_ranks[tid]["ast"] = rank
            for rank, (tid, _) in enumerate(threepm_ranked, start=1):
                if tid not in offensive_ranks:
                    offensive_ranks[tid] = {}
                offensive_ranks[tid]["3pm"] = rank

            cache.set(cache_key, offensive_ranks, ttl=86400)
            logger.info("Offensive ranks calculation complete", teams_ranked=len(offensive_ranks))
            return offensive_ranks
        except Exception as e:
            logger.warning("Error calculating offensive ranks", season=season, error=str(e))
            return {}

    @staticmethod
    def _calculate_team_ranks_from_player_stats(
        season: Optional[str] = None,
    ) -> tuple[Dict[int, Dict[str, int]], Dict[int, Dict[str, int]]]:
        """
        Fallback: compute defensive and offensive ranks purely from player game logs.
        Used when primary _calculate_defensive_ranks / _calculate_offensive_ranks return empty.
        Returns (defensive_ranks, offensive_ranks); each is {team_id: {"pts": rank, "reb": rank, ...}}.
        """
        try:
            cache = get_cache_service()
            season_to_use = season or "2025-26"
            cache_key = f"team_ranks_from_players_fallback:{season_to_use}:24h"
            cached = cache.get(cache_key)
            if cached is not None:
                return _normalize_rank_keys(cached.get("def", {})), _normalize_rank_keys(cached.get("off", {}))

            teams = NBADataService.fetch_all_teams()
            if not teams:
                return {}, {}

            teams_by_abbr: Dict[str, Dict[str, Any]] = {}
            for t in teams:
                abbr = (t.get("abbreviation") or "").strip().upper()
                if abbr:
                    teams_by_abbr[abbr] = t

            team_game_totals: Dict[int, Dict[str, Dict[str, float]]] = {}
            team_defensive_lists: Dict[int, Dict[str, List[float]]] = {}
            for t in teams:
                tid = t.get("id")
                if tid:
                    team_game_totals[tid] = {}
                    team_defensive_lists[tid] = {"pts": [], "reb": [], "ast": [], "3pm": []}

            players_per_team = 5
            games_per_player = 20
            all_players = NBADataService.fetch_all_players_including_rookies()
            players_by_team: Dict[int, List[Dict[str, Any]]] = {}
            for p in all_players:
                team_id = p.get("team_id")
                if team_id:
                    if team_id not in players_by_team:
                        players_by_team[team_id] = []
                    if len(players_by_team[team_id]) < players_per_team:
                        players_by_team[team_id].append(p)

            for team_id, team_players in players_by_team.items():
                if team_id not in team_game_totals:
                    continue
                for player in team_players:
                    player_id = player.get("id")
                    if not player_id:
                        continue
                    try:
                        logs = NBADataService.fetch_player_game_log(player_id, season_to_use)
                    except Exception:
                        continue
                    try:
                        for g in logs[:games_per_player]:
                            gd = g.get("game_date")
                            if not gd:
                                continue
                            if gd not in team_game_totals[team_id]:
                                team_game_totals[team_id][gd] = {"pts": 0.0, "reb": 0.0, "ast": 0.0, "3pm": 0.0}
                            team_game_totals[team_id][gd]["pts"] += float(g.get("pts", 0) or 0)
                            team_game_totals[team_id][gd]["reb"] += float(g.get("reb", 0) or 0)
                            team_game_totals[team_id][gd]["ast"] += float(g.get("ast", 0) or 0)
                            team_game_totals[team_id][gd]["3pm"] += float(g.get("tpm", 0) or 0)

                            # Defense: this game's opponent scoring = points allowed by team_id
                            matchup = (g.get("matchup") or "").upper()
                            opponent_abbr = None
                            for sep in [" VS. ", " VS ", " @ ", " V "]:
                                if sep in matchup:
                                    parts = matchup.split(sep)
                                    if len(parts) == 2:
                                        opponent_abbr = parts[1].strip().strip(" .")
                                        break
                            if not opponent_abbr and team_id in team_defensive_lists:
                                import re
                                match = re.search(r"([A-Z]{2,4})\s+(?:VS\.?|@|V\.?)\s+([A-Z]{2,4})", matchup)
                                if match:
                                    opponent_abbr = match.group(2).strip()
                            if opponent_abbr:
                                opponent_team = teams_by_abbr.get(opponent_abbr)
                                if not opponent_team:
                                    for abbr, ot in teams_by_abbr.items():
                                        if abbr.startswith(opponent_abbr[:2]) or opponent_abbr.startswith(abbr[:2]):
                                            opponent_team = ot
                                            break
                                if opponent_team:
                                    opp_tid = opponent_team.get("id")
                                    opp_players = players_by_team.get(opp_tid, [])[:2]
                                    for opp_p in opp_players:
                                        opp_pid = opp_p.get("id")
                                        if not opp_pid:
                                            continue
                                        try:
                                            opp_logs = NBADataService.fetch_player_game_log(opp_pid, season_to_use)
                                            same_game = next((lg for lg in opp_logs if lg.get("game_date") == gd), None)
                                            if same_game and team_id in team_defensive_lists:
                                                team_defensive_lists[team_id]["pts"].append(float(same_game.get("pts", 0) or 0))
                                                team_defensive_lists[team_id]["reb"].append(float(same_game.get("reb", 0) or 0))
                                                team_defensive_lists[team_id]["ast"].append(float(same_game.get("ast", 0) or 0))
                                                team_defensive_lists[team_id]["3pm"].append(float(same_game.get("tpm", 0) or 0))
                                                break
                                        except Exception:
                                            continue
                    except Exception:
                        continue

            # Offensive averages and ranks
            team_off_avg: Dict[int, Dict[str, float]] = {}
            for tid, games in team_game_totals.items():
                if not games:
                    continue
                n = len(games)
                team_off_avg[tid] = {
                    "pts": sum(x["pts"] for x in games.values()) / n,
                    "reb": sum(x["reb"] for x in games.values()) / n,
                    "ast": sum(x["ast"] for x in games.values()) / n,
                    "3pm": sum(x["3pm"] for x in games.values()) / n,
                }
            pts_o = sorted(team_off_avg.items(), key=lambda x: -x[1]["pts"])
            reb_o = sorted(team_off_avg.items(), key=lambda x: -x[1]["reb"])
            ast_o = sorted(team_off_avg.items(), key=lambda x: -x[1]["ast"])
            pm3_o = sorted(team_off_avg.items(), key=lambda x: -x[1]["3pm"])
            offensive_ranks: Dict[int, Dict[str, int]] = {}
            for rank, (tid, _) in enumerate(pts_o, start=1):
                offensive_ranks.setdefault(tid, {})["pts"] = rank
            for rank, (tid, _) in enumerate(reb_o, start=1):
                offensive_ranks.setdefault(tid, {})["reb"] = rank
            for rank, (tid, _) in enumerate(ast_o, start=1):
                offensive_ranks.setdefault(tid, {})["ast"] = rank
            for rank, (tid, _) in enumerate(pm3_o, start=1):
                offensive_ranks.setdefault(tid, {})["3pm"] = rank

            # Defensive averages (lower = better) and ranks
            team_def_avg: Dict[int, Dict[str, float]] = {}
            for tid, lists in team_defensive_lists.items():
                if not lists["pts"]:
                    continue
                n = len(lists["pts"])
                team_def_avg[tid] = {
                    "pts": sum(lists["pts"]) / n,
                    "reb": sum(lists["reb"]) / n if lists["reb"] else 0,
                    "ast": sum(lists["ast"]) / n if lists["ast"] else 0,
                    "3pm": sum(lists["3pm"]) / n if lists["3pm"] else 0,
                }
            pts_d = sorted(team_def_avg.items(), key=lambda x: x[1]["pts"])
            reb_d = sorted(team_def_avg.items(), key=lambda x: x[1]["reb"])
            ast_d = sorted(team_def_avg.items(), key=lambda x: x[1]["ast"])
            pm3_d = sorted(team_def_avg.items(), key=lambda x: x[1]["3pm"])
            defensive_ranks: Dict[int, Dict[str, int]] = {}
            for rank, (tid, _) in enumerate(pts_d, start=1):
                defensive_ranks.setdefault(tid, {})["pts"] = rank
            for rank, (tid, _) in enumerate(reb_d, start=1):
                defensive_ranks.setdefault(tid, {})["reb"] = rank
            for rank, (tid, _) in enumerate(ast_d, start=1):
                defensive_ranks.setdefault(tid, {})["ast"] = rank
            for rank, (tid, _) in enumerate(pm3_d, start=1):
                defensive_ranks.setdefault(tid, {})["3pm"] = rank

            cache.set(cache_key, {"def": defensive_ranks, "off": offensive_ranks}, ttl=86400)
            logger.info(
                "Team ranks from player stats fallback complete",
                season=season_to_use,
                def_teams=len(defensive_ranks),
                off_teams=len(offensive_ranks),
            )
            return defensive_ranks, offensive_ranks
        except Exception as e:
            logger.warning("Team ranks from player stats fallback failed", season=season, error=str(e))
            return {}, {}

    @staticmethod
    def _get_team_ppg_from_player_logs(season: Optional[str] = None) -> Dict[int, float]:
        """
        Compute each team's PPG from player game logs (sum team pts per game, then average).
        Used when TeamStatsService returns default 112.5 so game prediction page shows real data.
        Returns {team_id: ppg}. Cached 24h.
        """
        try:
            cache = get_cache_service()
            season_to_use = season or "2025-26"
            cache_key = f"team_ppg_from_logs:{season_to_use}:24h"
            cached = cache.get(cache_key)
            if cached is not None and isinstance(cached, dict):
                return {int(k): float(v) for k, v in cached.items() if v is not None and isinstance(v, (int, float))}
            teams = NBADataService.fetch_all_teams()
            if not teams:
                return {}
            team_game_pts: Dict[int, List[float]] = {}
            for t in teams:
                tid = t.get("id")
                if tid:
                    team_game_pts[tid] = []
            players_per_team = 6
            games_per_player = 25
            all_players = NBADataService.fetch_all_players_including_rookies()
            players_by_team: Dict[int, List[Dict[str, Any]]] = {}
            for p in all_players:
                team_id = p.get("team_id")
                if team_id:
                    players_by_team.setdefault(team_id, [])
                    if len(players_by_team[team_id]) < players_per_team:
                        players_by_team[team_id].append(p)
            for team_id, team_players in players_by_team.items():
                if team_id not in team_game_pts:
                    continue
                per_game: Dict[str, float] = {}
                for player in team_players:
                    pid = player.get("id")
                    if not pid:
                        continue
                    try:
                        logs = NBADataService.fetch_player_game_log(pid, season_to_use)
                    except Exception:
                        continue
                    for g in logs[:games_per_player]:
                        gd = g.get("game_date")
                        if not gd:
                            continue
                        per_game[gd] = per_game.get(gd, 0.0) + float(g.get("pts", 0) or 0)
                for pts in per_game.values():
                    if pts > 0:
                        team_game_pts[team_id].append(pts)
            result: Dict[int, float] = {}
            for team_id, pts_list in team_game_pts.items():
                if pts_list:
                    result[team_id] = round(sum(pts_list) / len(pts_list), 1)
            cache.set(cache_key, result, ttl=86400)
            logger.info("Team PPG from logs computed", season=season_to_use, teams_with_ppg=len(result))
            return result
        except Exception as e:
            logger.warning("Team PPG from logs failed", season=season, error=str(e))
            return {}

    @staticmethod
    def get_defensive_averages(season: Optional[str] = None) -> Dict[int, Dict[str, float]]:
        """Return raw per-team defensive averages (avg stats allowed per game). Populated as a side-effect of _calculate_defensive_ranks."""
        cache = get_cache_service()
        season_to_use = season or "2025-26"
        cached = cache.get(f"defensive_avgs:{season_to_use}:24h")
        if cached is not None:
            return _normalize_rank_keys(cached)
        # Trigger ranks calculation which populates the averages cache
        ContextCollector._calculate_defensive_ranks(season_to_use)
        cached = cache.get(f"defensive_avgs:{season_to_use}:24h")
        if cached is not None:
            return _normalize_rank_keys(cached)
        return {}

    @staticmethod
    def _calculate_pace_ranks(season: Optional[str] = None) -> Dict[int, Dict[str, Any]]:
        """
        Calculate pace (possessions per game) for each team.
        Formula: Possessions ≈ FGA + 0.44·FTA + TOV − OREB (summed per game across team players).
        Returns {team_id: {"possessions": float, "pace_rank": int}} — rank 1 = fastest pace.
        Cached 24h.
        """
        try:
            cache = get_cache_service()
            season_to_use = season or "2025-26"
            cache_key = f"pace_ranks:{season_to_use}:24h"
            cached = cache.get(cache_key)
            if cached is not None:
                return _normalize_rank_keys(cached)

            teams = NBADataService.fetch_all_teams()
            if not teams:
                return {}

            players_per_team = 5
            games_per_player = 20
            all_players = NBADataService.fetch_all_players_including_rookies()

            players_by_team: Dict[int, List[Dict[str, Any]]] = {}
            for p in all_players:
                tid = p.get("team_id")
                if tid:
                    players_by_team.setdefault(tid, [])
                    if len(players_by_team[tid]) < players_per_team:
                        players_by_team[tid].append(p)

            # game_date -> {fga, fta, tov, oreb} totals across team players
            team_game_poss: Dict[int, Dict[str, Dict[str, float]]] = {}
            for t in teams:
                tid = t.get("id")
                if tid:
                    team_game_poss[tid] = {}

            for team_id, team_players in players_by_team.items():
                if team_id not in team_game_poss:
                    continue
                for player in team_players:
                    pid = player.get("id")
                    if not pid:
                        continue
                    try:
                        logs = NBADataService.fetch_player_game_log(pid, season_to_use)
                    except Exception:
                        continue
                    for g in logs[:games_per_player]:
                        gd = g.get("game_date")
                        if not gd:
                            continue
                        if gd not in team_game_poss[team_id]:
                            team_game_poss[team_id][gd] = {"fga": 0.0, "fta": 0.0, "tov": 0.0, "oreb": 0.0}
                        team_game_poss[team_id][gd]["fga"] += float(g.get("fga", 0) or 0)
                        team_game_poss[team_id][gd]["fta"] += float(g.get("fta", 0) or 0)
                        team_game_poss[team_id][gd]["tov"] += float(g.get("tov", 0) or 0)
                        team_game_poss[team_id][gd]["oreb"] += float(g.get("oreb", 0) or 0)

            team_avg_poss: Dict[int, float] = {}
            for team_id, games_map in team_game_poss.items():
                if not games_map:
                    continue
                poss_per_game = []
                for _, stats in games_map.items():
                    poss = stats["fga"] + 0.44 * stats["fta"] + stats["tov"] - stats["oreb"]
                    if poss > 0:
                        poss_per_game.append(poss)
                if poss_per_game:
                    team_avg_poss[team_id] = sum(poss_per_game) / len(poss_per_game)

            # rank: highest pace = rank 1 (fastest)
            ranked = sorted(team_avg_poss.items(), key=lambda x: -x[1])
            result: Dict[int, Dict[str, Any]] = {}
            for rank, (tid, poss) in enumerate(ranked, start=1):
                result[tid] = {"possessions": round(poss, 1), "pace_rank": rank}

            cache.set(cache_key, result, ttl=86400)
            logger.info("Pace ranks calculation complete", teams_ranked=len(result))
            return result
        except Exception as e:
            logger.warning("Error calculating pace ranks", season=season, error=str(e))
            return {}

    @staticmethod
    def _calculate_position_defensive_ranks(season: Optional[str] = None) -> Dict[str, Dict[int, Dict[str, int]]]:
        """
        Rank all teams by stats allowed per player position (PG, SG, SF, PF, C).
        Returns {position: {team_id: {pts: rank, reb: rank, ast: rank, 3pm: rank}}}
        Rank 1 = best defense (allows fewest) for that position/stat.
        Cached 24h.
        """
        POSITIONS = ["PG", "SG", "SF", "PF", "C"]
        try:
            cache = get_cache_service()
            season_to_use = season or "2025-26"
            cache_key = f"position_def_ranks:{season_to_use}:24h"
            cached = cache.get(cache_key)
            if cached is not None:
                # Normalize team_id keys to int per position
                return {pos: _normalize_rank_keys(v) for pos, v in cached.items()}

            teams = NBADataService.fetch_all_teams()
            if not teams:
                return {}

            teams_by_abbr = {t.get("abbreviation", "").upper(): t for t in teams if t.get("abbreviation")}

            # position -> opponent_team_id -> {pts: [], reb: [], ast: [], 3pm: []}
            pos_def_stats: Dict[str, Dict[int, Dict[str, List[float]]]] = {
                pos: {} for pos in POSITIONS
            }

            all_players = NBADataService.fetch_all_players_including_rookies()
            players_per_team = 5
            games_per_player = 20

            players_by_team: Dict[int, List[Dict[str, Any]]] = {}
            for p in all_players:
                tid = p.get("team_id")
                if tid:
                    players_by_team.setdefault(tid, [])
                    if len(players_by_team[tid]) < players_per_team:
                        players_by_team[tid].append(p)

            import re as _re

            def _get_opponent_id(matchup: str) -> Optional[int]:
                """Parse opponent team abbreviation from matchup string and return team_id."""
                if not matchup:
                    return None
                mu = matchup.upper().strip()
                m = _re.search(r'([A-Z]{2,4})\s+(?:VS\.?|@|V\.?)\s+([A-Z]{2,4})', mu)
                if m:
                    opp_abbr = m.group(2).strip(" .")
                    team = teams_by_abbr.get(opp_abbr)
                    if team:
                        return team.get("id")
                return None

            for team_id, team_players in players_by_team.items():
                for player in team_players:
                    pid = player.get("id")
                    raw_pos = (player.get("position") or "").upper().strip()
                    # Normalize to one of the 5 positions
                    if raw_pos in ("G", "PG", "GUARD"):
                        position = "PG"
                    elif raw_pos in ("SG", "SHOOTING GUARD"):
                        position = "SG"
                    elif raw_pos in ("SF", "SMALL FORWARD", "F", "FORWARD", "G-F", "F-G"):
                        position = "SF"
                    elif raw_pos in ("PF", "POWER FORWARD", "F-C", "C-F"):
                        position = "PF"
                    elif raw_pos in ("C", "CENTER"):
                        position = "C"
                    else:
                        continue  # skip players with unknown position

                    if not pid:
                        continue
                    try:
                        logs = NBADataService.fetch_player_game_log(pid, season_to_use)
                    except Exception:
                        continue

                    for g in logs[:games_per_player]:
                        opp_id = _get_opponent_id(g.get("matchup", ""))
                        if not opp_id:
                            continue
                        if opp_id not in pos_def_stats[position]:
                            pos_def_stats[position][opp_id] = {"pts": [], "reb": [], "ast": [], "3pm": []}
                        pos_def_stats[position][opp_id]["pts"].append(float(g.get("pts", 0) or 0))
                        pos_def_stats[position][opp_id]["reb"].append(float(g.get("reb", 0) or 0))
                        pos_def_stats[position][opp_id]["ast"].append(float(g.get("ast", 0) or 0))
                        pos_def_stats[position][opp_id]["3pm"].append(float(g.get("tpm", 0) or 0))

            result: Dict[str, Dict[int, Dict[str, int]]] = {}
            for pos in POSITIONS:
                team_avgs: Dict[int, Dict[str, float]] = {}
                for tid, stats in pos_def_stats[pos].items():
                    if not stats["pts"]:
                        continue
                    n = len(stats["pts"])
                    team_avgs[tid] = {
                        "pts": sum(stats["pts"]) / n,
                        "reb": sum(stats["reb"]) / n,
                        "ast": sum(stats["ast"]) / n,
                        "3pm": sum(stats["3pm"]) / n,
                    }
                if not team_avgs:
                    result[pos] = {}
                    continue
                pts_ranked = sorted(team_avgs.items(), key=lambda x: x[1]["pts"])
                reb_ranked = sorted(team_avgs.items(), key=lambda x: x[1]["reb"])
                ast_ranked = sorted(team_avgs.items(), key=lambda x: x[1]["ast"])
                pm3_ranked = sorted(team_avgs.items(), key=lambda x: x[1]["3pm"])
                pos_ranks: Dict[int, Dict[str, int]] = {}
                for rank, (tid, _) in enumerate(pts_ranked, start=1):
                    pos_ranks.setdefault(tid, {})["pts"] = rank
                for rank, (tid, _) in enumerate(reb_ranked, start=1):
                    pos_ranks.setdefault(tid, {})["reb"] = rank
                for rank, (tid, _) in enumerate(ast_ranked, start=1):
                    pos_ranks.setdefault(tid, {})["ast"] = rank
                for rank, (tid, _) in enumerate(pm3_ranked, start=1):
                    pos_ranks.setdefault(tid, {})["3pm"] = rank
                result[pos] = pos_ranks

            cache.set(cache_key, result, ttl=86400)
            logger.info("Position defensive ranks complete", positions=list(result.keys()),
                        sample_pg_teams=len(result.get("PG", {})))
            return result
        except Exception as e:
            logger.warning("Error calculating position defensive ranks", season=season, error=str(e))
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
            # Fallback to previous season if current season has no data (but only if cached)
            team_ranks = {}
            try:
                defensive_ranks = ContextCollector._calculate_defensive_ranks(season_to_use)
                team_ranks = defensive_ranks.get(team_id, {})
                
                # If no ranks for current season, try previous season as fallback
                # BUT only use cached fallback - don't trigger new calculation
                if not team_ranks and len(defensive_ranks) == 0:
                    logger.debug("No defensive ranks for current season, trying cached previous season", team_id=team_id, season=season_to_use)
                    # Check cache directly for fallback season - don't trigger calculation
                    fallback_season = None
                    if season_to_use == "2025-26":
                        fallback_season = "2024-25"
                    elif season_to_use == "2024-25":
                        fallback_season = "2023-24"
                    
                    if fallback_season:
                        fallback_cache_key = f"defensive_ranks:{fallback_season}:24h"
                        fallback_ranks = cache.get(fallback_cache_key)
                        if fallback_ranks:
                            team_ranks = fallback_ranks.get(team_id, {})
                            if team_ranks:
                                logger.info("Using cached previous season defensive ranks as fallback", team_id=team_id, season=fallback_season)
                        else:
                            logger.debug("Fallback season not cached, skipping to avoid blocking", team_id=team_id, season=fallback_season)
                
                # Log if defensive ranks are missing for debugging (only log once per team to avoid spam)
                if not team_ranks and len(defensive_ranks) > 0:
                    logger.debug("No defensive ranks found for team", team_id=team_id, season=season_to_use, total_ranks=len(defensive_ranks))
                elif not team_ranks:
                    logger.warning("Defensive ranks calculation returned empty - may still be calculating", team_id=team_id, season=season_to_use)
            except Exception as e:
                logger.warning("Error getting defensive ranks, trying cached fallback", team_id=team_id, error=str(e))
                # Try cached fallback season on error too - don't trigger calculation
                try:
                    fallback_season = None
                    if season_to_use == "2025-26":
                        fallback_season = "2024-25"
                    elif season_to_use == "2024-25":
                        fallback_season = "2023-24"
                    
                    if fallback_season:
                        fallback_cache_key = f"defensive_ranks:{fallback_season}:24h"
                        fallback_ranks = cache.get(fallback_cache_key)
                        if fallback_ranks:
                            team_ranks = fallback_ranks.get(team_id, {})
                except Exception as fallback_error:
                    logger.warning("Fallback defensive ranks check also failed", team_id=team_id, error=str(fallback_error))
                    team_ranks = {}
            
            # Offensive ranks (team's own scoring/reb/ast/3pm — higher = better offense)
            offensive_ranks = ContextCollector._calculate_offensive_ranks(season_to_use)
            off_ranks = offensive_ranks.get(team_id, {})
            
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
                "def_rank_ast": team_ranks.get("ast"),
                "def_rank_3pm": team_ranks.get("3pm"),
                "off_rank_pts": off_ranks.get("pts"),
                "off_rank_reb": off_ranks.get("reb"),
                "off_rank_ast": off_ranks.get("ast"),
                "off_rank_3pm": off_ranks.get("3pm"),
            }
            
            # Log the result for debugging
            logger.debug("Team performance retrieved", team_id=team_id, def_rank_pts=result["def_rank_pts"], def_rank_3pm=result["def_rank_3pm"], off_rank_pts=result["off_rank_pts"])
            
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
            "def_rank_ast": None,
            "def_rank_3pm": None,
            "off_rank_pts": None,
            "off_rank_reb": None,
            "off_rank_ast": None,
            "off_rank_3pm": None,
        }
        # Cache error result for shorter time (1 hour)
        if team_id:
            cache = get_cache_service()
            season_to_use = season or "2025-26"
            cache_key = f"team_performance:{team_id}:{season_to_use}:1h"
            cache.set(cache_key, result, ttl=3600)
        return result
    
    @staticmethod
    def _minutes_played(g: Dict) -> float:
        """Parse minutes from a game log entry (handles number or 'MM:SS')."""
        m = g.get("minutes") or g.get("MIN") or 0
        if m is None:
            return 0.0
        if isinstance(m, str) and ":" in str(m):
            parts = str(m).split(":")
            return float(parts[0]) + (float(parts[1]) / 60.0) if len(parts) >= 2 else 0.0
        try:
            return float(m) if m else 0.0
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _infer_injury_from_recent_minutes(
        player_id: int, game_date: date, season: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        When ESPN says no injury, infer possible injury from recent minutes:
        1) DNP / no minutes in last game(s) → strong signal (questionable).
        2) Played half (or less) of normal minutes in last game(s) → potentially hurt (questionable).
        Returns a result dict to use as injury_info, or None if no inference.
        """
        try:
            season_str = season or current_candidate_season()
            logs = NBADataService.fetch_player_game_log(player_id, season_str)
            if not logs or len(logs) < 1:
                return None
            recent = logs[: max(3, RECENT_GAMES_TO_CHECK)]
            mins = [ContextCollector._minutes_played(g) for g in recent]

            # —— Tier 1: DNP / no minutes ——
            no_minutes_count = sum(1 for m in mins if m < MIN_MINUTES_PLAYED_THRESHOLD)
            if no_minutes_count >= len(recent):
                return {
                    "is_injured": True,
                    "injury_status": "questionable",
                    "injury_description": "No minutes in last game(s) — check availability",
                    "injury_date": None,
                }
            if len(mins) >= 1 and mins[0] < MIN_MINUTES_PLAYED_THRESHOLD:
                return {
                    "is_injured": True,
                    "injury_status": "questionable",
                    "injury_description": "DNP last game — check availability",
                    "injury_date": None,
                }

            # —— Tier 2: "Normal" baseline from season (exclude DNPs) ——
            all_mins = [ContextCollector._minutes_played(g) for g in logs]
            baseline_mins = [
                m for m in all_mins
                if m >= MIN_MINUTES_TO_COUNT_FOR_BASELINE
            ]
            if len(baseline_mins) < MIN_GAMES_FOR_BASELINE_MINUTES:
                return None
            normal_avg = sum(baseline_mins) / len(baseline_mins)
            half_normal = normal_avg * HALF_NORMAL_MINUTES_RATIO

            # —— Last game well below normal (e.g. half or less) → potentially hurt ——
            last_min = mins[0]
            if last_min <= half_normal and last_min >= MIN_MINUTES_PLAYED_THRESHOLD:
                desc = f"Below normal minutes ({int(last_min)} min vs ~{int(round(normal_avg))} avg) — check availability"
                return {
                    "is_injured": True,
                    "injury_status": "questionable",
                    "injury_description": desc,
                    "injury_date": None,
                }

            # —— Last 2 games both below half normal ——
            if len(mins) >= 2 and all(m >= MIN_MINUTES_PLAYED_THRESHOLD for m in mins[:2]):
                if mins[0] <= half_normal and mins[1] <= half_normal:
                    avg_recent = (mins[0] + mins[1]) / 2
                    desc = f"Last 2 games below normal minutes (~{int(avg_recent)} vs ~{int(round(normal_avg))} avg) — check availability"
                    return {
                        "is_injured": True,
                        "injury_status": "questionable",
                        "injury_description": desc,
                        "injury_date": None,
                    }

            return None
        except Exception as e:
            logger.debug("Could not infer injury from minutes", player_id=player_id, error=str(e))
            return None

    @staticmethod
    def get_injury_status(player_id: int, game_date: date) -> Dict[str, Any]:
        """
        Get injury status for a player from ESPN API.
        When ESPN has no injury listed, infers possible injury from recent minutes
        (no minutes in last game(s) → questionable / check availability).
        
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
                # No ESPN injury data — try inferring from recent minutes (DNP / 0 min)
                inferred = ContextCollector._infer_injury_from_recent_minutes(player_id, game_date)
                result = inferred if inferred else {
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
            
            # No injury found in ESPN — infer from recent minutes (DNP / 0 min) to avoid showing "Healthy" when they didn't play
            inferred = ContextCollector._infer_injury_from_recent_minutes(player_id, game_date)
            result = inferred if inferred else {
                "is_injured": False,
                "injury_status": None,
                "injury_description": None,
                "injury_date": None
            }
            # Cache for 4 hours - injuries change infrequently (1-2 times per day)
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

