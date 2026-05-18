"""Canonical NBA games ingested by the data pipeline."""
from sqlalchemy import Column, String, Integer, Date, DateTime, Index
from sqlalchemy.sql import func
from ..database import Base


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        Index("idx_games_date", "game_date"),
        Index("idx_games_season", "season"),
    )

    game_id = Column(String(32), primary_key=True)
    game_date = Column(Date, nullable=False, index=True)
    season = Column(String(10), nullable=False)
    home_team_abbr = Column(String(8), nullable=False, default="")
    away_team_abbr = Column(String(8), nullable=False, default="")
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    status = Column(String(16), nullable=False, default="SCHEDULED")
    source = Column(String(16), nullable=False, default="nba")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
