"""
Player Context Model - Stores contextual information about players for AI predictions
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from ..database import Base


class PlayerContext(Base):
    __tablename__ = "player_contexts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    player_id = Column(Integer, index=True, nullable=False)
    game_date = Column(Date, index=True, nullable=False)
    
    # ESPN identifiers
    espn_team_slug = Column(String, nullable=True)
    espn_player_id = Column(String, nullable=True)
    
    # Injury and availability
    is_injured = Column(Boolean, default=False)
    injury_status = Column(String, nullable=True)  # "probable", "questionable", "doubtful", "out"
    injury_description = Column(Text, nullable=True)
    injury_date = Column(Date, nullable=True)  # Date of injury
    rest_days = Column(Integer, nullable=True)  # Days since last game
    
    # Matchup context
    opponent_team_id = Column(Integer, nullable=True)
    opponent_team_abbr = Column(String, nullable=True)
    is_home_game = Column(Boolean, default=True)
    
    # Team performance context
    team_win_rate = Column(Float, nullable=True)  # Team's recent win rate
    opponent_win_rate = Column(Float, nullable=True)  # Opponent's recent win rate
    team_conference_rank = Column(Integer, nullable=True)  # Conference rank
    opponent_conference_rank = Column(Integer, nullable=True)  # Opponent conference rank
    team_recent_form = Column(Float, nullable=True)  # Last 10 games win %
    playoff_race_pressure = Column(Float, nullable=True)  # 0-1 score for playoff race pressure
    
    # Defensive/Offensive rankings
    opponent_def_rank_pts = Column(Integer, nullable=True)  # Opponent's defensive rank for points
    opponent_def_rank_reb = Column(Integer, nullable=True)
    opponent_def_rank_ast = Column(Integer, nullable=True)
    
    # Historical matchup performance
    h2h_avg_pts = Column(Float, nullable=True)  # Head-to-head average points
    h2h_avg_reb = Column(Float, nullable=True)
    h2h_avg_ast = Column(Float, nullable=True)
    h2h_games_played = Column(Integer, default=0)
    
    # Minutes and usage
    projected_minutes = Column(Float, nullable=True)
    usage_rate = Column(Float, nullable=True)
    
    # News and transaction context
    news_sentiment = Column(Float, nullable=True)  # -1 to 1 sentiment score
    has_recent_transaction = Column(Boolean, default=False)  # Recent trade/signing
    
    # Additional context (JSON for flexibility)
    additional_context = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

