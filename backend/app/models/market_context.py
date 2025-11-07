"""
Market Context Model - Stores betting market data for AI predictions
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from ..database import Base


class MarketContext(Base):
    __tablename__ = "market_contexts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    player_id = Column(Integer, index=True, nullable=False)
    game_date = Column(Date, index=True, nullable=False)
    prop_type = Column(String, index=True, nullable=False)  # PTS, REB, AST, 3PM, PRA
    
    # Market lines
    market_line = Column(Float, nullable=False)
    opening_line = Column(Float, nullable=True)  # Opening line for tracking movement
    line_movement = Column(Float, nullable=True)  # Change from opening line
    
    # Odds
    over_odds = Column(String, nullable=True)  # American odds format, e.g., "-110"
    under_odds = Column(String, nullable=True)
    
    # Public betting data (if available)
    public_bet_percentage_over = Column(Float, nullable=True)  # 0-100
    public_bet_percentage_under = Column(Float, nullable=True)
    
    # Sharp money indicators (if available)
    sharp_money_over = Column(Boolean, nullable=True)
    sharp_money_under = Column(Boolean, nullable=True)
    
    # Line value analysis
    fair_line = Column(Float, nullable=True)  # Our calculated fair line
    line_value = Column(Float, nullable=True)  # Difference between market and fair line
    
    # Additional market data (JSON for flexibility)
    additional_data = Column(JSON, nullable=True)
    
    # Source tracking
    source = Column(String, nullable=True)  # Which sportsbook/aggregator
    source_url = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

