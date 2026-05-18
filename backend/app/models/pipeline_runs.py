"""Audit trail for pipeline job executions."""
from sqlalchemy import Column, String, Integer, DateTime, JSON
from sqlalchemy.sql import func
from ..database import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(String(64), nullable=False, index=True)
    status = Column(String(16), nullable=False, default="started")
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
    stats_json = Column(JSON, nullable=True)
    error_message = Column(String(512), nullable=True)


class IngestWatermark(Base):
    __tablename__ = "ingest_watermarks"

    job_name = Column(String(64), primary_key=True)
    last_success_at = Column(DateTime, nullable=True)
    last_game_date = Column(String(16), nullable=True)
    rows_written = Column(Integer, nullable=True, default=0)
    meta_json = Column(JSON, nullable=True)
