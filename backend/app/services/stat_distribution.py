"""
Probability distribution layer for player stats (runs alongside existing pipeline).
Models: PTS/ASSISTS/PRA as Normal; REB/3PM as Poisson. Monte Carlo simulation for P(over) / P(under).
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

import numpy as np

# Optional scipy for distribution fitting
try:
    from scipy import stats as scipy_stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

N_SIMULATIONS = 10_000
STAT_NORMAL = {"pts", "ast", "pra"}
STAT_POISSON = {"reb", "tpm"}
LAST_N_GAMES = 20


def _extract_values(logs: List[Dict], stat: str) -> List[float]:
    if stat == "pra":
        return [
            float(g.get("pts", 0) or 0) + float(g.get("reb", 0) or 0) + float(g.get("ast", 0) or 0)
            for g in logs
        ]
    key = stat.lower()
    return [float(g.get(key, 0) or 0) for g in logs]


def compute_distribution(
    logs: List[Dict],
    stat: str,
    line: float,
    n_games: int = LAST_N_GAMES,
    n_sim: int = N_SIMULATIONS,
) -> Dict[str, Any]:
    """
    Fit distribution to last n_games values, run Monte Carlo, return mean, std, p_over, p_under, etc.
    Stat must be one of pts, reb, ast, tpm, pra.
    """
    stat_lower = stat.lower().strip()
    if stat_lower not in STAT_NORMAL and stat_lower not in STAT_POISSON:
        stat_lower = "pts"
    values = _extract_values(logs, stat_lower)[-n_games:]
    if len(values) < 3:
        return {
            "mean": 0.0,
            "std": 0.0,
            "p_over": 0.5,
            "p_under": 0.5,
            "percentile_line": 50.0,
            "distribution": "insufficient_data",
            "simulated_percentiles": {},
        }

    values_arr = np.array(values, dtype=float)
    mean = float(np.mean(values_arr))
    std = float(np.std(values_arr))
    if std < 1e-6:
        std = 1.0

    if not SCIPY_AVAILABLE:
        # Fallback: use empirical CDF from recent games
        p_over = sum(1 for v in values if v > line) / len(values)
        p_under = sum(1 for v in values if v < line) / len(values)
        return {
            "mean": round(mean, 2),
            "std": round(std, 2),
            "p_over": round(p_over, 4),
            "p_under": round(p_under, 4),
            "percentile_line": round(50.0, 1),
            "distribution": "empirical",
            "simulated_percentiles": {},
        }

    if stat_lower in STAT_POISSON:
        lam = max(0.1, mean)
        dist = scipy_stats.poisson(mu=lam)
        samples = dist.rvs(size=n_sim)
    else:
        dist = scipy_stats.norm(loc=mean, scale=std)
        samples = dist.rvs(size=n_sim)

    p_over = float(np.mean(samples > line))
    p_under = float(np.mean(samples < line))
    percentile_line = float(scipy_stats.percentileofscore(samples, line))

    simulated_percentiles = {
        "p5": float(np.percentile(samples, 5)),
        "p25": float(np.percentile(samples, 25)),
        "p50": float(np.percentile(samples, 50)),
        "p75": float(np.percentile(samples, 75)),
        "p95": float(np.percentile(samples, 95)),
    }

    return {
        "mean": round(mean, 2),
        "std": round(std, 2),
        "p_over": round(p_over, 4),
        "p_under": round(p_under, 4),
        "percentile_line": round(percentile_line, 1),
        "distribution": "poisson" if stat_lower in STAT_POISSON else "normal",
        "simulated_percentiles": {k: round(v, 2) for k, v in simulated_percentiles.items()},
        "line": line,
        "n_games_used": len(values),
    }
