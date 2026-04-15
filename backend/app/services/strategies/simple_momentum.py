from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from ...backtesting.models import MarketBar, StrategySignal
from ..ai import MarketAnalysisAssistant, MarketAnalysis


@dataclass
class SimpleMomentumStrategy:
    """
    Example strategy logic intended to be reusable for both live and backtesting paths.
    - Buy when price increases by threshold vs previous bar.
    - Sell when price decreases by threshold vs previous bar.
    """

    threshold: float = 0.6
    trade_size: float = 1.0
    ai_assistant: Optional[MarketAnalysisAssistant] = None

    def __post_init__(self) -> None:
        self._last_price_by_market: Dict[str, float] = {}
        self._bars_by_market: Dict[str, List[MarketBar]] = {}
        self._last_analysis_by_market: Dict[str, MarketAnalysis] = {}

    def get_last_analysis(self, market: str) -> Optional[MarketAnalysis]:
        return self._last_analysis_by_market.get(market)

    def on_bar(self, bar: MarketBar, portfolio_state: Dict[str, Any]) -> Optional[StrategySignal]:
        bars = self._bars_by_market.setdefault(bar.market, [])
        bars.append(bar)

        adjusted_threshold = self.threshold
        if self.ai_assistant is not None:
            analysis = self.ai_assistant.analyze_market_conditions(
                market=bar.market,
                bars=bars,
                portfolio_state=portfolio_state,
            )
            self._last_analysis_by_market[bar.market] = analysis
            # AI is advisory only: we use sentiment as a soft threshold adjustment.
            if analysis.market_sentiment == "bearish":
                adjusted_threshold = self.threshold * 1.2
            elif analysis.market_sentiment == "bullish":
                adjusted_threshold = self.threshold * 0.9

        prev = self._last_price_by_market.get(bar.market)
        self._last_price_by_market[bar.market] = bar.price
        if prev is None:
            return None
        delta = bar.price - prev
        if delta >= adjusted_threshold:
            return StrategySignal(market=bar.market, side="buy", size=self.trade_size)
        if delta <= -adjusted_threshold:
            return StrategySignal(market=bar.market, side="sell", size=self.trade_size)
        return None
