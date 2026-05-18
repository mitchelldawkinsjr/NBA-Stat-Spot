"""Pipeline run and watermark persistence."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ...models.pipeline_runs import IngestWatermark, PipelineRun


def start_run(db: Session, job_name: str) -> PipelineRun:
    row = PipelineRun(job_name=job_name, status="started")
    db.add(row)
    db.flush()
    return row


def finish_run(
    db: Session,
    run: PipelineRun,
    status: str,
    stats: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    run.status = status
    run.finished_at = datetime.utcnow()
    run.stats_json = stats or {}
    if error:
        run.error_message = error[:512]


def update_watermark(
    db: Session,
    job_name: str,
    *,
    last_game_date: Optional[str] = None,
    rows_written: int = 0,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    row = db.query(IngestWatermark).filter(IngestWatermark.job_name == job_name).first()
    if not row:
        row = IngestWatermark(job_name=job_name)
        db.add(row)
    row.last_success_at = datetime.utcnow()
    if last_game_date:
        row.last_game_date = last_game_date
    row.rows_written = rows_written
    if meta:
        row.meta_json = meta


def get_last_runs(db: Session, limit: int = 20) -> list:
    return (
        db.query(PipelineRun)
        .order_by(PipelineRun.started_at.desc())
        .limit(limit)
        .all()
    )


def get_watermarks(db: Session) -> list:
    return db.query(IngestWatermark).all()
