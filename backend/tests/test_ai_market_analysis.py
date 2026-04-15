from datetime import datetime, timezone, timedelta

from app.backtesting.models import MarketBar
from app.services.ai import MarketAnalysisAssistant
from app.services.strategies import SimpleMomentumStrategy


def _bars(prices):
    t0 = datetime.now(timezone.utc).replace(microsecond=0)
    return [
        MarketBar(timestamp=t0 + timedelta(minutes=5 * i), market="LAL_ML", price=float(p))
        for i, p in enumerate(prices)
    ]


def test_ai_analysis_outputs_required_fields():
    assistant = MarketAnalysisAssistant(lookback=10)
    bars = _bars([100, 100.2, 99.9, 101.0, 102.0])
    out = assistant.analyze_market_conditions("LAL_ML", bars=bars, portfolio_state={"open_trades": 1, "total_exposure": 100})
    assert out.market_sentiment in {"bullish", "bearish", "neutral"}
    assert isinstance(out.unusual_activity, list)
    assert isinstance(out.potential_mispricings, list)
    assert "Do NOT provide trading decisions" in out.prompt


def test_strategy_integrates_ai_as_advisory_only():
    assistant = MarketAnalysisAssistant(lookback=5)
    strategy = SimpleMomentumStrategy(threshold=0.5, trade_size=1.0, ai_assistant=assistant)
    state = {"open_trades": 0, "total_exposure": 0}
    bars = _bars([100, 100.8, 101.5])
    # Warm strategy
    assert strategy.on_bar(bars[0], state) is None
    sig = strategy.on_bar(bars[1], state)
    # May produce a buy signal depending on adjusted threshold, but AI never emits executions itself.
    assert sig is None or sig.side in {"buy", "sell"}
    assert strategy.get_last_analysis("LAL_ML") is not None

