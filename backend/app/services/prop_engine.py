from __future__ import annotations
from typing import List, Dict
from .stats_calculator import StatsCalculator

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
        recent = StatsCalculator.calculate_recent_form(player_stats, stat_type)
        confidence = 100.0 * (0.4 * hit_rate + 0.3 * (1.0 if recent["trend"] == "up" else 0.5 if recent["trend"] == "flat" else 0.0))
        suggestion = "over" if hit_rate_over >= 0.5 else "under"
        return {
            "type": stat_type.upper(),
            "line": line_value,
            "suggestion": suggestion,
            "confidence": round(confidence, 1),
            "stats": {"hit_rate": hit_rate, "hit_rate_over": hit_rate_over, "recent": recent},
            # Provide a human-readable rationale summary for display
            "rationale": {
                "summary": f"{recent['trend'].capitalize()} form; {hit_rate:.0%} hit {direction} {line_value} in season sample"
            },
        }
