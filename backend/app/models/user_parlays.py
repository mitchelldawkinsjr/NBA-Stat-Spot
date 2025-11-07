"""
User Parlay Tracking Model - Tracks parlay bets made by users
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class UserParlay(Base):
    __tablename__ = "user_parlays"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Parlay details
    name = Column(String, nullable=True)  # Optional name for the parlay
    game_date = Column(Date, index=True, nullable=False)
    
    # Betting details
    total_amount = Column(Float)  # Total wager amount
    total_odds = Column(String)  # Combined odds (e.g., "+450")
    total_payout = Column(Float)  # Potential/actual payout
    
    # System recommendation at time of bet
    system_confidence = Column(Float)  # 0-100 (aggregate confidence)
    leg_count = Column(Integer, nullable=False, default=0)  # Number of legs
    
    # Result tracking
    result = Column(String, index=True, default="pending")  # 'pending', 'won', 'lost', 'push', 'void'
    notes = Column(Text)  # Optional notes
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    settled_at = Column(DateTime)  # When parlay was marked as settled
    
    # Relationship to legs
    legs = relationship("UserParlayLeg", back_populates="parlay", cascade="all, delete-orphan")


class UserParlayLeg(Base):
    __tablename__ = "user_parlay_legs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    parlay_id = Column(Integer, ForeignKey("user_parlays.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Bet details (same as single bet)
    player_id = Column(Integer, index=True, nullable=False)
    player_name = Column(String, nullable=False)
    prop_type = Column(String, index=True, nullable=False)  # PTS, REB, AST, 3PM, PRA
    line_value = Column(Float, nullable=False)
    direction = Column(String, nullable=False)  # 'over' or 'under'
    
    # System recommendation at time of bet
    system_confidence = Column(Float)  # 0-100
    system_fair_line = Column(Float)
    system_suggestion = Column(String)  # 'over' or 'under'
    system_hit_rate = Column(Float)  # 0-100 (percentage) - hit rate for the chosen direction
    
    # Individual leg result
    result = Column(String, index=True, default="pending")  # 'pending', 'won', 'lost', 'push', 'void'
    actual_value = Column(Float)  # Actual stat value from the game
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationship
    parlay = relationship("UserParlay", back_populates="legs")

