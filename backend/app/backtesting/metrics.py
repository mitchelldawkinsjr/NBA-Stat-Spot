from __future__ import annotations

from typing import Iterable, Tuple


def win_rate(wins: int, losses: int) -> float:
    total = wins + losses
    if total == 0:
        return 0.0
    return wins / total


def max_drawdown(equity_curve: Iterable[float]) -> Tuple[float, float]:
    """
    Returns (max_drawdown_abs, max_drawdown_pct).
    """
    peak = None
    max_dd = 0.0
    max_dd_pct = 0.0
    for equity in equity_curve:
        if peak is None or equity > peak:
            peak = equity
        if peak is None:
            continue
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
        if peak > 0:
            dd_pct = dd / peak
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct
    return max_dd, max_dd_pct

