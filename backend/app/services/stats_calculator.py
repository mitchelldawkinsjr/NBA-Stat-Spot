from __future__ import annotations
from typing import List, Dict

class StatsCalculator:
    @staticmethod
    def calculate_rolling_average(player_stats: List[Dict], stat_type: str, n_games: int = 10) -> float:
        vals = [float(g.get(stat_type, 0) or 0) for g in player_stats][-n_games:]
        return sum(vals) / len(vals) if vals else 0.0

    @staticmethod
    def calculate_hit_rate(player_stats: List[Dict], line_value: float, stat_type: str) -> float:
        vals = [float(g.get(stat_type, 0) or 0) for g in player_stats]
        if not vals:
            return 0.0
        hits = sum(1 for v in vals if v > line_value)
        return hits / len(vals)

    @staticmethod
    def calculate_recent_form(player_stats: List[Dict], stat_type: str, n_games: int = 5) -> Dict:
        vals = [float(g.get(stat_type, 0) or 0) for g in player_stats][-n_games:]
        if not vals:
            return {"avg": 0.0, "trend": "flat"}
        avg = sum(vals) / len(vals)
        trend = "up" if len(vals) >= 2 and vals[-1] > vals[0] else ("down" if len(vals) >= 2 and vals[-1] < vals[0] else "flat")
        return {"avg": avg, "trend": trend}
