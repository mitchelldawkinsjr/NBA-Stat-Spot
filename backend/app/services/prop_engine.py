from __future__ import annotations
from typing import List, Dict, Optional
from datetime import date
from .stats_calculator import StatsCalculator
from .feature_engineer import FeatureEngineer
from .ml_models.model_server import get_model_server
from .rationale_generator import get_rationale_generator
from .nba_api_service import NBADataService

class PropBetEngine:
    @staticmethod
    def determine_line_value(player_stats: List[Dict], stat_type: str) -> float:
        avg = StatsCalculator.calculate_rolling_average(player_stats, stat_type, n_games=10)
        return round(avg * 2) / 2.0

    @staticmethod
    def evaluate_prop(player_stats: List[Dict], stat_type: str, line_value: float, direction: str = "over") -> Dict:
        """
        Evaluate a prop bet.
        
        Args:
            player_stats: List of game stat dictionaries
            stat_type: The stat type (pts, reb, ast, tpm, pra)
            line_value: The line value to evaluate
            direction: "over" or "under" (default: "over")
        
        Returns:
            Dictionary with evaluation results including hit_rate for the specified direction
        """
        # Calculate hit rate for the specified direction
        hit_rate = StatsCalculator.calculate_hit_rate(player_stats, line_value, stat_type, direction)
        # For suggestion, use "over" hit rate to determine default suggestion
        hit_rate_over = StatsCalculator.calculate_hit_rate(player_stats, line_value, stat_type, "over")
        hit_rate_under = StatsCalculator.calculate_hit_rate(player_stats, line_value, stat_type, "under")
        recent = StatsCalculator.calculate_recent_form(player_stats, stat_type)
        
        # Calculate confidence based on direction
        # For "over": trend up is good, trend down is bad
        # For "under": trend down is good, trend up is bad
        if direction.lower() == "under":
            trend_score = 1.0 if recent["trend"] == "down" else (0.5 if recent["trend"] == "flat" else 0.0)
        else:  # "over"
            trend_score = 1.0 if recent["trend"] == "up" else (0.5 if recent["trend"] == "flat" else 0.0)
        
        confidence = 100.0 * (0.4 * hit_rate + 0.3 * trend_score)
        suggestion = "over" if hit_rate_over >= 0.5 else "under"
        return {
            "type": stat_type.upper(),
            "line": line_value,
            "suggestion": suggestion,
            "confidence": round(confidence, 1),
            "stats": {"hit_rate": hit_rate, "hit_rate_over": hit_rate_over, "hit_rate_under": hit_rate_under, "recent": recent},
            # Provide a human-readable rationale summary for display
            "rationale": {
                "summary": f"{recent['trend'].capitalize()} form; {hit_rate:.0%} hit {direction} {line_value} in season sample"
            },
        }
    
    @staticmethod
    def evaluate_prop_with_ml(
        player_stats: List[Dict],
        stat_type: str,
        line_value: float,
        direction: str = "over",
        player_id: Optional[int] = None,
        game_date: Optional[date] = None,
        opponent_team_id: Optional[int] = None,
        is_home_game: bool = True,
        season: Optional[str] = None
    ) -> Dict:
        """
        Evaluate a prop bet using ML models with fallback to rule-based logic.
        
        Args:
            player_stats: List of game stat dictionaries
            stat_type: The stat type (pts, reb, ast, tpm, pra)
            line_value: The line value to evaluate
            direction: "over" or "under" (default: "over")
            player_id: Player ID (for ML features)
            game_date: Game date (for ML features)
            opponent_team_id: Opponent team ID (for ML features)
            is_home_game: Whether it's a home game (for ML features)
            season: Season string (for ML features)
            
        Returns:
            Dictionary with evaluation results including ML confidence if available
        """
        # Start with rule-based evaluation
        rule_based_result = PropBetEngine.evaluate_prop(player_stats, stat_type, line_value, direction)
        
        # Try to get ML predictions if we have the required context
        ml_confidence = None
        ml_predicted_line = None
        ml_available = False
        
        if player_id and game_date:
            try:
                model_server = get_model_server()
                
                # Build feature set
                feature_set = FeatureEngineer.build_feature_set(
                    player_id=player_id,
                    prop_type=stat_type.upper(),
                    game_date=game_date,
                    market_line=line_value,
                    opponent_team_id=opponent_team_id,
                    is_home_game=is_home_game,
                    season=season
                )
                
                # Normalize features
                normalized_features = FeatureEngineer.normalize_features(feature_set)
                
                # Get ML predictions
                if model_server.is_available():
                    ml_confidence = model_server.predict_confidence(normalized_features)
                    ml_predicted_line = model_server.predict_line(normalized_features)
                    ml_available = ml_confidence is not None or ml_predicted_line is not None
            except Exception as e:
                # ML prediction failed, fall back to rule-based
                import structlog
                logger = structlog.get_logger()
                logger.warning("ML prediction failed, using rule-based", error=str(e))
                ml_available = False
        
        # Combine results
        result = rule_based_result.copy()
        
        # Add ML predictions if available
        if ml_available:
            result["ml_confidence"] = ml_confidence
            result["ml_predicted_line"] = ml_predicted_line
            result["ml_available"] = True
            
            # Optionally blend ML and rule-based confidence
            if ml_confidence is not None:
                # Weighted average: 70% ML, 30% rule-based
                rule_confidence = result.get("confidence", 0)
                blended_confidence = 0.7 * ml_confidence + 0.3 * rule_confidence
                result["confidence"] = round(blended_confidence, 1)
                result["confidence_source"] = "ml_blended"
            else:
                result["confidence_source"] = "rule_based"
        else:
            result["ml_available"] = False
            result["confidence_source"] = "rule_based"
        
        # Generate LLM rationale if player_id is available
        if player_id:
            try:
                rationale_generator = get_rationale_generator()
                
                # Get player name from NBA API
                player_name = f"Player {player_id}"  # Default fallback
                try:
                    all_players = NBADataService.fetch_all_players_including_rookies()
                    player = next((p for p in all_players if p.get("id") == player_id), None)
                    if player:
                        player_name = player.get("full_name", player_name)
                except Exception:
                    pass
                
                # Build context for rationale
                rationale_context = {}
                if opponent_team_id:
                    rationale_context["opponent_team_id"] = opponent_team_id
                rationale_context["is_home_game"] = is_home_game
                
                # Get context features if available
                player_context = None
                try:
                    from .context_collector import ContextCollector
                    player_context = ContextCollector.collect_player_context(
                        player_id, game_date, opponent_team_id, is_home_game, season
                    )
                    rationale_context["rest_days"] = player_context.rest_days
                    rationale_context["opponent_def_rank"] = player_context.opponent_def_rank_pts
                    rationale_context["h2h_avg"] = player_context.h2h_avg_pts
                except Exception:
                    pass
                
                # Build ESPN context for rationale
                espn_context = {}
                if player_context:
                    espn_context["injury_status"] = player_context.injury_status
                    espn_context["conference_rank"] = player_context.team_conference_rank
                    espn_context["news_sentiment"] = player_context.news_sentiment
                
                # Generate rationale
                llm_rationale = rationale_generator.generate_rationale(
                    player_name=player_name,
                    prop_type=stat_type.upper(),
                    line_value=line_value,
                    direction=direction,
                    confidence=result.get("confidence", 0),
                    ml_confidence=ml_confidence,
                    stats=result.get("stats", {}),
                    context=rationale_context,
                    espn_context=espn_context if espn_context else None
                )
                
                result["rationale"]["llm"] = llm_rationale
                result["rationale"]["source"] = "llm" if rationale_generator.is_available() else "rule_based"
            except Exception as e:
                # LLM rationale generation failed, keep rule-based
                import structlog
                logger = structlog.get_logger()
                logger.warning("LLM rationale generation failed", error=str(e))
                result["rationale"]["source"] = "rule_based"
        
        return result
