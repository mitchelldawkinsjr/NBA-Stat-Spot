from __future__ import annotations
from typing import List, Dict, Optional
import math


class StatsCalculator:
    @staticmethod
    def calculate_rolling_average(player_stats: List[Dict], stat_type: str, n_games: int = 10) -> float:
        vals = [float(g.get(stat_type, 0) or 0) for g in player_stats][-n_games:]
        return sum(vals) / len(vals) if vals else 0.0

    @staticmethod
    def calculate_hit_rate(player_stats: List[Dict], line_value: float, stat_type: str, direction: str = "over") -> float:
        vals = [float(g.get(stat_type, 0) or 0) for g in player_stats]
        if not vals:
            return 0.0
        if direction.lower() == "under":
            hits = sum(1 for v in vals if v < line_value)
        else:
            hits = sum(1 for v in vals if v > line_value)
        return hits / len(vals)

    @staticmethod
    def trend_period(
        player_stats: List[Dict],
        line_value: float,
        stat_type: str,
        direction: str,
        n_games: int,
    ) -> Dict:
        """
        Hit/miss per game for the last n_games (or fewer if log is short).
        Returns hit_rate_percentage, hits, total, results (oldest→newest in window).
        """
        if n_games <= 0:
            return {"hit_rate_percentage": 0, "hits": 0, "total": 0, "results": []}
        window = player_stats[-n_games:] if len(player_stats) >= n_games else player_stats
        direction_l = (direction or "over").lower()
        results: List[bool] = []
        for g in window:
            v = float(g.get(stat_type, 0) or 0)
            if direction_l == "under":
                results.append(v < line_value)
            else:
                results.append(v > line_value)
        hits = sum(1 for r in results if r)
        total = len(results)
        pct = round(100 * hits / total) if total else 0
        return {"hit_rate_percentage": pct, "hits": hits, "total": total, "results": results}

    @staticmethod
    def calculate_recent_form(player_stats: List[Dict], stat_type: str, n_games: int = 5) -> Dict:
        vals = [float(g.get(stat_type, 0) or 0) for g in player_stats][-n_games:]
        if not vals:
            return {"avg": 0.0, "trend": "flat", "weighted_avg": 0.0, "trend_slope": 0.0}
        avg = sum(vals) / len(vals)
        weighted_avg = StatsCalculator.calculate_weighted_average(vals)
        slope = StatsCalculator._linear_slope(vals)
        if slope > 0.5:
            trend = "up"
        elif slope < -0.5:
            trend = "down"
        else:
            trend = "flat"
        return {"avg": avg, "trend": trend, "weighted_avg": weighted_avg, "trend_slope": slope}

    # ── New analytics methods ─────────────────────────────────────

    @staticmethod
    def calculate_weighted_average(vals: List[float]) -> float:
        """Exponentially-weighted average: most recent game gets the most weight."""
        if not vals:
            return 0.0
        decay = 0.6
        weights = [decay ** i for i in range(len(vals))]
        weighted = sum(w * v for w, v in zip(weights, reversed(vals)))
        return weighted / sum(weights)

    @staticmethod
    def _linear_slope(vals: List[float]) -> float:
        """Simple linear regression slope over the values (oldest→newest)."""
        n = len(vals)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2.0
        y_mean = sum(vals) / n
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(vals))
        den = sum((i - x_mean) ** 2 for i in range(n))
        return num / den if den else 0.0

    @staticmethod
    def calculate_consistency(player_stats: List[Dict], stat_type: str, n_games: int = 10) -> float:
        """
        0‒1 score.  Lower coefficient-of-variation → higher consistency.
        1.0 = perfectly consistent, 0.0 = wildly variable.
        """
        vals = [float(g.get(stat_type, 0) or 0) for g in player_stats][-n_games:]
        if len(vals) < 3:
            return 0.0
        mean = sum(vals) / len(vals)
        if mean == 0:
            return 0.0
        variance = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = math.sqrt(variance)
        cv = std / mean
        return max(0.0, min(1.0, 1.0 - cv))

    @staticmethod
    def calculate_weighted_trend_score(
        player_stats: List[Dict], stat_type: str, direction: str = "over", n_games: int = 10
    ) -> float:
        """
        0‒1 score.  Compares weighted-recent average to full-season average.
        For *over*: higher recent → higher score.
        For *under*: lower recent → higher score.
        """
        vals_all = [float(g.get(stat_type, 0) or 0) for g in player_stats]
        vals_recent = vals_all[-n_games:]
        if not vals_recent or not vals_all:
            return 0.5
        season_avg = sum(vals_all) / len(vals_all) if vals_all else 0.0
        weighted_recent = StatsCalculator.calculate_weighted_average(vals_recent)
        if season_avg == 0:
            return 0.5
        ratio = (weighted_recent - season_avg) / season_avg
        if direction.lower() == "under":
            ratio = -ratio
        return max(0.0, min(1.0, 0.5 + ratio))

    @staticmethod
    def calculate_volume_score(player_stats: List[Dict], min_games: int = 5, ideal_games: int = 20) -> float:
        """0‒1 score based on sample size.  ≥ ideal_games → 1.0."""
        n = len(player_stats)
        if n < min_games:
            return 0.0
        return min(1.0, n / ideal_games)

    @staticmethod
    def calculate_home_away_split(
        player_stats: List[Dict], stat_type: str, line_value: float, direction: str = "over", is_home: Optional[bool] = None
    ) -> float:
        """
        Hit-rate filtered to home or away games.
        Matchup field format: "LAL vs DEN" (home) or "LAL @ DEN" (away).
        Falls back to overall hit rate when we can't determine or filter yields < 3 games.
        """
        if is_home is None:
            return StatsCalculator.calculate_hit_rate(player_stats, line_value, stat_type, direction)
        filtered = []
        for g in player_stats:
            matchup = str(g.get("matchup", ""))
            if is_home and " vs " in matchup:
                filtered.append(g)
            elif not is_home and " @ " in matchup:
                filtered.append(g)
        if len(filtered) < 3:
            return StatsCalculator.calculate_hit_rate(player_stats, line_value, stat_type, direction)
        return StatsCalculator.calculate_hit_rate(filtered, line_value, stat_type, direction)

    @staticmethod
    def calculate_streak(player_stats: List[Dict], stat_type: str, line_value: float, direction: str = "over") -> int:
        """Current streak of consecutive hits (from most recent game backwards)."""
        vals = [float(g.get(stat_type, 0) or 0) for g in player_stats]
        streak = 0
        for v in reversed(vals):
            hit = (v > line_value) if direction.lower() == "over" else (v < line_value)
            if hit:
                streak += 1
            else:
                break
        return streak

    @staticmethod
    def calculate_heat_index(player_stats: List[Dict], stat_type: str, n_games: int = 10) -> float:
        """
        0-1 score: upward trend in recent games (recent avg > earlier avg).
        Higher = player is heating up in this stat.
        """
        vals = [float(g.get(stat_type, 0) or 0) for g in player_stats][-n_games:]
        if len(vals) < 4:
            return 0.5
        mid = len(vals) // 2
        first_half_avg = sum(vals[:mid]) / mid if mid else 0.0
        second_half_avg = sum(vals[mid:]) / (len(vals) - mid) if (len(vals) - mid) else 0.0
        if first_half_avg == 0:
            return 0.5
        ratio = (second_half_avg - first_half_avg) / first_half_avg
        return max(0.0, min(1.0, 0.5 + ratio))

    @staticmethod
    def calculate_volatility_index(player_stats: List[Dict], stat_type: str, n_games: int = 10) -> float:
        """
        0-1 score: coefficient of variation over recent games. Higher = more volatile.
        """
        vals = [float(g.get(stat_type, 0) or 0) for g in player_stats][-n_games:]
        if len(vals) < 3:
            return 0.0
        mean = sum(vals) / len(vals)
        if mean == 0:
            return 0.0
        variance = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = math.sqrt(variance)
        cv = std / mean
        return round(min(1.0, cv), 2)

    @staticmethod
    def calculate_calibrated_confidence(raw_confidence_0_1: float) -> float:
        """
        Map raw confidence (0-1) to a calibrated 0-100 score with sigmoid-like spread
        so values don't cluster in the 60-75 range. Centers at 0.6; steeper slope
        spreads small differences.
        """
        if raw_confidence_0_1 <= 0.0:
            return 0.0
        if raw_confidence_0_1 >= 1.0:
            return 100.0
        # Sigmoid: 50 + 50 * (1 / (1 + exp(-k*(x - 0.6)))) with k=10 for spread
        k = 10.0
        x = raw_confidence_0_1 - 0.6
        t = 1.0 / (1.0 + math.exp(-k * x))
        return round(min(99.0, max(1.0, 50.0 + 50.0 * t)), 1)
