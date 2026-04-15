from app.backtesting import generate_mock_market_data, BacktestEngine
from app.backtesting.models import MarketBar, StrategySignal
from app.services.risk_manager import RiskManager, RiskLimits
from datetime import datetime, timezone, timedelta


class BuyThenSellStrategy:
    """
    Reuses strategy contract used by backtesting engine.
    Buys on first bar and sells on second bar.
    """

    def __init__(self):
        self._count = 0

    def on_bar(self, bar: MarketBar, portfolio_state):
        self._count += 1
        if self._count == 1:
            return StrategySignal(market=bar.market, side="buy", size=1)
        if self._count == 2:
            return StrategySignal(market=bar.market, side="sell", size=1)
        return None


class AlwaysBuyStrategy:
    def on_bar(self, bar: MarketBar, portfolio_state):
        return StrategySignal(market=bar.market, side="buy", size=1)


def test_backtest_tracks_pnl_winrate_and_drawdown():
    t0 = datetime.now(timezone.utc).replace(microsecond=0)
    bars = [
        MarketBar(timestamp=t0, market="LAL_ML", price=100),
        MarketBar(timestamp=t0 + timedelta(minutes=5), market="LAL_ML", price=110),
        MarketBar(timestamp=t0 + timedelta(minutes=10), market="LAL_ML", price=105),
    ]
    strategy = BuyThenSellStrategy()
    risk = RiskManager(RiskLimits(max_position_per_market=10, max_daily_loss=1000, max_open_trades=5))
    engine = BacktestEngine(strategy=strategy, risk_manager=risk)
    result = engine.run(bars)

    assert result.realized_pnl == 10.0
    assert result.win_rate == 1.0
    assert result.total_closed_trades == 1
    assert result.trades_executed == 2
    assert result.trades_rejected == 0
    assert result.max_drawdown_abs >= 0.0
    assert result.max_drawdown_pct >= 0.0


def test_backtest_stops_on_kill_switch():
    bars = generate_mock_market_data(steps=50, seed=11)
    strategy = AlwaysBuyStrategy()
    risk = RiskManager(RiskLimits(max_position_per_market=1, max_daily_loss=1, max_open_trades=1))
    engine = BacktestEngine(strategy=strategy, risk_manager=risk)
    result = engine.run(bars)
    assert result.kill_switch_triggered is True
    assert result.trades_rejected >= 1
