from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from typing import Dict, Any


@dataclass
class RiskLimits:
    max_position_per_market: float
    max_daily_loss: float
    max_open_trades: int


@dataclass
class Position:
    market: str
    quantity: float = 0.0
    avg_price: float = 0.0
    last_price: float = 0.0
    realized_pnl: float = 0.0

    @property
    def notional_exposure(self) -> float:
        return abs(self.quantity * (self.last_price or self.avg_price or 0.0))

    @property
    def unrealized_pnl(self) -> float:
        if self.quantity == 0:
            return 0.0
        return (self.last_price - self.avg_price) * self.quantity


class RiskManager:
    """
    Tracks portfolio exposure and PnL and enforces risk limits.
    Kill switch is auto-enabled when hard limits are breached.
    """

    def __init__(self, limits: RiskLimits):
        self.limits = limits
        self.positions: Dict[str, Position] = {}
        self.kill_switch = False
        self.block_reason: str | None = None
        self._day = date.today()
        self._daily_realized_pnl = 0.0

    def _roll_day_if_needed(self) -> None:
        today = date.today()
        if today != self._day:
            self._day = today
            self._daily_realized_pnl = 0.0

    def update_mark_price(self, market: str, price: float) -> None:
        if market in self.positions:
            self.positions[market].last_price = float(price)

    def total_exposure(self) -> float:
        return sum(p.notional_exposure for p in self.positions.values())

    def realized_pnl(self) -> float:
        return sum(p.realized_pnl for p in self.positions.values())

    def unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions.values())

    def total_pnl(self) -> float:
        return self.realized_pnl() + self.unrealized_pnl()

    def open_trades_count(self) -> int:
        return sum(1 for p in self.positions.values() if p.quantity != 0)

    def _trip_kill_switch(self, reason: str) -> None:
        self.kill_switch = True
        self.block_reason = reason

    def can_open_trade(self, market: str, quantity: float, price: float) -> tuple[bool, str | None]:
        self._roll_day_if_needed()
        if self.kill_switch:
            return False, self.block_reason or "Kill switch is active"

        pos = self.positions.get(market, Position(market=market))
        projected_qty = pos.quantity + float(quantity)
        if abs(projected_qty) > self.limits.max_position_per_market:
            reason = f"max_position_per_market exceeded for {market}"
            self._trip_kill_switch(reason)
            return False, reason

        projected_open = self.open_trades_count()
        if pos.quantity == 0 and projected_qty != 0:
            projected_open += 1
        if projected_open > self.limits.max_open_trades:
            reason = "max_open_trades exceeded"
            self._trip_kill_switch(reason)
            return False, reason

        # Daily realized loss guard.
        if self._daily_realized_pnl <= -abs(self.limits.max_daily_loss):
            reason = "max_daily_loss reached"
            self._trip_kill_switch(reason)
            return False, reason

        # Keep price valid.
        if price <= 0:
            return False, "invalid price"

        return True, None

    def apply_trade(self, market: str, quantity: float, price: float) -> tuple[bool, str | None]:
        """
        Applies filled trade to position and PnL.
        quantity > 0 buy, quantity < 0 sell.
        """
        ok, reason = self.can_open_trade(market, quantity, price)
        if not ok:
            return False, reason

        price = float(price)
        qty = float(quantity)
        pos = self.positions.get(market, Position(market=market))
        if pos.last_price == 0:
            pos.last_price = price

        # If trade reduces/reverses position, book realized PnL for closed portion.
        if pos.quantity != 0 and (pos.quantity > 0) != (qty > 0):
            closing_qty = min(abs(pos.quantity), abs(qty))
            realized = (price - pos.avg_price) * closing_qty * (1 if pos.quantity > 0 else -1)
            pos.realized_pnl += realized
            self._daily_realized_pnl += realized

        new_qty = pos.quantity + qty
        if new_qty == 0:
            pos.quantity = 0.0
            pos.avg_price = 0.0
        elif pos.quantity == 0 or (pos.quantity > 0) == (qty > 0):
            # Increasing same direction position: weighted average.
            total_notional = (abs(pos.quantity) * pos.avg_price) + (abs(qty) * price)
            pos.quantity = new_qty
            pos.avg_price = total_notional / abs(new_qty)
        else:
            # Reversal with residual qty uses current fill as new basis.
            pos.quantity = new_qty
            pos.avg_price = price

        pos.last_price = price
        self.positions[market] = pos

        if self._daily_realized_pnl <= -abs(self.limits.max_daily_loss):
            self._trip_kill_switch("max_daily_loss reached")
            return False, self.block_reason

        return True, None

    def snapshot(self) -> Dict[str, Any]:
        self._roll_day_if_needed()
        return {
            "kill_switch": self.kill_switch,
            "block_reason": self.block_reason,
            "limits": asdict(self.limits),
            "total_exposure": round(self.total_exposure(), 4),
            "realized_pnl": round(self.realized_pnl(), 4),
            "unrealized_pnl": round(self.unrealized_pnl(), 4),
            "total_pnl": round(self.total_pnl(), 4),
            "daily_realized_pnl": round(self._daily_realized_pnl, 4),
            "open_trades": self.open_trades_count(),
            "positions": {
                m: {
                    "quantity": round(p.quantity, 6),
                    "avg_price": round(p.avg_price, 6),
                    "last_price": round(p.last_price, 6),
                    "realized_pnl": round(p.realized_pnl, 4),
                    "unrealized_pnl": round(p.unrealized_pnl, 4),
                    "notional_exposure": round(p.notional_exposure, 4),
                }
                for m, p in self.positions.items()
            },
        }

