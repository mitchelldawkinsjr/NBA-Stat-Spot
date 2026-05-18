"""Execute pipeline jobs with run tracking."""
from __future__ import annotations
from typing import Any, Callable, Dict

import structlog

from .context import PipelineContext, pipeline_session
from .repositories import pipeline_meta_repo

logger = structlog.get_logger()

JobFn = Callable[[PipelineContext, Any], Dict[str, Any]]


def run_job(ctx: PipelineContext, job_fn: JobFn) -> Dict[str, Any]:
    if ctx.dry_run:
        logger.info("pipeline_dry_run", job=ctx.job_name)
        return {"dry_run": True, "job": ctx.job_name}

    with pipeline_session() as db:
        run = pipeline_meta_repo.start_run(db, ctx.job_name)
        ctx.run_id = run.id
        try:
            stats = job_fn(ctx, db)
            pipeline_meta_repo.finish_run(db, run, "success", stats=stats)
            pipeline_meta_repo.update_watermark(
                db,
                ctx.job_name,
                rows_written=int(stats.get("rows_written", 0) or 0),
                last_game_date=stats.get("last_game_date"),
                meta=stats,
            )
            logger.info("pipeline_job_success", job=ctx.job_name, run_id=run.id, **stats)
            return {"status": "success", "run_id": run.id, **stats}
        except Exception as e:
            pipeline_meta_repo.finish_run(db, run, "failed", error=str(e))
            logger.exception("pipeline_job_failed", job=ctx.job_name, error=str(e))
            raise
