"""
Feature Engineering Service - Extracts and normalizes features for ML models
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import date
import statistics
from ..services.nba_api_service import NBADataService
from ..services.stats_calculator import StatsCalculator
from ..services.context_collector import ContextCollector
from ..services.market_data_service import MarketDataService
# PropBetEngine imported lazily to avoid circular import


class FeatureEngineer:
    """Extracts and normalizes features from player stats, context, and market data"""
    
    @staticmethod
    def extract_player_stat_features(
        player_id: int,
        prop_type: str,
        season: Optional[str] = None,
        last_n: int = 10
    ) -> Dict[str, Any]:
        """
        Extract statistical features from player's game logs.
        
        Args:
            player_id: Player ID
            prop_type: Prop type (PTS, REB, AST, 3PM, PRA)
            season: Season string
            last_n: Number of recent games to analyze
            
        Returns:
            Dictionary with statistical features
        """
        try:
            logs = NBADataService.fetch_player_game_log(player_id, season)
            if not logs:
                return {}
            
            # Limit to last N games
            recent_logs = logs[-last_n:] if len(logs) > last_n else logs
            
            # Map prop type to stat key
            stat_map = {
                "PTS": "pts",
                "REB": "reb",
                "AST": "ast",
                "3PM": "tpm",
                "PRA": "pra"  # Would need to calculate
            }
            stat_key = stat_map.get(prop_type, "pts")
            
            # Extract values
            if stat_key == "pra":
                # Calculate PRA (Points + Rebounds + Assists)
                values = [
                    float(log.get("pts", 0) or 0) + 
                    float(log.get("reb", 0) or 0) + 
                    float(log.get("ast", 0) or 0)
                    for log in recent_logs
                ]
            else:
                values = [float(log.get(stat_key, 0) or 0) for log in recent_logs]
            
            if not values:
                return {}
            
            # Calculate statistics
            rolling_avg_10 = StatsCalculator.calculate_rolling_average(logs, stat_key, 10)
            rolling_avg_5 = StatsCalculator.calculate_rolling_average(logs, stat_key, 5)
            season_avg = sum(values) / len(values) if values else 0.0
            
            # Calculate variance
            variance = statistics.variance(values) if len(values) > 1 else 0.0
            
            # Calculate trend
            recent_form = StatsCalculator.calculate_recent_form(logs, stat_key, 5)
            trend = recent_form.get("trend", "flat")
            
            # Calculate momentum (rate of change over last 5 games)
            momentum = 0.0
            if len(values) >= 5:
                first_half = sum(values[:len(values)//2]) / (len(values)//2)
                second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
                momentum = second_half - first_half
            
            return {
                "rolling_avg_10": rolling_avg_10,
                "rolling_avg_5": rolling_avg_5,
                "season_avg": season_avg,
                "variance": variance,
                "trend": trend,
                "momentum": momentum
            }
        except Exception:
            return {}
    
    @staticmethod
    def extract_context_features(
        player_id: int,
        game_date: date,
        opponent_team_id: Optional[int] = None,
        is_home_game: bool = True,
        season: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract context features from player context data.
        
        Args:
            player_id: Player ID
            game_date: Date of the game
            opponent_team_id: Opponent team ID
            is_home_game: Whether it's a home game
            season: Season string
            
        Returns:
            Dictionary with context features
        """
        try:
            context = ContextCollector.collect_player_context(
                player_id, game_date, opponent_team_id, is_home_game, season
            )
            
            # Encode injury status
            injury_status_encoded = 1.0  # Default: healthy
            if context.injury_status:
                status_lower = context.injury_status.lower()
                if status_lower == "probable":
                    injury_status_encoded = 0.9
                elif status_lower == "questionable":
                    injury_status_encoded = 0.5
                elif status_lower == "doubtful":
                    injury_status_encoded = 0.2
                elif status_lower == "out":
                    injury_status_encoded = 0.0
            
            # Calculate days since injury
            days_since_injury = None
            if context.injury_date:
                days_since_injury = (game_date - context.injury_date).days
            
            return {
                "rest_days": context.rest_days,
                "is_injured": context.is_injured,
                "injury_status_encoded": injury_status_encoded,
                "days_since_injury": days_since_injury if days_since_injury is not None else 0,
                "is_home_game": context.is_home_game,
                "opponent_def_rank_pts": context.opponent_def_rank_pts,
                "opponent_def_rank_reb": context.opponent_def_rank_reb,
                "opponent_def_rank_ast": context.opponent_def_rank_ast,
                "h2h_avg_pts": context.h2h_avg_pts,
                "h2h_avg_reb": context.h2h_avg_reb,
                "h2h_avg_ast": context.h2h_avg_ast,
                "h2h_games_played": context.h2h_games_played,
                "opponent_back_to_back": False,  # Would need to extract from matchup_info
                "team_win_rate": context.team_win_rate,
                "opponent_win_rate": context.opponent_win_rate,
                "team_conference_rank": context.team_conference_rank if context.team_conference_rank else 15,
                "opponent_conference_rank": context.opponent_conference_rank if context.opponent_conference_rank else 15,
                "team_recent_form": context.team_recent_form if context.team_recent_form is not None else 0.5,
                "opponent_recent_form": None,  # Would need opponent's recent form
                "playoff_race_pressure": context.playoff_race_pressure if context.playoff_race_pressure is not None else 0.0,
                "has_recent_news": context.news_sentiment is not None and context.news_sentiment != 0.0,
                "news_sentiment": context.news_sentiment if context.news_sentiment is not None else 0.0,
                "has_recent_transaction": context.has_recent_transaction if context.has_recent_transaction else False,
                "days_since_transaction": 0  # Would need to track transaction date
            }
        except Exception:
            return {}
    
    @staticmethod
    def extract_live_game_features(game_id: str, player_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Extract live game features from ESPN.
        
        Args:
            game_id: ESPN game ID
            player_id: Optional player ID for player-specific features
            
        Returns:
            Dictionary with live game features
        """
        try:
            from .live_game_context_service import get_live_game_context_service
            
            live_service = get_live_game_context_service()
            
            if player_id:
                live_context = live_service.extract_live_context(game_id, player_id)
                return {
                    "live_pace": live_context.get("live_pace", 0.0),
                    "live_shooting_efficiency": 0.45,  # Would extract from gamecast
                    "foul_trouble_score": live_context.get("foul_trouble_score", 0.0),
                    "projected_minutes_remaining": live_context.get("projected_minutes_remaining", 0.0),
                    "game_flow_score": live_context.get("game_flow_score", 0.5)
                }
            else:
                game_features = live_service.get_live_game_features(game_id)
                return {
                    "live_pace": game_features.get("live_pace", 0.0),
                    "live_shooting_efficiency": game_features.get("shooting_efficiency", 0.45),
                    "foul_trouble_score": 0.0,
                    "projected_minutes_remaining": 0.0,
                    "game_flow_score": 0.5
                }
        except Exception:
            return {
                "live_pace": 0.0,
                "live_shooting_efficiency": 0.45,
                "foul_trouble_score": 0.0,
                "projected_minutes_remaining": 0.0,
                "game_flow_score": 0.5
            }
    
    @staticmethod
    def extract_market_features(
        player_id: int,
        prop_type: str,
        game_date: date,
        market_line: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Extract market features from market context data.
        
        Args:
            player_id: Player ID
            prop_type: Prop type
            game_date: Date of the game
            market_line: Market line (optional)
            
        Returns:
            Dictionary with market features
        """
        try:
            market_context = MarketDataService.get_or_create_market_context(
                player_id, prop_type, game_date, market_line
            )
            
            return {
                "market_line": market_context.market_line,
                "line_movement": market_context.line_movement,
                "line_value": market_context.line_value,
                "public_bet_pct": market_context.public_bet_percentage_over,
                "fair_line": market_context.fair_line
            }
        except Exception:
            return {}
    
    @staticmethod
    def extract_historical_performance_features(
        player_id: int,
        prop_type: str,
        line_value: float,
        season: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract historical performance features at a specific line.
        
        Args:
            player_id: Player ID
            prop_type: Prop type
            line_value: Line value to check
            season: Season string
            
        Returns:
            Dictionary with historical performance features
        """
        try:
            logs = NBADataService.fetch_player_game_log(player_id, season)
            if not logs:
                return {}
            
            # Map prop type to stat key
            stat_map = {
                "PTS": "pts",
                "REB": "reb",
                "AST": "ast",
                "3PM": "tpm",
                "PRA": "pra"
            }
            stat_key = stat_map.get(prop_type, "pts")
            
            # Calculate hit rates
            hit_rate_over = StatsCalculator.calculate_hit_rate(logs, line_value, stat_key, "over")
            hit_rate_under = StatsCalculator.calculate_hit_rate(logs, line_value, stat_key, "under")
            
            # Calculate hit rate at this specific line (using a small range)
            tolerance = 0.5
            hit_rate_at_line = StatsCalculator.calculate_hit_rate(
                logs, line_value, stat_key, "over"
            )
            
            return {
                "hit_rate_over": hit_rate_over,
                "hit_rate_under": hit_rate_under,
                "hit_rate_at_line": hit_rate_at_line
            }
        except Exception:
            return {}
    
    @staticmethod
    def build_feature_set(
        player_id: int,
        prop_type: str,
        game_date: date,
        market_line: Optional[float] = None,
        opponent_team_id: Optional[int] = None,
        is_home_game: bool = True,
        season: Optional[str] = None,
        last_n: int = 10
    ) -> Dict[str, Any]:
        """
        Build complete feature set for ML model.
        
        Args:
            player_id: Player ID
            prop_type: Prop type
            game_date: Date of the game
            market_line: Market line (optional)
            opponent_team_id: Opponent team ID
            is_home_game: Whether it's a home game
            season: Season string
            last_n: Number of recent games to analyze
            
        Returns:
            Complete feature set dictionary
        """
        # Extract all feature types
        stat_features = FeatureEngineer.extract_player_stat_features(
            player_id, prop_type, season, last_n
        )
        
        context_features = FeatureEngineer.extract_context_features(
            player_id, game_date, opponent_team_id, is_home_game, season
        )
        
        # Use market_line or calculate fair line
        stat_map = {
            "PTS": "pts",
            "REB": "reb",
            "AST": "ast",
            "3PM": "tpm",
            "PRA": "pra"
        }
        if market_line is None:
            # Lazy import to avoid circular dependency
            from ..services.prop_engine import PropBetEngine
            logs = NBADataService.fetch_player_game_log(player_id, season) or []
            stat_key = stat_map.get(prop_type, "pts")
            market_line = PropBetEngine.determine_line_value(logs, stat_key)
        
        market_features = FeatureEngineer.extract_market_features(
            player_id, prop_type, game_date, market_line
        )
        
        historical_features = FeatureEngineer.extract_historical_performance_features(
            player_id, prop_type, market_line or 0.0, season
        )
        
        # Combine all features
        feature_set = {
            **stat_features,
            **context_features,
            **market_features,
            **historical_features,
            "player_id": player_id,
            "prop_type": prop_type,
            "game_date": game_date.isoformat() if isinstance(game_date, date) else game_date
        }
        
        return feature_set
    
    @staticmethod
    def normalize_features(features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize feature values for ML model input.
        
        Args:
            features: Raw feature dictionary
            
        Returns:
            Normalized feature dictionary
        """
        normalized = {}
        
        # Normalize numeric features to 0-1 range where appropriate
        for key, value in features.items():
            if isinstance(value, (int, float)) and value is not None:
                # Skip normalization for certain features
                if key in ["player_id", "game_date"]:
                    normalized[key] = value
                elif key in ["rest_days"]:
                    # Normalize rest days (0-7 days)
                    normalized[key] = min(1.0, max(0.0, value / 7.0))
                elif key in ["rolling_avg_10", "rolling_avg_5", "season_avg", "market_line", "fair_line"]:
                    # Keep as-is (will be normalized by model if needed)
                    normalized[key] = value
                elif key in ["variance", "momentum"]:
                    # Keep as-is
                    normalized[key] = value
                elif key in ["hit_rate_over", "hit_rate_under", "hit_rate_at_line"]:
                    # Already 0-1
                    normalized[key] = value
                elif key in ["team_win_rate", "opponent_win_rate", "public_bet_pct"]:
                    # Already 0-100 or 0-1
                    normalized[key] = value / 100.0 if value > 1.0 else value
                else:
                    normalized[key] = value
            elif isinstance(value, bool):
                normalized[key] = 1.0 if value else 0.0
            elif isinstance(value, str):
                # Encode string features
                if key == "trend":
                    trend_map = {"up": 1.0, "flat": 0.5, "down": 0.0}
                    normalized[key] = trend_map.get(value.lower(), 0.5)
                else:
                    normalized[key] = value
            else:
                normalized[key] = value
        
        return normalized

