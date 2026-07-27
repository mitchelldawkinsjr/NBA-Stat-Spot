"""Precomputed daily prop evaluations for snappy dashboard reads."""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.sql import func

from ..database import Base


class PlayerPropEvaluation(Base):
    __tablename__ = "player_prop_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "game_date",
            "player_id",
            "stat_type",
            "line",
            "direction",
            name="uq_player_prop_evaluations",
        ),
        Index("idx_ppe_game_date", "game_date"),
        Index("idx_ppe_date_confidence", "game_date", "confidence"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_date = Column(Date, nullable=False, index=True)
    season = Column(String(10), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    player_name = Column(String(128), nullable=True)
    stat_type = Column(String(16), nullable=False)  # pts|reb|ast|tpm|pra
    display_type = Column(String(8), nullable=True)  # PTS|REB|...
    line = Column(Float, nullable=False)
    fair_line = Column(Float, nullable=True)
    market_line = Column(Float, nullable=True)
    direction = Column(String(8), nullable=False)
    suggestion = Column(String(8), nullable=True)
    confidence = Column(Float, nullable=True)
    hit_rate = Column(Float, nullable=True)
    tier = Column(String(16), nullable=True)
    is_hot = Column(Boolean, default=False)
    rationale = Column(Text, nullable=True)
    stats_json = Column(Text, nullable=True)
    confidence_source = Column(String(32), nullable=True)
    rationale_source = Column(String(32), nullable=True)
    ml_available = Column(Boolean, default=False)
    formula_version = Column(String(32), nullable=False, default="v1-stats-calculator")
    computed_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
