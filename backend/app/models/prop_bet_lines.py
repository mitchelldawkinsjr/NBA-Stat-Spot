from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from ..database import Base

class PropBetLine(Base):
    __tablename__ = "prop_bet_lines"

    id = Column(String, primary_key=True)  # UUID string
    player_id = Column(Integer, ForeignKey("players.id"), index=True, nullable=False)
    game_date = Column(Date, index=True)
    prop_type = Column(String)
    line_value = Column(Float)
    over_odds = Column(Float)
    under_odds = Column(Float)
    source = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
