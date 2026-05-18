"""Read published dashboard snapshots for API handlers."""
from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, Optional

from ..database import SessionLocal
from ..pipeline.repositories import snapshots_repo


def load_published_snapshot(
    snapshot_date: date, artifact_type: str
) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        row = snapshots_repo.get_published(db, snapshot_date, artifact_type)
        if not row:
            return None
        payload = row.payload if isinstance(row.payload, dict) else {}
        return {
            **payload,
            "_meta": {
                "source": "snapshot",
                "built_at": row.built_at.isoformat() if row.built_at else None,
                "pipeline_run_id": row.pipeline_run_id,
                "version": row.version,
                "artifact_type": artifact_type,
            },
        }
    finally:
        db.close()


def home_dashboard_payload(target_date: date) -> Optional[Dict[str, Any]]:
    top = load_published_snapshot(target_date, snapshots_repo.ARTIFACT_TOP_PICKS)
    daily = load_published_snapshot(target_date, snapshots_repo.ARTIFACT_DAILY_PROPS)
    pick = load_published_snapshot(target_date, snapshots_repo.ARTIFACT_PICK_OF_DAY)
    if not top and not daily and not pick:
        return None
    built = None
    run_id = None
    for block in (top, daily, pick):
        if block and block.get("_meta"):
            built = block["_meta"].get("built_at") or built
            run_id = block["_meta"].get("pipeline_run_id") or run_id
    return {
        "date": target_date.isoformat(),
        "top_picks": top or {"items": []},
        "daily_props": daily or {"items": []},
        "pick_of_the_day": pick or {},
        "data_as_of": built or datetime.utcnow().isoformat(),
        "pipeline_run_id": run_id,
        "source": "snapshot",
    }
