#!/usr/bin/env python3
"""
Backfill pick_of_the_day_records and optionally game_prediction_records, then settle for graded accuracy.

Run from repo backend directory:
  cd backend && PYTHONPATH=. python scripts/backfill_accuracy_history.py --dry-run
  cd backend && PYTHONPATH=. python scripts/backfill_accuracy_history.py --days 14 --settle

With explicit range (inclusive):
  cd backend && PYTHONPATH=. python scripts/backfill_accuracy_history.py \\
    --from-date 2025-03-10 --to-date 2025-03-23 --pick-of-the-day --settle

Requires DATABASE_URL (and normal NBA API access) in the environment; optional: python-dotenv loads .env from cwd.

Flags:
  --days N          Last N calendar days ending yesterday (default: 14). Ignored if --from-date/--to-date set.
  --from-date       YYYY-MM-DD start (inclusive)
  --to-date         YYYY-MM-DD end (inclusive)
  --pick-of-the-day / --no-pick-of-the-day   Backfill AI pick rows (default: on)
  --game-predictions                        Also backfill game_prediction_records
  --settle / --no-settle                    Run settle_all_for_date per day (default: on)
  --top-picks                               Hybrid Top Picks: if no prop_prediction rows for a date, run BestPicksService.get_top_picks for that day
  --dry-run                                 Log actions only; no DB writes
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from typing import Any, Dict, Iterator, Optional

# Run from backend so app is importable
sys.path.insert(0, ".")

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _iter_dates(start: date, end: date) -> Iterator[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def build_pick_of_the_day_dict(best: Dict[str, Any]) -> Dict[str, Any]:
    """Same shape as props_v1.pick_of_the_day and admin warm-dashboard."""
    return {
        "playerId": best.get("playerId"),
        "playerName": best.get("playerName"),
        "type": best.get("type"),
        "marketLine": best.get("marketLine") or best.get("fairLine"),
        "fairLine": best.get("fairLine"),
        "suggestion": best.get("suggestion", "over"),
        "confidence": best.get("confidence"),
        "rationale": best.get("rationale"),
        "gameDate": best.get("gameDate") or best.get("game_date"),
        "confidenceSource": best.get("confidenceSource"),
        "rationaleSource": best.get("rationaleSource"),
        "mlAvailable": best.get("mlAvailable"),
        "matchup_score": best.get("matchup_score"),
        "insight_type": best.get("insight_type"),
        "matchup_explanation": best.get("matchup_explanation"),
        "opponent_abbr": best.get("opponent_abbr"),
        "opponent_def_rank_vs_position": best.get("opponent_def_rank_vs_position"),
        "supporting_metrics": best.get("supporting_metrics"),
    }


def fetch_best_pick_for_date(target_date_str: str, season: str) -> Optional[Dict[str, Any]]:
    from app.services.daily_props_service import DailyPropsService
    from app.utils.season import get_current_season

    season = season or get_current_season()
    try:
        result = DailyPropsService.get_top_props_for_date(
            date=target_date_str,
            season=season,
            min_confidence=50.0,
            limit=200,
            last_n=10,
        )
        items = result.get("items", [])
    except Exception as e:
        print(f"  [pick] DailyPropsService failed: {e}")
        return None

    items = [
        i
        for i in items
        if (i.get("gameDate") or i.get("game_date") or "").startswith(target_date_str[:10])
    ]
    if not items:
        return None
    items.sort(key=lambda x: (x.get("confidence") or 0), reverse=True)
    return build_pick_of_the_day_dict(items[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill accuracy DB rows for historical dates.")
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Number of calendar days ending yesterday (default: 14). Used when --from-date/--to-date omitted.",
    )
    parser.add_argument("--from-date", type=str, default=None, help="Start date YYYY-MM-DD (inclusive)")
    parser.add_argument("--to-date", type=str, default=None, help="End date YYYY-MM-DD (inclusive)")
    parser.add_argument(
        "--no-pick-of-the-day",
        dest="pick_of_the_day",
        action="store_false",
        help="Skip AI pick of the day backfill",
    )
    parser.add_argument(
        "--game-predictions",
        action="store_true",
        help="Also insert game_prediction_records via get_todays_predictions",
    )
    parser.add_argument(
        "--no-settle",
        dest="settle",
        action="store_false",
        help="Skip settle_all_for_date after backfill",
    )
    parser.add_argument(
        "--top-picks",
        action="store_true",
        help="If prop_prediction_records are missing for a date, run BestPicksService.get_top_picks (historical scoreboard)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions only; no database writes",
    )
    parser.add_argument(
        "--season",
        type=str,
        default=None,
        help="NBA season string (e.g. 2025-26). Defaults to get_current_season().",
    )
    parser.add_argument(
        "--use-pipeline",
        action="store_true",
        help="Use pipeline jobs (build_dashboard, settle_accuracy) instead of legacy settle path",
    )
    parser.set_defaults(pick_of_the_day=True, settle=True)
    args = parser.parse_args()

    if args.from_date or args.to_date:
        if not args.from_date or not args.to_date:
            print("error: both --from-date and --to-date are required when using explicit range", file=sys.stderr)
            return 2
        start = date.fromisoformat(args.from_date)
        end = date.fromisoformat(args.to_date)
    else:
        yesterday = date.today() - timedelta(days=1)
        start = yesterday - timedelta(days=args.days - 1)
        end = yesterday

    if start > end:
        print("error: start date after end date", file=sys.stderr)
        return 2

    from app.utils.season import get_current_season

    season = args.season or get_current_season()

    if not args.dry_run:
        from app.services.accuracy_tracking_service import (
            record_game_predictions,
            record_pick_of_the_day,
            settle_all_for_date,
        )
        from app.services.game_prediction_service import get_game_prediction_service

        pred_svc = get_game_prediction_service()
    else:
        record_pick_of_the_day = None  # type: ignore[assignment]
        record_game_predictions = None  # type: ignore[assignment]
        settle_all_for_date = None  # type: ignore[assignment]
        pred_svc = None
        if args.game_predictions:
            from app.services.game_prediction_service import get_game_prediction_service

            pred_svc = get_game_prediction_service()

    print(
        f"Range: {start.isoformat()} .. {end.isoformat()} ({sum(1 for _ in _iter_dates(start, end))} days)"
        f" dry_run={args.dry_run} pick_of_the_day={args.pick_of_the_day} "
        f"game_predictions={args.game_predictions} top_picks={args.top_picks} settle={args.settle}"
    )

    for d in _iter_dates(start, end):
        ds = d.isoformat()
        print(f"\n=== {ds} ===")

        if args.pick_of_the_day:
            pick = fetch_best_pick_for_date(ds, season)
            if not pick or pick.get("playerId") is None:
                print("  [pick] no candidate items / missing playerId — skip")
            elif args.dry_run:
                print(f"  [pick] would record_pick_of_the_day: {pick.get('playerName')} {pick.get('type')} line={pick.get('marketLine')}")
            else:
                ok = record_pick_of_the_day(d, pick)  # type: ignore[misc]
                print(f"  [pick] record_pick_of_the_day -> {'inserted' if ok else 'skipped (exists or invalid)'}")

        if args.game_predictions:
            try:
                preds = pred_svc.get_todays_predictions(d) if pred_svc else []
            except Exception as e:
                print(f"  [games] get_todays_predictions failed: {e}")
                preds = []
            if args.dry_run:
                print(f"  [games] would record_game_predictions: {len(preds)} rows")
            else:
                n = record_game_predictions(d, preds)  # type: ignore[misc]
                print(f"  [games] record_game_predictions -> {n} new rows (0 if already had rows for date)")

        if args.top_picks:
            if args.dry_run:
                print(f"  [top-picks] would check prop_prediction_records for {ds}; if empty, BestPicksService.get_top_picks")
            else:
                from app.database import get_db
                from app.models.prediction_accuracy import PropPredictionRecord
                from app.services.best_picks_service import BestPicksService

                db = next(get_db())
                try:
                    n_existing = (
                        db.query(PropPredictionRecord)
                        .filter(PropPredictionRecord.record_date == d)
                        .count()
                    )
                finally:
                    db.close()
                if n_existing > 0:
                    print(f"  [top-picks] {n_existing} prop row(s) already exist — skip")
                else:
                    try:
                        BestPicksService.get_top_picks(date=ds, season=season)
                        print(f"  [top-picks] get_top_picks completed for {ds}")
                    except Exception as e:
                        print(f"  [top-picks] get_top_picks failed: {e}")

        if args.settle:
            if args.dry_run:
                if args.use_pipeline:
                    print(f"  [settle] would pipeline run settle_accuracy --date {ds}")
                else:
                    print(f"  [settle] would settle_all_for_date({ds})")
            elif args.use_pipeline:
                from app.pipeline.context import PipelineContext
                from app.pipeline.runner import run_job
                from app.pipeline.jobs import settle_accuracy as settle_job

                ctx = PipelineContext(job_name="settle_accuracy", target_date=d, season=season)
                out = run_job(ctx, settle_job.run)
                print(f"  [settle] pipeline -> {out}")
            else:
                out = settle_all_for_date(d, season=season)  # type: ignore[misc]
                gp = out.get("game_predictions") or {}
                pd = out.get("pick_of_the_day") or {}
                tp = out.get("top_picks") or {}
                print(
                    f"  [settle] game_settled={gp.get('settled')} pick={pd} top_picks={tp}"
                )

        if args.use_pipeline and args.top_picks and not args.dry_run:
            from app.pipeline.context import PipelineContext
            from app.pipeline.runner import run_job
            from app.pipeline.jobs import build_dashboard as build_job

            ctx = PipelineContext(job_name="build_dashboard", target_date=d, season=season)
            out = run_job(ctx, build_job.run)
            print(f"  [pipeline] build_dashboard -> {out}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
