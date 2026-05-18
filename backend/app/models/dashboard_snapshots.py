"""Versioned dashboard artifacts built by the pipeline."""
from sqlalchemy import Column, String, Integer, Date, DateTime, Boolean, Index, JSON
from sqlalchemy.sql import func
from ..database import Base


class DashboardSnapshot(Base):
    __tablename__ = "dashboard_snapshots"
    __table_args__ = (
        Index("idx_snapshots_date_type", "snapshot_date", "artifact_type"),
        Index("idx_snapshots_published", "snapshot_date", "artifact_type", "is_published"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(Date, nullable=False)
    artifact_type = Column(String(32), nullable=False)
    season = Column(String(10), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    payload = Column(JSON, nullable=False)
    is_published = Column(Boolean, nullable=False, default=False)
    built_at = Column(DateTime, server_default=func.now())
    pipeline_run_id = Column(Integer, nullable=True)
