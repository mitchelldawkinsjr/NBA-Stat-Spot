from sqlalchemy import Column, Integer, String, Date, Boolean, Float, DateTime, ForeignKey, UniqueConstraint, Index, Text
from sqlalchemy.sql import func
from ..database import Base

class PlayerGameStat(Base):
    __tablename__ = "player_game_stats"
    __table_args__ = (
        UniqueConstraint("player_id", "game_id", name="uq_player_game_stats_player_game"),
        Index("idx_pgs_player_season", "player_id", "season"),
        Index("idx_pgs_season_validation", "season", "validation_status"),
    )

    id = Column(String, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), index=True, nullable=False)
    game_id = Column(String, index=True, nullable=False)
    season = Column(String(10), nullable=True, index=True)
    game_date = Column(Date, index=True)
    source = Column(String(16), nullable=True, default="espn")
    fetched_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    opponent_team_id = Column(Integer, ForeignKey("teams.id"))
    is_home = Column(Boolean, default=False)
    minutes_played = Column(Float)
    points = Column(Integer)
    rebounds = Column(Integer)
    assists = Column(Integer)
    steals = Column(Integer)
    blocks = Column(Integer)
    three_pointers_made = Column(Integer)
    field_goals_made = Column(Integer)
    field_goals_attempted = Column(Integer)
    free_throws_made = Column(Integer)
    turnovers = Column(Integer)
    validation_status = Column(String(16), nullable=False, default="valid")
    validation_failures = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
