from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.sql import func
from ..database import Base

class PropSuggestion(Base):
    __tablename__ = "prop_suggestions"

    id = Column(String, primary_key=True)  # UUID string
    player_id = Column(Integer, ForeignKey("players.id"), index=True, nullable=False)
    game_date = Column(Date, index=True)
    prop_type = Column(String, index=True)  # points, rebounds, assists, etc.
    line_value = Column(Float)
    suggestion = Column(String)  # over, under
    confidence_score = Column(Float)  # 0-100
    rationale = Column(JSON)
    historical_hit_rate = Column(Float)
    recent_form = Column(JSON)
    matchup_advantage = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
