from __future__ import annotations

from typing import Dict, Any

from .risk_manager import RiskManager


class TradeExecutor:
    """
    Thin execution layer that enforces RiskManager checks before applying fills.
    """

    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager

    def execute_trade(self, market: str, quantity: float, price: float) -> Dict[str, Any]:
        ok, reason = self.risk_manager.apply_trade(market=market, quantity=quantity, price=price)
        if not ok:
            return {
                "accepted": False,
                "reason": reason,
                "risk": self.risk_manager.snapshot(),
            }
        return {
            "accepted": True,
            "market": market,
            "quantity": quantity,
            "price": price,
            "risk": self.risk_manager.snapshot(),
        }

    def update_market_price(self, market: str, price: float) -> Dict[str, Any]:
        self.risk_manager.update_mark_price(market=market, price=price)
        return {
            "updated": True,
            "market": market,
            "price": price,
            "risk": self.risk_manager.snapshot(),
        }

