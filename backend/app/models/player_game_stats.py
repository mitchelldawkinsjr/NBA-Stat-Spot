from sqlalchemy import Column, Integer, String, Date, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from ..database import Base

class PlayerGameStat(Base):
    __tablename__ = "player_game_stats"

    id = Column(String, primary_key=True)  # UUID string
    player_id = Column(Integer, ForeignKey("players.id"), index=True, nullable=False)
    game_id = Column(String, index=True, nullable=False)
    game_date = Column(Date, index=True)
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
    created_at = Column(DateTime, server_default=func.now())
