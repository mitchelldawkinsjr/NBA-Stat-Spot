"""Dashboard snapshot read/write."""
from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ...models.dashboard_snapshots import DashboardSnapshot


ARTIFACT_TOP_PICKS = "top_picks"
ARTIFACT_DAILY_PROPS = "daily_props"
ARTIFACT_PICK_OF_DAY = "pick_of_the_day"
ARTIFACT_TEAM_RANKS = "team_ranks"


def next_version(db: Session, snapshot_date: date, artifact_type: str) -> int:
    v = (
        db.query(func.max(DashboardSnapshot.version))
        .filter(
            DashboardSnapshot.snapshot_date == snapshot_date,
            DashboardSnapshot.artifact_type == artifact_type,
        )
        .scalar()
    )
    return int(v or 0) + 1


def save_snapshot(
    db: Session,
    *,
    snapshot_date: date,
    artifact_type: str,
    season: str,
    payload: Dict[str, Any],
    pipeline_run_id: Optional[int],
    publish: bool,
) -> DashboardSnapshot:
    version = next_version(db, snapshot_date, artifact_type)
    row = DashboardSnapshot(
        snapshot_date=snapshot_date,
        artifact_type=artifact_type,
        season=season,
        version=version,
        payload=payload,
        is_published=publish,
        built_at=datetime.utcnow(),
        pipeline_run_id=pipeline_run_id,
    )
    db.add(row)
    if publish:
        (
            db.query(DashboardSnapshot)
            .filter(
                DashboardSnapshot.snapshot_date == snapshot_date,
                DashboardSnapshot.artifact_type == artifact_type,
                DashboardSnapshot.id != row.id,
            )
            .update({DashboardSnapshot.is_published: False}, synchronize_session=False)
        )
    db.flush()
    return row


def get_published(
    db: Session, snapshot_date: date, artifact_type: str
) -> Optional[DashboardSnapshot]:
    return (
        db.query(DashboardSnapshot)
        .filter(
            DashboardSnapshot.snapshot_date == snapshot_date,
            DashboardSnapshot.artifact_type == artifact_type,
            DashboardSnapshot.is_published.is_(True),
        )
        .order_by(DashboardSnapshot.version.desc())
        .first()
    )


def publish_latest(
    db: Session, snapshot_date: date, artifact_type: str
) -> Optional[DashboardSnapshot]:
    latest = (
        db.query(DashboardSnapshot)
        .filter(
            DashboardSnapshot.snapshot_date == snapshot_date,
            DashboardSnapshot.artifact_type == artifact_type,
        )
        .order_by(DashboardSnapshot.version.desc())
        .first()
    )
    if not latest:
        return None
    (
        db.query(DashboardSnapshot)
        .filter(
            DashboardSnapshot.snapshot_date == snapshot_date,
            DashboardSnapshot.artifact_type == artifact_type,
        )
        .update({DashboardSnapshot.is_published: False}, synchronize_session=False)
    )
    latest.is_published = True
    db.flush()
    return latest


def list_versions(
    db: Session, snapshot_date: date, artifact_type: Optional[str] = None
) -> List[DashboardSnapshot]:
    q = db.query(DashboardSnapshot).filter(DashboardSnapshot.snapshot_date == snapshot_date)
    if artifact_type:
        q = q.filter(DashboardSnapshot.artifact_type == artifact_type)
    return q.order_by(DashboardSnapshot.artifact_type, DashboardSnapshot.version.desc()).all()
