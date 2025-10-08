from typing import Dict, List
from statistics import mean

# Minimal, deterministic feature engineering for v1

def ewma(values: List[float], alpha: float = 0.4) -> float:
    if not values:
        return 0.0
    s = values[0]
    for v in values[1:]:
        s = alpha * v + (1 - alpha) * s
    return float(s)


def rolling_mean(values: List[float], n: int) -> float:
    if not values:
        return 0.0
    window = values[-n:] if n > 0 else values
    return float(mean(window))


def project_stat(per_minute: float, minutes: float, pace_adj: float, def_adj: float) -> float:
    return max(0.0, per_minute * minutes * pace_adj * def_adj)


def suggest_props_stub() -> List[Dict]:
    # Placeholder suggestion
    return [
        {
            "type": "PTS",
            "fairLine": 20.5,
            "confidence": 0.55,
            "rationale": ["Stubbed rationale (v1)"],
            "features": {"minutesProj": 32, "paceAdj": 1.0, "defAdj": 1.0},
            "distribution": {"mean": 20.1, "variance": 18.0},
        }
    ]
