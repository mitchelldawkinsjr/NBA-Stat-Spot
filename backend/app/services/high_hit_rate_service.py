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
            season = current_candidate_season()
        
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
        
        # Filter to players on today's teams
        todays_players = [
            p for p in all_players 
            if p.get("team_id") and p.get("team_id") in team_ids_today
        ]
        
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
                # Get player game logs
                logs = NBADataService.fetch_player_game_log(player_id, season)
                if not logs or len(logs) < 5:  # Need at least 5 games for meaningful hit rate
                    continue
                
                # Use last_n games if specified, otherwise use all games
                logs_for_hit_rate = logs[-last_n:] if last_n else logs
                
                # Compute props for each stat type
                for stat_key in HighHitRateService.STAT_TYPES:
                    try:
                        # Determine fair line based on recent performance
                        fair_line = PropBetEngine.determine_line_value(logs, stat_key)
                        
                        # Calculate hit rate using all available games (or last_n)
                        hit_rate = StatsCalculator.calculate_hit_rate(logs_for_hit_rate, fair_line, stat_key)
                        
                        # Only include if hit rate meets threshold
                        if hit_rate < min_hit_rate:
                            continue
                        
                        # Calculate confidence for display
                        evaluation = PropBetEngine.evaluate_prop(logs, stat_key, fair_line)
                        
                        # Map stat key to display format
                        display_map = {
                            "pts": "PTS",
                            "reb": "REB",
                            "ast": "AST",
                            "tpm": "3PM"
                        }
                        
                        # Calculate sample size (number of games used)
                        sample_size = len(logs_for_hit_rate)
                        
                        suggestion = {
                            "type": display_map.get(stat_key, stat_key.upper()),
                            "playerId": player_id,
                            "playerName": player_name,
                            "marketLine": fair_line,
                            "fairLine": fair_line,
                            "confidence": evaluation.get("confidence", 0),
                            "suggestion": evaluation.get("suggestion", "over"),
                            "hitRate": round(hit_rate * 100, 1),  # Convert to percentage
                            "sampleSize": sample_size,
                            "rationale": evaluation.get("rationale", {}).get("summary", ""),
                            "stats": evaluation.get("stats", {}),
                            "gameDate": target_date,  # Add game date for today's games
                        }
                        
                        all_props.append(suggestion)
                        
                        # Early exit if we have enough high-quality props
                        if len(all_props) >= limit * 2:  # Collect extra for better sorting
                            break
                    except Exception:
                        # Skip this stat type if computation fails
                        continue
                
                # Early exit if we have enough props
                if len(all_props) >= limit * 2:
                    break
                
                # Also compute PRA prop
                try:
                    # Enrich logs with PRA
                    enriched_logs = []
                    for log in logs:
                        pra = float(log.get("pts", 0) or 0) + float(log.get("reb", 0) or 0) + float(log.get("ast", 0) or 0)
                        enriched_log = {**log, "pra": pra}
                        enriched_logs.append(enriched_log)
                    
                    enriched_logs_for_hit_rate = enriched_logs[-last_n:] if last_n else enriched_logs
                    
                    fair_line_pra = PropBetEngine.determine_line_value(enriched_logs, "pra")
                    hit_rate_pra = StatsCalculator.calculate_hit_rate(enriched_logs_for_hit_rate, fair_line_pra, "pra")
                    
                    if hit_rate_pra >= min_hit_rate:
                        evaluation_pra = PropBetEngine.evaluate_prop(enriched_logs, "pra", fair_line_pra)
                        sample_size_pra = len(enriched_logs_for_hit_rate)
                        
                        suggestion_pra = {
                            "type": "PRA",
                            "playerId": player_id,
                            "playerName": player_name,
                            "marketLine": fair_line_pra,
                            "fairLine": fair_line_pra,
                            "confidence": evaluation_pra.get("confidence", 0),
                            "suggestion": evaluation_pra.get("suggestion", "over"),
                            "hitRate": round(hit_rate_pra * 100, 1),
                            "sampleSize": sample_size_pra,
                            "rationale": evaluation_pra.get("rationale", {}).get("summary", ""),
                            "stats": evaluation_pra.get("stats", {}),
                            "gameDate": target_date,  # Add game date for today's games
                        }
                        all_props.append(suggestion_pra)
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

