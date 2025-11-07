"""
User Bet Tracking Model - Tracks bets made by users based on system recommendations
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, Text
from sqlalchemy.sql import func
from ..database import Base


class UserBet(Base):
    __tablename__ = "user_bets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Bet details
    player_id = Column(Integer, index=True, nullable=False)
    player_name = Column(String, nullable=False)
    prop_type = Column(String, index=True, nullable=False)  # PTS, REB, AST, 3PM, PRA
    line_value = Column(Float, nullable=False)
    direction = Column(String, nullable=False)  # 'over' or 'under'
    game_date = Column(Date, index=True, nullable=False)
    
    # System recommendation at time of bet
    system_confidence = Column(Float)  # 0-100
    system_fair_line = Column(Float)
    system_suggestion = Column(String)  # 'over' or 'under'
    
    # Bet details
    amount = Column(Float)  # Optional bet amount
    odds = Column(String)  # Optional odds (e.g., "-110")
    notes = Column(Text)  # Optional notes
    
    # Result tracking
    result = Column(String, index=True)  # 'pending', 'won', 'lost', 'push', 'void'
    actual_value = Column(Float)  # Actual stat value from the game
    payout = Column(Float)  # Actual payout amount
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    settled_at = Column(DateTime)  # When bet was marked as settled

