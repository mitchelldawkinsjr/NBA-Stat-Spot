from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from ...backtesting.models import MarketBar


@dataclass
class MarketAnalysis:
    """
    AI-assisted analysis payload. Informational only; never an execution instruction.
    """

    market_sentiment: str
    unusual_activity: List[str]
    potential_mispricings: List[str]
    prompt: str
    model_response: Optional[str] = None


class MarketAnalysisAssistant:
    """
    Builds structured prompts and returns a non-execution market analysis summary.
    This module intentionally does NOT return trade actions.
    """

    def __init__(self, lookback: int = 20):
        self.lookback = max(5, lookback)

    def build_structured_prompt(
        self,
        market: str,
        recent_prices: List[float],
        portfolio_state: Dict[str, Any],
    ) -> str:
        returns = []
        for i in range(1, len(recent_prices)):
            prev = recent_prices[i - 1]
            curr = recent_prices[i]
            if prev > 0:
                returns.append((curr - prev) / prev)
        avg_return = sum(returns) / len(returns) if returns else 0.0
        vol = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 0.0
        prompt = (
            "You are an AI market analyst assistant. "
            "Summarize market conditions only. "
            "Do NOT provide trading decisions, entries, exits, or position sizing.\n\n"
            "Return strict JSON with keys:\n"
            "- market_sentiment (bullish|bearish|neutral)\n"
            "- unusual_activity (array of strings)\n"
            "- potential_mispricings (array of strings)\n\n"
            f"Market: {market}\n"
            f"Recent prices ({len(recent_prices)}): {recent_prices}\n"
            f"Mean return: {avg_return:.6f}\n"
            f"Volatility proxy: {vol:.6f}\n"
            f"Open trades: {portfolio_state.get('open_trades')}\n"
            f"Current total exposure: {portfolio_state.get('total_exposure')}\n"
            "Focus on contextual analysis, not actions."
        )
        return prompt

    def analyze_market_conditions(
        self,
        market: str,
        bars: List[MarketBar],
        portfolio_state: Dict[str, Any],
    ) -> MarketAnalysis:
        recent = bars[-self.lookback :] if len(bars) > self.lookback else bars
        prices = [b.price for b in recent]
        prompt = self.build_structured_prompt(market=market, recent_prices=prices, portfolio_state=portfolio_state)

        # Deterministic fallback analysis (no live model call required).
        if len(prices) < 3:
            return MarketAnalysis(
                market_sentiment="neutral",
                unusual_activity=[],
                potential_mispricings=[],
                prompt=prompt,
                model_response=None,
            )

        change = prices[-1] - prices[0]
        sentiment = "bullish" if change > 0.5 else ("bearish" if change < -0.5 else "neutral")

        unusual_activity: List[str] = []
        potential_mispricings: List[str] = []
        deltas = [abs(prices[i] - prices[i - 1]) for i in range(1, len(prices))]
        avg_delta = sum(deltas) / len(deltas) if deltas else 0.0
        if deltas and deltas[-1] > avg_delta * 2.0:
            unusual_activity.append("Latest move is >2x recent average move.")
        if avg_delta > 1.5:
            unusual_activity.append("Elevated short-horizon volatility detected.")

        mean_price = sum(prices) / len(prices)
        if prices[-1] > mean_price * 1.03:
            potential_mispricings.append("Price is >3% above short-window mean.")
        elif prices[-1] < mean_price * 0.97:
            potential_mispricings.append("Price is >3% below short-window mean.")

        return MarketAnalysis(
            market_sentiment=sentiment,
            unusual_activity=unusual_activity,
            potential_mispricings=potential_mispricings,
            prompt=prompt,
            model_response=None,
        )

