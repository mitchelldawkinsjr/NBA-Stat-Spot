from __future__ import annotations

import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List

from .models import MarketBar


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_market_data_from_json(path: str | Path) -> List[MarketBar]:
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    bars = [
        MarketBar(
            timestamp=_parse_ts(row["timestamp"]),
            market=str(row["market"]),
            price=float(row["price"]),
        )
        for row in raw
    ]
    return sorted(bars, key=lambda b: b.timestamp)


def load_market_data_from_csv(path: str | Path) -> List[MarketBar]:
    p = Path(path)
    bars: List[MarketBar] = []
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bars.append(
                MarketBar(
                    timestamp=_parse_ts(str(row["timestamp"])),
                    market=str(row["market"]),
                    price=float(row["price"]),
                )
            )
    return sorted(bars, key=lambda b: b.timestamp)


def generate_mock_market_data(
    market: str = "LAL_ML",
    start_price: float = 100.0,
    steps: int = 120,
    interval_minutes: int = 5,
    seed: int = 7,
) -> List[MarketBar]:
    """
    Deterministic random walk mock data for quick local backtests.
    """
    rng = random.Random(seed)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    price = start_price
    bars: List[MarketBar] = []
    for i in range(steps):
        drift = 0.02 if i > steps // 2 else -0.01
        noise = rng.uniform(-1.0, 1.0)
        price = max(1.0, price + drift + noise)
        bars.append(
            MarketBar(
                timestamp=now + timedelta(minutes=i * interval_minutes),
                market=market,
                price=round(price, 4),
            )
        )
    return bars


def chunk_by_market(bars: Iterable[MarketBar]) -> dict[str, List[MarketBar]]:
    grouped: dict[str, List[MarketBar]] = {}
    for bar in bars:
        grouped.setdefault(bar.market, []).append(bar)
    return grouped
