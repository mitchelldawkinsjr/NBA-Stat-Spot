from __future__ import annotations
from typing import List, Dict
from .stats_calculator import StatsCalculator

class PropBetEngine:
    @staticmethod
    def determine_line_value(player_stats: List[Dict], stat_type: str) -> float:
        avg = StatsCalculator.calculate_rolling_average(player_stats, stat_type, n_games=10)
        return round(avg * 2) / 2.0

    @staticmethod
    def evaluate_prop(player_stats: List[Dict], stat_type: str, line_value: float) -> Dict:
        hit_rate = StatsCalculator.calculate_hit_rate(player_stats, line_value, stat_type)
        recent = StatsCalculator.calculate_recent_form(player_stats, stat_type)
        confidence = 100.0 * (0.4 * hit_rate + 0.3 * (1.0 if recent["trend"] == "up" else 0.5 if recent["trend"] == "flat" else 0.0))
        suggestion = "over" if hit_rate >= 0.5 else "under"
        return {
            "type": stat_type.upper(),
            "line": line_value,
            "suggestion": suggestion,
            "confidence": round(confidence, 1),
            "stats": {"hit_rate": hit_rate, "recent": recent},
            # Provide a human-readable rationale summary for display
            "rationale": {
                "summary": f"{recent['trend'].capitalize()} form; {hit_rate:.0%} hit over {line_value} in season sample"
            },
        }
