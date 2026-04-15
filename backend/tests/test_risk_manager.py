from app.services.risk_manager import RiskManager, RiskLimits
from app.services.trade_executor import TradeExecutor


def test_tracks_exposure_and_pnl():
    rm = RiskManager(RiskLimits(max_position_per_market=10, max_daily_loss=1000, max_open_trades=5))
    ex = TradeExecutor(rm)

    r1 = ex.execute_trade("LAL_ML", quantity=2, price=100)
    assert r1["accepted"] is True
    assert r1["risk"]["total_exposure"] == 200.0

    # Mark-to-market move creates unrealized PnL.
    mtm = ex.update_market_price("LAL_ML", 110)
    assert mtm["risk"]["unrealized_pnl"] == 20.0

    # Partial close realizes PnL.
    r2 = ex.execute_trade("LAL_ML", quantity=-1, price=110)
    assert r2["accepted"] is True
    assert r2["risk"]["realized_pnl"] == 10.0


def test_enforces_max_position_and_kill_switch():
    rm = RiskManager(RiskLimits(max_position_per_market=2, max_daily_loss=1000, max_open_trades=5))
    ex = TradeExecutor(rm)

    assert ex.execute_trade("BOS_ML", quantity=2, price=100)["accepted"] is True
    blocked = ex.execute_trade("BOS_ML", quantity=1, price=100)
    assert blocked["accepted"] is False
    assert blocked["risk"]["kill_switch"] is True
    assert "max_position_per_market" in (blocked["reason"] or "")


def test_enforces_max_open_trades():
    rm = RiskManager(RiskLimits(max_position_per_market=10, max_daily_loss=1000, max_open_trades=1))
    ex = TradeExecutor(rm)

    assert ex.execute_trade("DEN_ML", quantity=1, price=50)["accepted"] is True
    blocked = ex.execute_trade("NYK_ML", quantity=1, price=60)
    assert blocked["accepted"] is False
    assert blocked["risk"]["kill_switch"] is True
    assert blocked["reason"] == "max_open_trades exceeded"


def test_enforces_max_daily_loss_and_kill_switch():
    rm = RiskManager(RiskLimits(max_position_per_market=10, max_daily_loss=5, max_open_trades=5))
    ex = TradeExecutor(rm)

    assert ex.execute_trade("PHX_ML", quantity=1, price=100)["accepted"] is True
    # Close at a loss of 10 -> breach max_daily_loss of 5.
    blocked = ex.execute_trade("PHX_ML", quantity=-1, price=90)
    assert blocked["accepted"] is False
    assert blocked["risk"]["kill_switch"] is True
    assert blocked["reason"] == "max_daily_loss reached"

