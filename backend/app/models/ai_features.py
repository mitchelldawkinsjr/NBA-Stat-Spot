"""
AI Feature Set Model - Stores aggregated features for ML model training and prediction
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from ..database import Base


class AIFeatureSet(Base):
    __tablename__ = "ai_feature_sets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    player_id = Column(Integer, index=True, nullable=False)
    game_date = Column(Date, index=True, nullable=False)
    prop_type = Column(String, index=True, nullable=False)  # PTS, REB, AST, 3PM, PRA
    
    # Player stat features
    rolling_avg_10 = Column(Float, nullable=True)  # 10-game rolling average
    rolling_avg_5 = Column(Float, nullable=True)  # 5-game rolling average
    season_avg = Column(Float, nullable=True)
    variance = Column(Float, nullable=True)  # Statistical variance
    trend = Column(String, nullable=True)  # "up", "down", "flat"
    momentum = Column(Float, nullable=True)  # Calculated momentum score
    
    # Context features
    rest_days = Column(Integer, nullable=True)
    is_injured = Column(Boolean, default=False)
    is_home_game = Column(Boolean, default=True)
    opponent_def_rank = Column(Integer, nullable=True)
    h2h_avg = Column(Float, nullable=True)
    
    # Market features
    market_line = Column(Float, nullable=True)
    line_movement = Column(Float, nullable=True)
    line_value = Column(Float, nullable=True)  # Market line vs fair line
    public_bet_pct = Column(Float, nullable=True)
    
    # Historical performance features
    hit_rate_over = Column(Float, nullable=True)  # Historical hit rate for over
    hit_rate_under = Column(Float, nullable=True)  # Historical hit rate for under
    hit_rate_at_line = Column(Float, nullable=True)  # Hit rate at this specific line
    
    # Team context features
    team_win_rate = Column(Float, nullable=True)
    opponent_win_rate = Column(Float, nullable=True)
    team_avg_pts = Column(Float, nullable=True)
    opponent_avg_pts_allowed = Column(Float, nullable=True)
    
    # Usage and minutes
    projected_minutes = Column(Float, nullable=True)
    usage_rate = Column(Float, nullable=True)
    minutes_consistency = Column(Float, nullable=True)  # Variance in minutes
    
    # Additional features (JSON for extensibility)
    additional_features = Column(JSON, nullable=True)
    
    # Target variable (for training)
    actual_outcome = Column(Float, nullable=True)  # Actual stat value
    hit_over = Column(Boolean, nullable=True)  # Did it hit over? (for training)
    hit_under = Column(Boolean, nullable=True)  # Did it hit under? (for training)
    
    # Model predictions (for inference)
    ml_confidence = Column(Float, nullable=True)  # ML model confidence (0-100)
    ml_predicted_line = Column(Float, nullable=True)  # ML predicted optimal line
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

