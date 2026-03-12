"""
Insight scoring: matchup strength score (0–100) and insight type per pick.

Used by BestPicksService to attach matchup_score, insight_type, and (later) narrative
to top-picks items. Factors: position defense, recent form, pace, usage (optional), H2H.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .context_collector import ContextCollector
from .stats_calculator import StatsCalculator

STAT_DISPLAY = {"pts": "PTS", "reb": "REB", "ast": "AST", "tpm": "3PM", "pra": "PRA"}


# Stat key used in picks (PTS, REB, etc.) -> defensive rank key and H2H key
STAT_TO_RK = {"pts": "pts", "reb": "reb", "ast": "ast", "tpm": "3pm", "pra": "pts"}
STAT_TO_H2H = {"pts": "h2h_avg_pts", "reb": "h2h_avg_reb", "ast": "h2h_avg_ast", "tpm": "h2h_avg_pts", "pra": "h2h_avg_pts"}
# Pick "type" (PTS, REB, ...) -> stat key for scoring
DISPLAY_TO_STAT = {"PTS": "pts", "REB": "reb", "AST": "ast", "3PM": "tpm", "PRA": "pra"}
# Insight types (plan)
INSIGHT_TYPES = [
    "favorable_scoring_matchup",
    "assist_advantage",
    "rebounding_advantage",
    "defensive_weakness_exploit",
    "hot_streak",
    "pace_driven",
    "historical_dominance",
    "usage_spike",
]


def _norm_def_score(rank: Optional[int]) -> float:
    """Position/team def rank (1=best) -> 0–1 (higher = easier matchup)."""
    if rank is None:
        return 0.5
    return max(0.0, min(1.0, (31 - rank) / 30.0))


def _norm_pace(possessions: Optional[float], league_avg: float = 100.0) -> float:
    """Pace vs league avg -> 0–1 (higher = faster, more opportunities)."""
    if possessions is None or league_avg <= 0:
        return 0.5
    # e.g. 98–102 -> ~0.5, high pace -> higher
    return max(0.0, min(1.0, (possessions - 90) / 20.0))


def _norm_form(recent_avg: float, season_avg: float) -> float:
    """Recent vs season avg -> 0–1 (higher = better form)."""
    if season_avg <= 0:
        return 0.5
    ratio = recent_avg / season_avg
    if ratio >= 1.2:
        return 1.0
    if ratio <= 0.8:
        return 0.0
    return (ratio - 0.8) / 0.4


def _norm_h2h(h2h_avg: Optional[float], season_avg: float) -> float:
    """H2H vs season avg -> 0–1 (higher = historically strong vs this opponent)."""
    if season_avg <= 0 or h2h_avg is None:
        return 0.5
    ratio = h2h_avg / season_avg
    if ratio >= 1.15:
        return 1.0
    if ratio <= 0.85:
        return 0.0
    return (ratio - 0.85) / 0.3


def _usage_from_logs(logs: List[Dict], n: int = 10) -> Optional[float]:
    """Rough usage from last n games: (FGA + 0.44*FTA + TOV) per game. None if missing fields."""
    if not logs:
        return None
    recent = logs[-n:] if len(logs) >= n else logs
    total = 0.0
    count = 0
    for g in recent:
        fga = g.get("fga")
        fta = g.get("fta")
        tov = g.get("tov")
        if fga is None and fta is None and tov is None:
            continue
        fga = float(fga or 0)
        fta = float(fta or 0)
        tov = float(tov or 0)
        total += fga + 0.44 * fta + tov
        count += 1
    if count == 0:
        return None
    return total / count


def _norm_usage(usage: Optional[float], typical_high: float = 30.0) -> float:
    """Usage rate proxy -> 0–1 (higher = more involved)."""
    if usage is None:
        return 0.5
    return max(0.0, min(1.0, usage / typical_high))


def _ordinal(n: int) -> str:
    """e.g. 1 -> 1st, 2 -> 2nd, 3 -> 3rd, 25 -> 25th."""
    if n <= 0:
        return str(n)
    s = str(n)
    if 10 <= n % 100 <= 20:
        return s + "th"
    return s + {"1": "st", "2": "nd", "3": "rd"}.get(s[-1], "th")


def _derive_insight_type(
    stat: str,
    pos_def_rank: Optional[int],
    trend: str,
    pace_score: float,
    h2h_score: float,
    form_score: float,
) -> str:
    """Rule-based mapping to one of the fixed insight types."""
    stat_lower = stat.lower()
    # Defensive weakness / favorable matchup
    if pos_def_rank is not None and pos_def_rank >= 25:
        if stat_lower in ("pts", "tpm", "pra"):
            return "favorable_scoring_matchup"
        if stat_lower == "ast":
            return "assist_advantage"
        if stat_lower == "reb":
            return "rebounding_advantage"
        return "defensive_weakness_exploit"
    if trend == "up" and form_score >= 0.7:
        return "hot_streak"
    if pace_score >= 0.7:
        return "pace_driven"
    if h2h_score >= 0.7:
        return "historical_dominance"
    if pos_def_rank is not None and pos_def_rank >= 20:
        return "defensive_weakness_exploit"
    return "favorable_scoring_matchup"


def compute_matchup_score(
    player_id: int,
    stat: str,
    logs: List[Dict],
    opponent_team_id: int,
    position: Optional[str],
    opponent_def_ranks: Optional[Dict[str, int]],
    opponent_pos_def_ranks: Optional[Dict[str, int]],
    pace_ranks: Optional[Dict[int, Dict[str, Any]]],
    season: str,
    game_date: str,
    h2h: Optional[Dict[str, Any]] = None,
    player_name: Optional[str] = None,
    opponent_abbr: Optional[str] = None,
) -> Tuple[float, str, Optional[str], Optional[str], Optional[Dict[str, Any]]]:
    """
    Compute matchup_score (0–100), insight_type, and optional narrative for one (player, stat, opponent).

    Weights: defense vs position 0.35, recent form 0.30, pace 0.15, usage 0.10, historical 0.10.
    If usage cannot be computed, reweight: def 0.35, form 0.35, pace 0.15, historical 0.15.

    Returns:
        (matchup_score, insight_type, matchup_explanation, opponent_def_rank_vs_position, supporting_metrics)
        Last three are None when player_name/opponent_abbr not provided.
    """
    rk_key = STAT_TO_RK.get(stat, "pts")
    # Defense vs position (0.35)
    pos_rank = None
    if opponent_pos_def_ranks:
        pos_rank = opponent_pos_def_ranks.get(rk_key)
    if pos_rank is None and opponent_def_ranks:
        pos_rank = opponent_def_ranks.get(rk_key)
    def_score = _norm_def_score(pos_rank)

    # Recent form (0.30)
    n_recent = min(5, len(logs))
    if len(logs) < 3:
        form_score = 0.5
        trend = "flat"
    else:
        season_avg = StatsCalculator.calculate_rolling_average(logs, stat, n_games=min(10, len(logs)))
        recent_avg = StatsCalculator.calculate_rolling_average(logs[-n_recent:], stat, n_games=n_recent)
        form_score = _norm_form(recent_avg, season_avg)
        form_info = StatsCalculator.calculate_recent_form(logs, stat, n_games=n_recent)
        trend = form_info.get("trend", "flat")

    # Pace (0.15)
    opp_pace = None
    league_avg_poss = 100.0
    if pace_ranks:
        opp_data = pace_ranks.get(opponent_team_id) or {}
        opp_pace = opp_data.get("possessions")
        if pace_ranks and isinstance(pace_ranks, dict):
            all_poss = [v.get("possessions") for v in pace_ranks.values() if isinstance(v, dict) and v.get("possessions") is not None]
            if all_poss:
                league_avg_poss = sum(all_poss) / len(all_poss)
    pace_score = _norm_pace(opp_pace, league_avg_poss)

    # Usage (0.10) – optional
    usage = _usage_from_logs(logs)
    use_usage = usage is not None
    usage_score = _norm_usage(usage) if use_usage else 0.5

    # Historical (0.10)
    if h2h is None:
        try:
            h2h = ContextCollector.get_matchup_history(player_id, opponent_team_id, season, limit=10)
        except Exception:
            h2h = {}
    h2h_key = STAT_TO_H2H.get(stat, "h2h_avg_pts")
    h2h_avg = h2h.get(h2h_key) if h2h else None
    season_avg = StatsCalculator.calculate_rolling_average(logs, stat, n_games=min(20, len(logs))) if logs else 0.0
    h2h_score = _norm_h2h(h2h_avg, season_avg)

    if use_usage:
        w_def, w_form, w_pace, w_usage, w_h2h = 0.35, 0.30, 0.15, 0.10, 0.10
        composite = w_def * def_score + w_form * form_score + w_pace * pace_score + w_usage * usage_score + w_h2h * h2h_score
    else:
        w_def, w_form, w_pace, w_h2h = 0.35, 0.35, 0.15, 0.15
        composite = w_def * def_score + w_form * form_score + w_pace * pace_score + w_h2h * h2h_score

    matchup_score = round(composite * 100.0)
    matchup_score = max(0, min(100, matchup_score))

    insight_type = _derive_insight_type(stat, pos_rank, trend, pace_score, h2h_score, form_score)

    matchup_explanation = None
    opponent_def_rank_vs_position = None
    supporting_metrics = None
    if player_name and opponent_abbr:
        stat_label = STAT_DISPLAY.get(stat, stat.upper())
        pos_label = (position or "this position") + "s"
        if pos_rank is not None:
            opponent_def_rank_vs_position = f"#{pos_rank} most {stat_label} to {pos_label}"
        n_recent = min(5, len(logs))
        recent_avg = StatsCalculator.calculate_rolling_average(logs[-n_recent:], stat, n_games=n_recent) if logs else 0.0
        matchup_explanation = (
            f"Favorable matchup: {player_name} vs {opponent_abbr}. "
            + (f"{opponent_abbr} allows the {_ordinal(pos_rank)} most {stat_label} to {pos_label}; " if pos_rank is not None else "")
            + f"{player_name} is averaging {recent_avg:.1f} {stat_label} over the last {n_recent}."
        )
        supporting_metrics = {
            "recent_avg_5": round(recent_avg, 1),
            "pace": round(opp_pace, 1) if opp_pace is not None else None,
            "usage_approx": round(usage, 1) if usage is not None else None,
        }

    return (float(matchup_score), insight_type, matchup_explanation, opponent_def_rank_vs_position, supporting_metrics)
