"""
Daily Props Service - Computes top props for all players playing on a given day.
"""
from __future__ import annotations
from typing import List, Dict, Optional
from datetime import datetime
from .nba_api_service import NBADataService
from .prop_engine import PropBetEngine
from .prop_filter import PropFilter
from ..core.config import current_candidate_season


class DailyPropsService:
    """Service for computing and ranking daily prop bets for players playing today."""
    
    # Stat types to compute props for
    STAT_TYPES = ["pts", "reb", "ast", "tpm"]
    
    @staticmethod
    def _compute_props_for_player(
        player_id: int, 
        player_name: str, 
        season: Optional[str] = None,
        last_n: Optional[int] = None,
        game_date: Optional[str] = None
    ) -> List[Dict]:
        """
        Compute props for a single player.
        
        Args:
            player_id: NBA player ID
            player_name: Player's full name
            season: Season string (e.g., "2025-26")
            last_n: Optional limit to last N games
            
        Returns:
            List of prop suggestions with player info
        """
        try:
            # Fetch player game logs - try current season first, then fallback to previous season
            logs = NBADataService.fetch_player_game_log(player_id, season)
            
            # If no logs for current season, try previous season as fallback
            if not logs and season:
                # Extract year from season string (e.g., "2025-26" -> "2024-25")
                try:
                    year_part = season.split("-")[0]
                    prev_year = int(year_part) - 1
                    prev_season = f"{prev_year}-{str(prev_year + 1)[-2:]}"
                    logs = NBADataService.fetch_player_game_log(player_id, prev_season)
                except Exception:
                    pass
            
            if not logs:
                return []
            
            # Apply last_n filter if provided
            if last_n and last_n > 0:
                logs = logs[-last_n:]
            
            # Enrich with PRA (Points + Rebounds + Assists)
            for game in logs:
                game["pra"] = (
                    float(game.get("pts", 0) or 0) + 
                    float(game.get("reb", 0) or 0) + 
                    float(game.get("ast", 0) or 0)
                )
            
            suggestions: List[Dict] = []
            
            # Compute props for each stat type
            for stat_key in DailyPropsService.STAT_TYPES:
                try:
                    # Determine fair line based on player's recent performance
                    fair_line = PropBetEngine.determine_line_value(logs, stat_key)
                    
                    # Check if AI is enabled globally
                    try:
                        from ..services.settings_service import SettingsService
                        ai_enabled = SettingsService.get_ai_enabled()
                    except Exception:
                        ai_enabled = False
                    
                    # Map stat key to display format
                    display_map = {
                        "pts": "PTS",
                        "reb": "REB", 
                        "ast": "AST",
                        "tpm": "3PM"
                    }
                    
                    # Evaluate BOTH over and under to find the best suggestions
                    for direction in ["over", "under"]:
                        try:
                            # Use AI-enhanced evaluation if enabled for better accuracy
                            # For comprehensive league-wide scan, we want the best predictions
                            if ai_enabled and game_date:
                                try:
                                    from datetime import datetime
                                    game_date_obj = datetime.strptime(game_date, "%Y-%m-%d").date() if isinstance(game_date, str) else game_date
                                    evaluation = PropBetEngine.evaluate_prop_with_ml(
                                        logs, stat_key, fair_line, direction,
                                        player_id=player_id,
                                        game_date=game_date_obj,
                                        opponent_team_id=None,
                                        is_home_game=True,
                                        season=season
                                    )
                                except Exception:
                                    # Fallback to rule-based if AI fails
                                    evaluation = PropBetEngine.evaluate_prop(logs, stat_key, fair_line, direction)
                            else:
                                evaluation = PropBetEngine.evaluate_prop(logs, stat_key, fair_line, direction)
                            
                            # Only include if the evaluation suggests this direction and has reasonable confidence
                            eval_suggestion = evaluation.get("suggestion", "over")
                            confidence = evaluation.get("confidence", 0)
                            
                            # Include if:
                            # 1. The evaluation suggests this direction, OR
                            # 2. The confidence is high enough (>= 50) regardless of default suggestion
                            if eval_suggestion == direction or confidence >= 50:
                                suggestion = {
                                    "type": display_map.get(stat_key, stat_key.upper()),
                                    "playerId": player_id,
                                    "playerName": player_name,
                                    "marketLine": fair_line,
                                    "fairLine": fair_line,
                                    "confidence": confidence,
                                    "suggestion": direction,
                                    "rationale": evaluation.get("rationale", {}).get("summary", "Based on recent form and hit rate"),
                                    "stats": evaluation.get("stats", {}),
                                    "gameDate": game_date,
                                }
                                suggestions.append(suggestion)
                        except Exception:
                            # Skip this direction if evaluation fails
                            continue
                except Exception:
                    # Skip this stat type if computation fails
                    continue
            
            # Also compute PRA prop - evaluate both over and under
            try:
                fair_line_pra = PropBetEngine.determine_line_value(logs, "pra")
                
                for direction in ["over", "under"]:
                    try:
                        evaluation_pra = PropBetEngine.evaluate_prop(logs, "pra", fair_line_pra, direction)
                        eval_suggestion = evaluation_pra.get("suggestion", "over")
                        confidence = evaluation_pra.get("confidence", 0)
                        
                        # Include if evaluation suggests this direction or confidence is high enough
                        if eval_suggestion == direction or confidence >= 50:
                            suggestion_pra = {
                                "type": "PRA",
                                "playerId": player_id,
                                "playerName": player_name,
                                "marketLine": fair_line_pra,
                                "fairLine": fair_line_pra,
                                "confidence": confidence,
                                "suggestion": direction,
                                "rationale": evaluation_pra.get("rationale", {}).get("summary", "Based on recent form and hit rate"),
                                "stats": evaluation_pra.get("stats", {}),
                                "gameDate": game_date,
                            }
                            suggestions.append(suggestion_pra)
                    except Exception:
                        continue
            except Exception:
                pass
                
            return suggestions
            
        except Exception:
            # Return empty list if player data fetch fails
            return []
    
    @staticmethod
    def get_top_props_for_date(
        date: Optional[str] = None,
        season: Optional[str] = None,
        min_confidence: Optional[float] = None,
        limit: int = 50,
        last_n: Optional[int] = None
    ) -> Dict:
        """
        Get top props for all players playing on a given date.
        
        Args:
            date: Date string (optional, defaults to today)
            season: Season string (e.g., "2025-26", defaults to "2025-26")
            min_confidence: Minimum confidence threshold (optional)
            limit: Maximum number of props to return
            last_n: Optional limit to last N games for computation
            
        Returns:
            Dictionary with "items" list of top props
        """
        season = season or "2025-26"  # Default to 2025-26 season
        
        # Get the date for game_date field - use provided date or today in UTC
        from datetime import datetime, timezone
        if date:
            # Use provided date
            target_date = date
        else:
            # Use today's date in UTC to match frontend
            target_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Get today's games (includes scheduled, live, and recently completed games)
        try:
            games = NBADataService.fetch_todays_games()
            # Filter to include all games for today regardless of status
            # (scheduled, in progress, or recently finished)
            games = [g for g in games if g.get("home") and g.get("away")]
        except Exception:
            games = []
        
        # Extract team abbreviations from games
        team_abbrs = set()
        for game in games:
            if game.get("home"):
                team_abbrs.add(game.get("home"))
            if game.get("away"):
                team_abbrs.add(game.get("away"))
        
        all_props: List[Dict] = []
        team_ids_today: set = set()  # Initialize outside the if block
        
        if team_abbrs:
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
            # Filter out None values
            team_ids_today = {tid for tid in team_ids_today if tid is not None}
            
            # Get all players (including rookies) who are on today's teams
            all_players = NBADataService.fetch_all_players_including_rookies() or []
            
            # Filter to players on today's teams
            # Use TeamPlayerService to normalize team IDs
            from .team_player_service import TeamPlayerService
            team_ids_today_int = {TeamPlayerService.normalize_team_id(tid) for tid in team_ids_today}
            team_ids_today_int.discard(None)  # Remove None values
            
            todays_players = []
            for p in all_players:
                player_team_id = TeamPlayerService.normalize_team_id(p.get("team_id"))
                if player_team_id is not None and player_team_id in team_ids_today_int:
                    todays_players.append(p)
            
            # If still no players found, but we have games, try to match by team abbreviation
            # This is a last resort when team ID mapping completely fails
            if len(todays_players) == 0 and team_abbrs:
                # Try to match players by team abbreviation if available
                # This is more reliable than just taking any player
                teams = NBADataService.fetch_all_teams() or []
                team_id_to_abbr = {t.get("id"): t.get("abbreviation") for t in teams if t.get("id") and t.get("abbreviation")}
                
                for player in all_players:
                    player_team_id = player.get("team_id")
                    if not player_team_id:
                        continue
                    
                    # Check if player's team abbreviation matches any of today's teams
                    player_team_abbr = team_id_to_abbr.get(player_team_id)
                    if player_team_abbr and player_team_abbr in team_abbrs:
                        todays_players.append(player)
                        if len(todays_players) >= 60:
                            break
            
            # Process ALL players on today's teams - comprehensive league-wide scan
            # No limit on players - we want to check everyone playing today
            
            # Process players in parallel for better performance
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import threading
            
            # Use a lock to safely append to all_props
            props_lock = threading.Lock()
            # Collect enough props for comprehensive results
            max_props_needed = limit * 5 if limit else 1000  # Collect more for better sorting
            
            def process_player(player):
                """Process a single player and return props"""
                player_id = player.get("id")
                player_name = player.get("full_name", "Unknown Player")
                
                if not player_id:
                    return []
                
                try:
                    # Compute props for this player
                    props = DailyPropsService._compute_props_for_player(
                        player_id=player_id,
                        player_name=player_name,
                        season=season,
                        last_n=last_n or 10,  # Use 10 games for comprehensive analysis
                        game_date=target_date
                    )
                    return props or []
                except Exception:
                    # Skip this player if computation fails
                    return []
            
            # Process players in parallel with more workers for comprehensive scan
            # Use more workers since we're processing all players
            with ThreadPoolExecutor(max_workers=12) as executor:  # Increased workers for comprehensive scan
                # Submit all player processing tasks
                future_to_player = {
                    executor.submit(process_player, player): player 
                    for player in todays_players
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_player):
                    try:
                        props = future.result(timeout=5.0)  # Longer timeout for comprehensive scan
                        if props:
                            with props_lock:
                                all_props.extend(props)
                                # Only stop early if we have way more than needed (for efficiency)
                                if limit and len(all_props) >= max_props_needed:
                                    # Cancel remaining tasks only if we have way more than needed
                                    for f in future_to_player:
                                        f.cancel()
                                    break
                    except Exception:
                        # Skip failed players
                        continue
        
        # If we have games but no props yet, try fallback featured players
        # ONLY include featured players if they're actually on today's teams
        if len(all_props) == 0 and team_abbrs and team_ids_today:
            # Fallback: use featured players ONLY if they're on today's teams
            # (handles edge cases where regular players on today's teams have no data)
            featured_player_ids = [2544, 201939, 203507, 1629029, 203076]
            all_players = NBADataService.fetch_all_players_including_rookies() or []
            player_map = {p.get("id"): p for p in all_players}
            
            for player_id in featured_player_ids:
                player = player_map.get(player_id)
                if not player:
                    continue
                
                # ONLY include featured players if they're on today's teams
                # Use TeamPlayerService to normalize team_id
                from .team_player_service import TeamPlayerService
                player_team_id = TeamPlayerService.normalize_team_id(player.get("team_id"))
                if player_team_id is None:
                    continue
                
                team_ids_today_int = {TeamPlayerService.normalize_team_id(tid) for tid in team_ids_today}
                team_ids_today_int.discard(None)
                should_include = player_team_id in team_ids_today_int
                
                if should_include:
                    try:
                        player_name = player.get("full_name", "Unknown Player")
                        props = DailyPropsService._compute_props_for_player(
                            player_id=player_id,
                            player_name=player_name,
                            season=season,
                            last_n=last_n,
                            game_date=target_date
                        )
                        
                        if props:
                            all_props.extend(props)
                    except Exception:
                        continue
        
        # Filter by minimum confidence if specified
        props_before_filter = all_props.copy() if all_props else []
        if min_confidence:
            all_props = PropFilter.filter_by_confidence(all_props, min_confidence)
        
        # Ensure all props have gameDate set
        for prop in all_props:
            if not prop.get("gameDate"):
                prop["gameDate"] = target_date
        
        # If we still have no props after all processing
        if len(all_props) == 0:
            # If no games today, return empty (don't show bets for games that aren't happening)
            if not team_abbrs:
                return {
                    "items": [],
                    "total": 0,
                    "returned": 0,
                    "date": date or datetime.now().strftime("%Y-%m-%d"),
                    "season": season,
                    "message": "No games scheduled for today"
                }
            # If games today but confidence filter removed everything, use unfiltered props
            if len(props_before_filter) > 0:
                all_props = props_before_filter
            # If still no props but games exist, use featured players as absolute fallback
            elif len(props_before_filter) == 0 and team_abbrs:
                # Last resort: if games exist but we couldn't compute props, use featured players
                # This ensures we always return something when games are scheduled
                featured_player_ids = [2544, 201939, 203507, 1629029, 203076]
                all_players = NBADataService.fetch_all_players_including_rookies() or []
                player_map = {p.get("id"): p for p in all_players}
                
                for player_id in featured_player_ids[:5]:  # Try up to 5 featured players
                    player = player_map.get(player_id)
                    if not player:
                        continue
                    try:
                        player_name = player.get("full_name", "Unknown Player")
                        props = DailyPropsService._compute_props_for_player(
                            player_id=player_id,
                            player_name=player_name,
                            season=season,
                            last_n=last_n or 10,
                            game_date=target_date  # Pass game_date to featured players too
                        )
                        if props:
                            all_props.extend(props)
                            # Once we have some props, we can stop (or continue for more)
                            if len(all_props) >= 20:  # Get a good sample
                                break
                    except Exception:
                        continue
        
        # Rank by confidence (descending)
        ranked_props = PropFilter.rank_suggestions(all_props, "confidence")
        
        # Return top N
        top_props = ranked_props[:max(1, limit)]
        
        return {
            "items": top_props,
            "total": len(all_props),
            "returned": len(top_props),
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "season": season
        }

