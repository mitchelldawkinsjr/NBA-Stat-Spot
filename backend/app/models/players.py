from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    position = Column(String)
    team_id = Column(Integer, ForeignKey("teams.id"))
    jersey_number = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    team = relationship("Team", backref="players")
    game_stats = relationship("PlayerGameStat", backref="player")
    prop_suggestions = relationship("PropSuggestion", backref="player")
