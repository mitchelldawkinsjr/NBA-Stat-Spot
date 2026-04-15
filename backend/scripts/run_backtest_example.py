"""
Example:
    python backend/scripts/run_backtest_example.py
    python backend/scripts/run_backtest_example.py --csv backend/data/sample_market_data.csv
"""
import argparse

from app.backtesting import (
    generate_mock_market_data,
    load_market_data_from_csv,
    load_market_data_from_json,
    BacktestEngine,
)
from app.services.risk_manager import RiskManager, RiskLimits
from app.services.ai import MarketAnalysisAssistant
from app.services.strategies import SimpleMomentumStrategy


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run backtest example.")
    parser.add_argument("--csv", type=str, default=None, help="Path to CSV historical data (timestamp,market,price).")
    parser.add_argument("--json", type=str, default=None, help="Path to JSON historical data.")
    parser.add_argument("--market", type=str, default="LAL_ML", help="Market for mock data mode.")
    parser.add_argument("--steps", type=int, default=200, help="Number of mock bars in mock mode.")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if args.csv:
        bars = load_market_data_from_csv(args.csv)
    elif args.json:
        bars = load_market_data_from_json(args.json)
    else:
        bars = generate_mock_market_data(
            market=args.market,
            start_price=100,
            steps=args.steps,
            interval_minutes=5,
            seed=42,
        )

    ai_assistant = MarketAnalysisAssistant(lookback=20)
    strategy = SimpleMomentumStrategy(threshold=0.8, trade_size=1.0, ai_assistant=ai_assistant)
    risk = RiskManager(
        RiskLimits(
            max_position_per_market=5.0,
            max_daily_loss=75.0,
            max_open_trades=3,
        )
    )

    engine = BacktestEngine(strategy=strategy, risk_manager=risk)
    result = engine.run(bars)

    print("=== Backtest Summary ===")
    print(f"Total PnL: {result.pnl:.2f}")
    print(f"Realized PnL: {result.realized_pnl:.2f}")
    print(f"Unrealized PnL: {result.unrealized_pnl:.2f}")
    print(f"Win Rate: {result.win_rate:.2%}")
    print(f"Closed Trades: {result.total_closed_trades} (wins={result.wins}, losses={result.losses})")
    print(f"Executed / Rejected: {result.trades_executed} / {result.trades_rejected}")
    print(f"Max Drawdown: {result.max_drawdown_abs:.2f} ({result.max_drawdown_pct:.2%})")
    print(f"Kill Switch Triggered: {result.kill_switch_triggered}")
    analysis = strategy.get_last_analysis(args.market if not args.csv and not args.json else bars[-1].market if bars else "LAL_ML")
    if analysis:
        print("AI Market Analysis (advisory):")
        print(f"  Sentiment: {analysis.market_sentiment}")
        print(f"  Unusual Activity: {analysis.unusual_activity or ['none']}")
        print(f"  Potential Mispricings: {analysis.potential_mispricings or ['none']}")


if __name__ == "__main__":
    main()
