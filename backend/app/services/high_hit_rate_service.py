"""
High Hit Rate Bets Service - Finds props with historically high hit rates
"""
from __future__ import annotations
from typing import List, Dict, Optional
from datetime import datetime
from .nba_api_service import NBADataService
from .prop_engine import PropBetEngine
from .stats_calculator import StatsCalculator
from ..core.config import current_candidate_season


class HighHitRateService:
    """Service for finding props with historically high hit rates"""
    
    STAT_TYPES = ["pts", "reb", "ast", "tpm"]
    
    @staticmethod
    def get_high_hit_rate_bets(
        date: Optional[str] = None,
        season: Optional[str] = None,
        min_hit_rate: float = 0.75,
        limit: int = 10,
        last_n: Optional[int] = None
    ) -> Dict:
        """
        Get props with high historical hit rates for players playing today.
        
        Args:
            date: Date to check (YYYY-MM-DD), defaults to today
            season: Season string, defaults to current season
            min_hit_rate: Minimum hit rate threshold (0.0-1.0), default 0.75 (75%)
            limit: Maximum number of results to return
            last_n: Number of recent games to consider for hit rate calculation
        
        Returns:
            Dict with items list and metadata
        """
        if not season:
            season = "2025-26"  # Default to 2025-26 season
        
        # Get the date for game_date field - use provided date or today in UTC
        from datetime import timezone
        if date:
            # Use provided date
            target_date = date
        else:
            # Use today's date in UTC to match frontend
            target_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Get today's games
        games = NBADataService.fetch_todays_games()
        if not games:
            return {
                "items": [],
                "total": 0,
                "returned": 0,
                "date": date or datetime.now().strftime("%Y-%m-%d"),
                "season": season,
                "message": "No games scheduled for today"
            }
        
        # Extract team abbreviations from today's games
        team_abbrs = set()
        for game in games:
            if game.get("home"):
                team_abbrs.add(game.get("home"))
            if game.get("away"):
                team_abbrs.add(game.get("away"))
        
        if not team_abbrs:
            return {
                "items": [],
                "total": 0,
                "returned": 0,
                "date": date or datetime.now().strftime("%Y-%m-%d"),
                "season": season,
                "message": "No games scheduled for today"
            }
        
        # Get all players including rookies
        all_players = NBADataService.fetch_all_players_including_rookies() or []
        
        # Map team abbreviations to team IDs
        teams = NBADataService.fetch_all_teams() or []
        abbr_to_id = {
            t.get("abbreviation"): t.get("id") 
            for t in teams if t.get("abbreviation")
        }
        team_ids_today = {
            abbr_to_id.get(ab) 
            for ab in team_abbrs 
            if ab in abbr_to_id and abbr_to_id.get(ab) is not None
        }
        team_ids_today = {tid for tid in team_ids_today if tid is not None}
        
        # Use TeamPlayerService to normalize team IDs
        from .team_player_service import TeamPlayerService
        team_ids_today_int = {TeamPlayerService.normalize_team_id(tid) for tid in team_ids_today}
        team_ids_today_int.discard(None)  # Remove None values
        
        # Filter to players on today's teams
        todays_players = []
        for p in all_players:
            player_team_id = TeamPlayerService.normalize_team_id(p.get("team_id"))
            if player_team_id is not None and player_team_id in team_ids_today_int:
                todays_players.append(p)
        
        # Limit to reasonable number to avoid timeout (reduced for faster response)
        if len(todays_players) > 40:
            todays_players = todays_players[:40]
        
        all_props: List[Dict] = []
        
        # Process each player
        for player in todays_players:
            player_id = player.get("id")
            player_name = player.get("full_name", "Unknown Player")
            
            if not player_id:
                continue
            
            try:
                # Get player game logs - ONLY use current season
                # If player doesn't have stats from current season, exclude them
                logs = NBADataService.fetch_player_game_log(player_id, season)
                if not logs or len(logs) < 5:  # Need at least 5 games for meaningful hit rate
                    continue
                
                # Verify logs are from the requested season by checking game dates
                # This ensures we're not using stale data from a different season
                if season:
                    # Extract year from season string (e.g., "2025-26" -> 2025)
                    try:
                        season_year = int(season.split("-")[0])
                        # Check if any logs have game dates from the current season
                        has_current_season_logs = False
                        for log in logs:
                            game_date = log.get("game_date", "")
                            if game_date:
                                # Parse date and check if it's from current season (Oct 2024 - Jun 2025 for 2024-25 season)
                                try:
                                    from datetime import datetime
                                    date_obj = datetime.strptime(game_date.split("T")[0] if "T" in game_date else game_date, "%Y-%m-%d")
                                    # Season starts in October, so for 2025-26 season, dates should be Oct 2025 onwards
                                    if date_obj.year >= season_year:
                                        has_current_season_logs = True
                                        break
                                except (ValueError, AttributeError):
                                    pass
                        
                        # If no current season logs found, skip this player
                        if not has_current_season_logs:
                            continue
                    except (ValueError, AttributeError):
                        # If we can't parse season, still include player (backward compatibility)
                        pass
                
                # Filter by minimum average minutes (22 minutes)
                minutes_list = [float(game.get("minutes", 0) or 0) for game in logs if game.get("minutes")]
                if minutes_list:
                    avg_minutes = sum(minutes_list) / len(minutes_list)
                    if avg_minutes < 22.0:
                        # Player doesn't meet minimum minutes threshold
                        continue
                
                # Use last_n games if specified, otherwise use all games
                logs_for_hit_rate = logs[-last_n:] if last_n else logs
                
                # Compute props for each stat type
                for stat_key in HighHitRateService.STAT_TYPES:
                    try:
                        # Determine fair line based on recent performance
                        fair_line = PropBetEngine.determine_line_value(logs, stat_key)
                        
                        # Check a range of lines: -2.5, -1.5, fair, +1.5, +2.5
                        lines_to_check = [
                            fair_line - 2.5,
                            fair_line - 1.5,
                            fair_line,
                            fair_line + 1.5,
                            fair_line + 2.5
                        ]
                        
                        best_suggestion = None
                        best_hit_rate = 0.0
                        best_line = None
                        best_direction = None
                        
                        # Check each line and both directions (over/under)
                        for line_value in lines_to_check:
                            # Skip negative lines (not valid for stats)
                            if line_value < 0:
                                continue
                            
                            # Round to nearest 0.5 for consistency
                            line_value = round(line_value * 2) / 2.0
                            
                            # Check both "over" and "under" directions
                            for direction in ["over", "under"]:
                                # Calculate hit rate for this line and direction
                                hit_rate = StatsCalculator.calculate_hit_rate(
                                    logs_for_hit_rate, 
                                    line_value, 
                                    stat_key, 
                                    direction
                                )
                                
                                # Only consider if it meets the minimum threshold
                                if hit_rate >= min_hit_rate:
                                    # If this is better than what we have, save it
                                    if hit_rate > best_hit_rate:
                                        best_hit_rate = hit_rate
                                        best_line = line_value
                                        best_direction = direction
                        
                        # Only add if we found a suggestion that meets the threshold
                        if best_suggestion is None and best_line is not None:
                            # Calculate full evaluation for the best line/direction
                            evaluation = PropBetEngine.evaluate_prop(
                                logs, 
                                stat_key, 
                                best_line, 
                                best_direction
                            )
                            
                            # Map stat key to display format
                            display_map = {
                                "pts": "PTS",
                                "reb": "REB",
                                "ast": "AST",
                                "tpm": "3PM"
                            }
                            
                            # Calculate sample size
                            sample_size = len(logs_for_hit_rate)
                            
                            best_suggestion = {
                                "type": display_map.get(stat_key, stat_key.upper()),
                                "playerId": player_id,
                                "playerName": player_name,
                                "marketLine": best_line,  # Use the best line found
                                "fairLine": fair_line,  # Keep original fair line for reference
                                "confidence": evaluation.get("confidence", 0),
                                "suggestion": best_direction,  # Use the direction with best hit rate
                                "hitRate": round(best_hit_rate * 100, 1),  # Convert to percentage
                                "sampleSize": sample_size,
                                "rationale": evaluation.get("rationale", {}).get("summary", ""),
                                "stats": evaluation.get("stats", {}),
                                "gameDate": target_date,
                            }
                        
                        if best_suggestion:
                            all_props.append(best_suggestion)
                        
                        # Early exit if we have enough high-quality props
                        if len(all_props) >= limit * 2:  # Collect extra for better sorting
                            break
                    except Exception:
                        # Skip this stat type if computation fails
                        continue
                
                # Early exit if we have enough props
                if len(all_props) >= limit * 2:
                    break
                
                # Also compute PRA prop with range checking
                try:
                    # Enrich logs with PRA
                    enriched_logs = []
                    for log in logs:
                        pra = float(log.get("pts", 0) or 0) + float(log.get("reb", 0) or 0) + float(log.get("ast", 0) or 0)
                        enriched_log = {**log, "pra": pra}
                        enriched_logs.append(enriched_log)
                    
                    enriched_logs_for_hit_rate = enriched_logs[-last_n:] if last_n else enriched_logs
                    
                    fair_line_pra = PropBetEngine.determine_line_value(enriched_logs, "pra")
                    
                    # Check a range of lines: -2.5, -1.5, fair, +1.5, +2.5
                    pra_lines_to_check = [
                        fair_line_pra - 2.5,
                        fair_line_pra - 1.5,
                        fair_line_pra,
                        fair_line_pra + 1.5,
                        fair_line_pra + 2.5
                    ]
                    
                    best_pra_suggestion = None
                    best_pra_hit_rate = 0.0
                    best_pra_line = None
                    best_pra_direction = None
                    
                    # Check each line and both directions
                    for line_value in pra_lines_to_check:
                        # Skip negative lines
                        if line_value < 0:
                            continue
                        
                        # Round to nearest 0.5 for consistency
                        line_value = round(line_value * 2) / 2.0
                        
                        for direction in ["over", "under"]:
                            hit_rate_pra = StatsCalculator.calculate_hit_rate(
                                enriched_logs_for_hit_rate, 
                                line_value, 
                                "pra", 
                                direction
                            )
                            
                            if hit_rate_pra >= min_hit_rate and hit_rate_pra > best_pra_hit_rate:
                                best_pra_hit_rate = hit_rate_pra
                                best_pra_line = line_value
                                best_pra_direction = direction
                    
                    # Only add if we found a suggestion that meets the threshold
                    if best_pra_suggestion is None and best_pra_line is not None:
                        evaluation_pra = PropBetEngine.evaluate_prop(
                            enriched_logs, 
                            "pra", 
                            best_pra_line, 
                            best_pra_direction
                        )
                        sample_size_pra = len(enriched_logs_for_hit_rate)
                        
                        best_pra_suggestion = {
                            "type": "PRA",
                            "playerId": player_id,
                            "playerName": player_name,
                            "marketLine": best_pra_line,  # Use the best line found
                            "fairLine": fair_line_pra,  # Keep original fair line for reference
                            "confidence": evaluation_pra.get("confidence", 0),
                            "suggestion": best_pra_direction,  # Use the direction with best hit rate
                            "hitRate": round(best_pra_hit_rate * 100, 1),
                            "sampleSize": sample_size_pra,
                            "rationale": evaluation_pra.get("rationale", {}).get("summary", ""),
                            "stats": evaluation_pra.get("stats", {}),
                            "gameDate": target_date,
                        }
                    
                    if best_pra_suggestion:
                        all_props.append(best_pra_suggestion)
                except Exception:
                    continue
                    
            except Exception:
                # Skip this player if computation fails
                continue
        
        # Sort by hit rate (descending), then by confidence
        all_props.sort(key=lambda x: (x.get("hitRate", 0), x.get("confidence", 0)), reverse=True)
        
        # Return top N
        top_props = all_props[:limit]
        
        return {
            "items": top_props,
            "total": len(all_props),
            "returned": len(top_props),
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "season": season,
            "min_hit_rate": min_hit_rate
        }

