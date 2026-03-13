from __future__ import annotations
import os
from typing import List, Dict, Optional
from datetime import date
from .stats_calculator import StatsCalculator
from .rationale_generator import get_rationale_generator
from .nba_api_service import NBADataService


def _ml_enabled() -> bool:
    """True when ML_ENABLED env is set to true/1 (default false to avoid loading unused ML stack)."""
    return os.getenv("ML_ENABLED", "false").strip().lower() in ("true", "1")


class PropBetEngine:
    @staticmethod
    def determine_line_value(player_stats: List[Dict], stat_type: str) -> float:
        avg = StatsCalculator.calculate_rolling_average(player_stats, stat_type, n_games=10)
        return round(avg * 2) / 2.0

    @staticmethod
    def find_best_line(
        player_stats: List[Dict],
        stat_type: str,
        direction: str = "over",
        n_recent: int = 10,
    ) -> tuple[float, float]:
        """
        Search half-point lines around the rolling average and return the
        (line_value, hit_rate) pair with the best hit rate for *direction*.
        """
        base = PropBetEngine.determine_line_value(player_stats, stat_type)
        recent = player_stats[-n_recent:] if n_recent else player_stats
        best_line = base
        best_hr = 0.0
        for offset in [-3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
            candidate = round((base + offset) * 2) / 2.0
            if candidate < 0:
                continue
            hr = StatsCalculator.calculate_hit_rate(recent, candidate, stat_type, direction)
            if hr > best_hr:
                best_hr = hr
                best_line = candidate
        return best_line, best_hr

    @staticmethod
    def multi_factor_confidence(
        player_stats: List[Dict],
        stat_type: str,
        line_value: float,
        direction: str = "over",
        is_home: Optional[bool] = None,
        opp_def_score: float = 0.5,
    ) -> float:
        """
        Multi-factor confidence score (0‒100).

        Weights:
          25 %  hit rate (last 10 games)
          20 %  consistency (low variance)
          20 %  weighted trend (exponential-decay recent form)
          15 %  sample-size / volume
          10 %  home/away split hit rate
          10 %  opponent defensive context
        """
        recent = player_stats[-10:]
        hit_rate = StatsCalculator.calculate_hit_rate(recent, line_value, stat_type, direction)
        consistency = StatsCalculator.calculate_consistency(player_stats, stat_type, n_games=10)
        trend = StatsCalculator.calculate_weighted_trend_score(player_stats, stat_type, direction, n_games=10)
        volume = StatsCalculator.calculate_volume_score(player_stats, min_games=5, ideal_games=20)
        ha_hit = StatsCalculator.calculate_home_away_split(player_stats, stat_type, line_value, direction, is_home)

        raw = (
            0.25 * hit_rate
            + 0.20 * consistency
            + 0.20 * trend
            + 0.15 * volume
            + 0.10 * ha_hit
            + 0.10 * opp_def_score
        )
        return round(min(99, max(0, raw * 100)), 1)

    @staticmethod
    def build_rationale_text(
        hit_rate: float,
        direction: str,
        line_value: float,
        trend: str,
        consistency: float,
        streak: int,
        sample_size: int,
    ) -> str:
        parts: list[str] = []
        parts.append(f"{trend.capitalize()} form")
        parts.append(f"{hit_rate:.0%} hit {direction} {line_value} (last {sample_size})")
        if streak >= 3:
            parts.append(f"{streak}-game streak")
        if consistency >= 0.7:
            parts.append("very consistent")
        elif consistency >= 0.5:
            parts.append("consistent")
        return "; ".join(parts)

    @staticmethod
    def evaluate_prop(
        player_stats: List[Dict],
        stat_type: str,
        line_value: float,
        direction: str = "over",
        is_home: Optional[bool] = None,
        opp_def_score: float = 0.5,
    ) -> Dict:
        recent = player_stats[-10:]
        hit_rate = StatsCalculator.calculate_hit_rate(recent, line_value, stat_type, direction)
        hit_rate_over = StatsCalculator.calculate_hit_rate(recent, line_value, stat_type, "over")
        hit_rate_under = StatsCalculator.calculate_hit_rate(recent, line_value, stat_type, "under")
        form = StatsCalculator.calculate_recent_form(player_stats, stat_type)
        consistency = StatsCalculator.calculate_consistency(player_stats, stat_type, n_games=10)
        streak = StatsCalculator.calculate_streak(player_stats, stat_type, line_value, direction)

        confidence = PropBetEngine.multi_factor_confidence(
            player_stats, stat_type, line_value, direction, is_home, opp_def_score
        )
        suggestion = "over" if hit_rate_over >= 0.5 else "under"

        rationale_text = PropBetEngine.build_rationale_text(
            hit_rate, direction, line_value, form["trend"], consistency, streak, len(recent)
        )

        return {
            "type": stat_type.upper(),
            "line": line_value,
            "suggestion": suggestion,
            "confidence": confidence,
            "stats": {
                "hit_rate": hit_rate,
                "hit_rate_over": hit_rate_over,
                "hit_rate_under": hit_rate_under,
                "recent": form,
                "consistency": round(consistency, 2),
                "streak": streak,
            },
            "rationale": {"summary": rationale_text},
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
        season: Optional[str] = None,
    ) -> Dict:
        rule_based_result = PropBetEngine.evaluate_prop(player_stats, stat_type, line_value, direction)
        ml_confidence = None
        ml_predicted_line = None
        ml_available = False

        if player_id and game_date and _ml_enabled():
            try:
                from .feature_engineer import FeatureEngineer
                from .ml_models.model_server import get_model_server
                model_server = get_model_server()
                feature_set = FeatureEngineer.build_feature_set(
                    player_id=player_id,
                    prop_type=stat_type.upper(),
                    game_date=game_date,
                    market_line=line_value,
                    opponent_team_id=opponent_team_id,
                    is_home_game=is_home_game,
                    season=season,
                )
                normalized_features = FeatureEngineer.normalize_features(feature_set)
                if model_server.is_available():
                    ml_confidence = model_server.predict_confidence(normalized_features)
                    ml_predicted_line = model_server.predict_line(normalized_features)
                    ml_available = ml_confidence is not None or ml_predicted_line is not None
                    if ml_available:
                        import structlog
                        structlog.get_logger().debug("ML model used for prop", player_id=player_id, stat_type=stat_type, ml_confidence=ml_confidence)
            except Exception:
                ml_available = False

        result = rule_based_result.copy()
        if ml_available:
            result["ml_confidence"] = ml_confidence
            result["ml_predicted_line"] = ml_predicted_line
            result["ml_available"] = True
            if ml_confidence is not None:
                blended = 0.7 * ml_confidence + 0.3 * result.get("confidence", 0)
                result["confidence"] = round(blended, 1)
                result["confidence_source"] = "ml_blended"
            else:
                result["confidence_source"] = "rule_based"
        else:
            result["ml_available"] = False
            result["confidence_source"] = "rule_based"

        if player_id:
            try:
                rationale_generator = get_rationale_generator()
                player_name = f"Player {player_id}"
                try:
                    all_players = NBADataService.fetch_all_players_including_rookies()
                    player = next((p for p in all_players if p.get("id") == player_id), None)
                    if player:
                        player_name = player.get("full_name", player_name)
                except Exception:
                    pass

                rationale_context: Dict = {}
                if opponent_team_id:
                    rationale_context["opponent_team_id"] = opponent_team_id
                rationale_context["is_home_game"] = is_home_game

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

                espn_context: Dict = {}
                if player_context:
                    espn_context["injury_status"] = player_context.injury_status
                    espn_context["conference_rank"] = player_context.team_conference_rank
                    espn_context["news_sentiment"] = player_context.news_sentiment

                llm_rationale = rationale_generator.generate_rationale(
                    player_name=player_name,
                    prop_type=stat_type.upper(),
                    line_value=line_value,
                    direction=direction,
                    confidence=result.get("confidence", 0),
                    ml_confidence=ml_confidence,
                    stats=result.get("stats", {}),
                    context=rationale_context,
                    espn_context=espn_context if espn_context else None,
                )
                result["rationale"]["llm"] = llm_rationale
                llm_used = rationale_generator.is_available()
                result["rationale"]["source"] = "llm" if llm_used else "rule_based"
                if llm_used:
                    import structlog
                    structlog.get_logger().debug("LLM rationale generated", player_id=player_id, stat_type=stat_type)
            except Exception:
                result["rationale"]["source"] = "rule_based"

        return result
