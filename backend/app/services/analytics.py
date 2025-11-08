from __future__ import annotations
from typing import Dict, List, Optional
from statistics import mean, pstdev

from .nba_api_service import NBADataService


def _extract(values: List[dict], key: str) -> List[float]:
    return [float(v.get(key, 0) or 0) for v in values]


def _safe_variance(xs: List[float]) -> float:
    if not xs:
        return 0.0
    if len(xs) == 1:
        return 0.0
    try:
        return float(pstdev(xs)) ** 2
    except Exception:
        return 0.0


def suggest_from_gamelogs(player_id: int, season: Optional[str], lastN: Optional[int], market_lines: Optional[Dict[str, float]]) -> List[Dict]:
    logs = NBADataService.fetch_player_game_log(player_id=player_id, season=season)
    if lastN:
        logs = logs[: lastN]

    minutes = _extract(logs, "minutes")
    pts = _extract(logs, "pts")
    reb = _extract(logs, "reb")
    ast = _extract(logs, "ast")
    tpm = _extract(logs, "tpm")

    def _build(stat: str, series: List[float]) -> Dict:
        avg = float(mean(series)) if series else 0.0
        var = _safe_variance(series)
        median = sorted(series)[len(series) // 2] if series else 0.0
        market = market_lines.get(stat) if market_lines else None
        confidence = None
        edge = None
        if market is not None:
            # Simple z-score based confidence proxy (assumes normal)
            if var > 0:
                import math
                z = (avg - market) / (var ** 0.5)
                # Convert z to one-sided probability
                # Phi(z) ~ 0.5 * (1 + erf(z / sqrt(2)))
                confidence = 0.5 * (1 + math.erf(z / (2 ** 0.5)))
                edge = confidence - 0.5
            else:
                confidence = 1.0 if avg > market else 0.0
                edge = confidence - 0.5
        return {
            "type": stat,
            "fairLine": float(median),
            "confidence": float(confidence) if confidence is not None else 0.0,
            "marketLine": float(market) if market is not None else None,
            "edge": float(edge) if edge is not None else None,
            "rationale": [
                f"LastN avg={avg:.1f}",
                f"Variance={var:.1f}",
            ],
            "features": {
                "minutesProj": float(mean(minutes)) if minutes else 0.0,
            },
            "distribution": {"mean": avg, "variance": var},
        }

    suggestions = [
        _build("PTS", pts),
        _build("REB", reb),
        _build("AST", ast),
        _build("3PM", tpm),
        _build("PRA", [a + b + c for a, b, c in zip(pts, reb, ast)]),
    ]
    return suggestions
