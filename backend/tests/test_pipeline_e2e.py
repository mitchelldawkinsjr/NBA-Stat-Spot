"""Lightweight pipeline e2e: snapshot save/load."""
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.pipeline.repositories import snapshots_repo
from app.services.snapshot_service import load_published_snapshot


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_snapshot_publish_and_load():
    db = _session()
    d = date(2026, 5, 1)
    snapshots_repo.save_snapshot(
        db,
        snapshot_date=d,
        artifact_type=snapshots_repo.ARTIFACT_TOP_PICKS,
        season="2025-26",
        payload={"items": [{"playerName": "Test"}]},
        pipeline_run_id=None,
        publish=True,
    )
    db.commit()
    loaded = load_published_snapshot(d, snapshots_repo.ARTIFACT_TOP_PICKS)
    assert loaded is not None
    assert loaded["items"][0]["playerName"] == "Test"
    assert loaded["_meta"]["source"] == "snapshot"
