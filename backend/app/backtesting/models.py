from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class MarketBar:
    timestamp: datetime
    market: str
    price: float


@dataclass(frozen=True)
class StrategySignal:
    market: str
    side: Literal["buy", "sell"]
    size: float

