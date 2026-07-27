"""CLI: python -m app.pipeline run <job> [options]"""
from __future__ import annotations
import argparse
import sys
from datetime import date, datetime
from typing import Optional

from .context import PipelineContext
from .runner import run_job
from .jobs import (
    ingest_schedule,
    ingest_boxscores,
    ingest_player_logs,
    compute_analytics,
    build_prop_evaluations,
    build_dashboard,
    build_ranks,
    settle_accuracy,
    backfill_settlement_stats,
    data_quality,
)

JOBS = {
    "ingest_schedule": ingest_schedule.run,
    "ingest_boxscores": ingest_boxscores.run,
    "ingest_player_logs": ingest_player_logs.run,
    "compute_analytics": compute_analytics.run,
    "build_prop_evaluations": build_prop_evaluations.run,
    "build_dashboard": build_dashboard.run,
    "build_ranks": build_ranks.run,
    "settle_accuracy": settle_accuracy.run,
    "backfill_settlement_stats": backfill_settlement_stats.run,
    "data_quality": data_quality.run,
}

# Optional jobs (may not exist on every deploy tree).
try:
    from .jobs import build_opponent_analysis

    JOBS["build_opponent_analysis"] = build_opponent_analysis.run
except ImportError:
    pass


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    return date.fromisoformat(s[:10])


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="app.pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run a pipeline job")
    run_p.add_argument("job", choices=sorted(JOBS.keys()))
    run_p.add_argument("--date", help="Target date YYYY-MM-DD")
    run_p.add_argument("--season", help="Season e.g. 2025-26")
    run_p.add_argument("--from-date", dest="from_date", help="Range start")
    run_p.add_argument("--to-date", dest="to_date", help="Range end")
    run_p.add_argument("--dry-run", action="store_true")

    backfill_p = sub.add_parser("backfill", help="Run jobs for each day in range")
    backfill_p.add_argument("--from-date", required=True)
    backfill_p.add_argument("--to-date", required=True)
    backfill_p.add_argument(
        "--jobs",
        default="ingest_schedule,ingest_boxscores,build_dashboard,settle_accuracy",
        help="Comma-separated job names",
    )
    backfill_p.add_argument("--season")

    args = parser.parse_args(argv)

    if args.command == "run":
        job = args.job
        if job not in JOBS:
            print(f"Unknown job: {job}", file=sys.stderr)
            return 1
        ctx = PipelineContext(
            job_name=job,
            target_date=_parse_date(args.date),
            season=args.season,
            from_date=_parse_date(getattr(args, "from_date", None)),
            to_date=_parse_date(getattr(args, "to_date", None)),
            dry_run=args.dry_run,
        )
        if args.dry_run:
            print(f"dry-run ok: {job}")
            return 0
        try:
            out = run_job(ctx, JOBS[job])
            print(out)
            return 0
        except Exception as e:
            print(f"failed: {e}", file=sys.stderr)
            return 1

    if args.command == "backfill":
        from_d = _parse_date(args.from_date)
        to_d = _parse_date(args.to_date)
        if not from_d or not to_d:
            print("Invalid date range", file=sys.stderr)
            return 1
        job_names = [j.strip() for j in args.jobs.split(",") if j.strip()]
        d = from_d
        while d <= to_d:
            for job in job_names:
                if job not in JOBS:
                    continue
                ctx = PipelineContext(
                    job_name=job,
                    target_date=d,
                    season=args.season,
                    from_date=d,
                    to_date=d,
                )
                print(f"Running {job} for {d.isoformat()}...")
                run_job(ctx, JOBS[job])
            d = date.fromordinal(d.toordinal() + 1)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
