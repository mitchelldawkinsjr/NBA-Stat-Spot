"""Precomputed hit rates vs a line for a player/stat/window."""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.sql import func

from ..database import Base


class PlayerLineHitRate(Base):
    __tablename__ = "player_line_hit_rates"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "season",
            "stat_type",
            "line",
            "direction",
            "window",
            name="uq_player_line_hit_rates",
        ),
        Index("idx_plhr_player_season", "player_id", "season"),
        Index("idx_plhr_stat_line", "stat_type", "line"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    season = Column(String(10), nullable=False, index=True)
    stat_type = Column(String(16), nullable=False)
    line = Column(Float, nullable=False)
    direction = Column(String(8), nullable=False)  # over|under
    window = Column(String(16), nullable=False)  # l5|l10|l20|season
    hit_rate = Column(Float, nullable=True)
    hits = Column(Integer, nullable=True)
    total = Column(Integer, nullable=True)
    formula_version = Column(String(32), nullable=False, default="v1-stats-calculator")
    computed_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
