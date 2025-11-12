"""
Prop Scanner Service - Analyzes players playing today and identifies best prop bets
Focuses on players doing well in specific stats and playing that day
"""
from __future__ import annotations
from typing import List, Dict, Optional, Any
from datetime import datetime
from .nba_api_service import NBADataService
from .prop_engine import PropBetEngine
from .stats_calculator import StatsCalculator


class PropScannerService:
    """Scans players playing today and identifies high-confidence prop bets"""
    
    @staticmethod
    def scan_best_bets_for_today(season: str = "2025-26", min_confidence: float = 65.0, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Main scanning function:
        1. Gets today's games
        2. Finds players on those teams
        3. Analyzes their recent form (last 10 games)
        4. Identifies stats they're doing well in
        5. Suggests props around those stats with high confidence
        """
        try:
            # Get today's games
            games = NBADataService.fetch_todays_games()
            if not games:
                return []
            
            # Extract team abbreviations
            team_abbrs = set()
            for g in games:
                if g.get("home"):
                    team_abbrs.add(g.get("home"))
                if g.get("away"):
                    team_abbrs.add(g.get("away"))
            
            # Map abbreviations to team IDs
            teams = NBADataService.fetch_all_teams() or []
            abbr_to_id = {t.get("abbreviation"): t.get("id") for t in teams}
            team_ids_today = {abbr_to_id.get(ab) for ab in team_abbrs if ab in abbr_to_id}
            
            # Get all active players (including rookies)
            all_players = NBADataService.fetch_all_players_including_rookies() or []
            
            # Use TeamPlayerService to normalize team IDs
            from .team_player_service import TeamPlayerService
            team_ids_today_int = {TeamPlayerService.normalize_team_id(tid) for tid in team_ids_today}
            team_ids_today_int.discard(None)
            
            # Filter to players on today's teams
            todays_players = []
            for p in all_players:
                player_team_id = TeamPlayerService.normalize_team_id(p.get("team_id"))
                if player_team_id is not None and player_team_id in team_ids_today_int:
                    todays_players.append(p)
            
            if not todays_players:
                return []
            
            # Analyze each player
            all_suggestions: List[Dict[str, Any]] = []
            
            for player in todays_players[:80]:  # Limit to avoid too many API calls
                player_id = player.get("id")
                player_name = player.get("full_name", "Unknown")
                
                if not player_id:
                    continue
                
                try:
                    # Fetch recent game logs - ONLY use current season
                    # If player doesn't have stats from current season, exclude them
                    logs = NBADataService.fetch_player_game_log(player_id, season)
                    
                    # Need at least 5 games to make meaningful suggestions
                    if not logs or len(logs) < 5:
                        continue
                    
                    # Verify logs are from the requested season
                    if season:
                        try:
                            season_year = int(season.split("-")[0])
                            # Check if any logs have game dates from the current season
                            has_current_season_logs = False
                            for log in logs:
                                game_date = log.get("game_date", "")
                                if game_date:
                                    try:
                                        from datetime import datetime
                                        date_obj = datetime.strptime(game_date.split("T")[0] if "T" in game_date else game_date, "%Y-%m-%d")
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
                    minutes_list = [
                        float(game.get("minutes", 0) or 0) 
                        for game in logs 
                        if game.get("minutes") and float(game.get("minutes", 0) or 0) > 0
                    ]
                    if minutes_list:
                        avg_minutes = sum(minutes_list) / len(minutes_list)
                        if avg_minutes < 22.0:
                            # Player doesn't meet minimum minutes threshold
                            continue
                    elif len(logs) > 0:
                        # If we have logs but no valid minutes data, skip
                        continue
                    
                    # Analyze each stat category
                    stat_types = ["pts", "reb", "ast", "tpm"]
                    
                    for stat_type in stat_types:
                        # Calculate recent form (last 10 games)
                        recent_avg = StatsCalculator.calculate_rolling_average(logs, stat_type, n_games=10)
                        recent_form = StatsCalculator.calculate_recent_form(logs, stat_type, n_games=5)
                        season_avg = StatsCalculator.calculate_rolling_average(logs, stat_type, n_games=len(logs))
                        
                        # Skip if player isn't producing in this stat
                        if recent_avg < 1.0:  # Minimum threshold
                            continue
                        
                        # Determine fair line based on recent performance
                        fair_line = PropBetEngine.determine_line_value(logs[-10:], stat_type)
                        
                        # Use recent average as market line if not provided
                        market_line = round(recent_avg * 2) / 2.0
                        
                        # Evaluate the prop
                        evaluation = PropBetEngine.evaluate_prop(logs, stat_type, market_line)
                        
                        confidence = evaluation.get("confidence", 0.0)
                        
                        # Only include high-confidence suggestions
                        if confidence < min_confidence:
                            continue
                        
                        # Calculate hit rate
                        hit_rate = StatsCalculator.calculate_hit_rate(logs, market_line, stat_type)
                        
                        # Determine if over or under is better
                        suggestion = "over" if hit_rate >= 0.5 else "under"
                        
                        # Calculate edge (difference between fair line and market line)
                        edge = fair_line - market_line
                        
                        # Build rationale
                        trend_indicator = "📈" if recent_form["trend"] == "up" else "📉" if recent_form["trend"] == "down" else "➡️"
                        rationale = [
                            f"{trend_indicator} {stat_type.upper()} trending {recent_form['trend']} in last 5 games (avg: {recent_form['avg']:.1f})",
                            f"Recent form: {recent_avg:.1f} avg over last 10 games vs season avg {season_avg:.1f}",
                            f"Hit rate: {hit_rate:.0%} over {market_line} in recent games",
                            f"Playing today - favorable matchup"
                        ]
                        
                        # Add to suggestions
                        all_suggestions.append({
                            "playerId": player_id,
                            "playerName": player_name,
                            "type": stat_type.upper(),
                            "marketLine": market_line,
                            "fairLine": fair_line,
                            "edge": round(edge, 1),
                            "confidence": round(confidence, 1),
                            "hitRate": round(hit_rate * 100, 1),
                            "suggestion": suggestion,
                            "recentAvg": round(recent_avg, 1),
                            "seasonAvg": round(season_avg, 1),
                            "trend": recent_form["trend"],
                            "rationale": rationale,
                            "gamesAnalyzed": len(logs),
                        })
                
                except Exception as e:
                    # Log error but continue with other players
                    import structlog
                    logger = structlog.get_logger()
                    logger.error("Error scanning player", player_name=player_name, player_id=player_id, error=str(e))
                    continue
            
            # Sort by confidence (highest first)
            all_suggestions.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            
            # Return top N
            return all_suggestions[:limit]
        
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error("Error in scan_best_bets_for_today", error=str(e))
            return []
    
    @staticmethod
    def scan_player_stats_trends(player_id: int, season: str = "2025-26") -> Dict[str, Any]:
        """Analyze a specific player's stat trends to identify hot streaks"""
        try:
            logs = NBADataService.fetch_player_game_log(player_id, season)
            
            if len(logs) < 5:
                return {"error": "Insufficient data"}
            
            trends = {}
            stat_types = ["pts", "reb", "ast", "tpm"]
            
            for stat_type in stat_types:
                recent_5 = StatsCalculator.calculate_rolling_average(logs, stat_type, n_games=5)
                recent_10 = StatsCalculator.calculate_rolling_average(logs, stat_type, n_games=10)
                season_avg = StatsCalculator.calculate_rolling_average(logs, stat_type, n_games=len(logs))
                form = StatsCalculator.calculate_recent_form(logs, stat_type, n_games=5)
                
                trends[stat_type] = {
                    "recent5": round(recent_5, 1),
                    "recent10": round(recent_10, 1),
                    "season": round(season_avg, 1),
                    "trend": form["trend"],
                    "improving": recent_5 > season_avg * 1.1,  # 10% above season avg
                }
            
            return {"playerId": player_id, "trends": trends, "gamesAnalyzed": len(logs)}
        
        except Exception as e:
            return {"error": str(e)}

