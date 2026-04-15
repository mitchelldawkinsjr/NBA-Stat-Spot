from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any

from ..services.risk_manager import RiskManager
from ..services.trade_executor import TradeExecutor
from .metrics import max_drawdown, win_rate
from .models import MarketBar
from .strategy import BacktestStrategy


@dataclass
class BacktestResult:
    pnl: float
    realized_pnl: float
    unrealized_pnl: float
    win_rate: float
    wins: int
    losses: int
    total_closed_trades: int
    max_drawdown_abs: float
    max_drawdown_pct: float
    equity_curve: List[float]
    trades_executed: int
    trades_rejected: int
    kill_switch_triggered: bool
    final_state: Dict[str, Any]


class BacktestEngine:
    """
    Replays bars step-by-step and runs provided strategy logic through executor/risk manager.
    """

    def __init__(self, strategy: BacktestStrategy, risk_manager: RiskManager):
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.executor = TradeExecutor(risk_manager=risk_manager)

    def run(self, bars: List[MarketBar]) -> BacktestResult:
        ordered = sorted(bars, key=lambda b: b.timestamp)
        equity_curve: List[float] = []
        wins = 0
        losses = 0
        trades_executed = 0
        trades_rejected = 0

        for bar in ordered:
            # Replay market state tick-by-tick.
            self.executor.update_market_price(market=bar.market, price=bar.price)
            before_realized = self.risk_manager.realized_pnl()

            signal = self.strategy.on_bar(bar, self.risk_manager.snapshot())
            if signal and signal.size > 0:
                qty = signal.size if signal.side == "buy" else -signal.size
                execution = self.executor.execute_trade(market=signal.market, quantity=qty, price=bar.price)
                if execution.get("accepted"):
                    trades_executed += 1
                    after_realized = self.risk_manager.realized_pnl()
                    delta_realized = after_realized - before_realized
                    if delta_realized > 0:
                        wins += 1
                    elif delta_realized < 0:
                        losses += 1
                else:
                    trades_rejected += 1

            equity_curve.append(self.risk_manager.total_pnl())
            if self.risk_manager.kill_switch:
                break

        final = self.risk_manager.snapshot()
        dd_abs, dd_pct = max_drawdown(equity_curve)
        return BacktestResult(
            pnl=final["total_pnl"],
            realized_pnl=final["realized_pnl"],
            unrealized_pnl=final["unrealized_pnl"],
            win_rate=win_rate(wins, losses),
            wins=wins,
            losses=losses,
            total_closed_trades=wins + losses,
            max_drawdown_abs=dd_abs,
            max_drawdown_pct=dd_pct,
            equity_curve=equity_curve,
            trades_executed=trades_executed,
            trades_rejected=trades_rejected,
            kill_switch_triggered=final["kill_switch"],
            final_state=final,
        )
