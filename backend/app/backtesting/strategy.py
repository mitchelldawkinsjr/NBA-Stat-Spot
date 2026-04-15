from __future__ import annotations

from typing import Protocol, Dict, Any, Optional

from .models import MarketBar, StrategySignal


class BacktestStrategy(Protocol):
    """
    Strategy contract reused by backtesting and live execution wrappers.
    """

    def on_bar(self, bar: MarketBar, portfolio_state: Dict[str, Any]) -> Optional[StrategySignal]:
        ...

