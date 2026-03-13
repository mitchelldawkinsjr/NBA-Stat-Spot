"""
Prediction Accuracy Models - Store and settle game predictions and AI pick-of-the-day for historical accuracy tracking.
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, Text, Index
from sqlalchemy.sql import func
from ..database import Base


class GamePredictionRecord(Base):
    """One record per game we predicted. Filled at prediction time; actual_winner and correct set when settled."""
    __tablename__ = "game_prediction_records"
    __table_args__ = (
        Index("idx_game_pred_record_date", "record_date"),
        Index("idx_game_pred_settled", "correct"),
        Index("idx_game_pred_status", "actual_winner_abbr"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_date = Column(Date, nullable=False, index=True)
    game_id = Column(String(32), nullable=False, index=True)  # ESPN event id
    home_abbr = Column(String(8), nullable=False)
    away_abbr = Column(String(8), nullable=False)
    predicted_winner_abbr = Column(String(8), nullable=False)
    win_probability_home = Column(Float)
    win_probability_away = Column(Float)
    # Confidence: win prob of predicted winner (for filtering/display)
    confidence_pct = Column(Float, nullable=True)
    # Supporting insight/reasoning at prediction time
    insight_summary = Column(Text, nullable=True)
    # Settled after game completes
    actual_winner_abbr = Column(String(8), nullable=True)
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    correct = Column(Boolean, nullable=True)  # True = we predicted the winner correctly
    created_at = Column(DateTime, server_default=func.now())
    settled_at = Column(DateTime, nullable=True)


class PickOfTheDayRecord(Base):
    """One record per day for the AI pick of the day. actual_value and hit set when settled."""
    __tablename__ = "pick_of_the_day_records"
    __table_args__ = (Index("idx_pick_record_date", "record_date"),)

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_date = Column(Date, nullable=False, index=True)
    player_id = Column(Integer, nullable=False, index=True)
    player_name = Column(String(128), nullable=False)
    stat_type = Column(String(8), nullable=False)  # PTS, REB, AST, 3PM
    line_value = Column(Float, nullable=False)
    suggestion = Column(String(8), nullable=False)  # over, under
    confidence = Column(Float, nullable=True)
    # Settled after game
    actual_value = Column(Float, nullable=True)
    hit = Column(Boolean, nullable=True)  # True = over hit when suggestion was over, etc.
    push = Column(Boolean, nullable=True, default=False)  # actual == line
    created_at = Column(DateTime, server_default=func.now())
    settled_at = Column(DateTime, nullable=True)


class PropPredictionRecord(Base):
    """One record per generated prop pick (for self-improving pipeline). Settled with actual_value and error."""
    __tablename__ = "prop_prediction_records"
    __table_args__ = (
        Index("idx_prop_pred_date", "record_date"),
        Index("idx_prop_pred_settled", "actual_value"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_date = Column(Date, nullable=False, index=True)
    player_id = Column(Integer, nullable=False, index=True)
    player_name = Column(String(128), nullable=True)
    stat_type = Column(String(16), nullable=False)
    line_value = Column(Float, nullable=False)
    direction = Column(String(8), nullable=False)
    confidence = Column(Float, nullable=True)
    predicted_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    error = Column(Float, nullable=True)
    model_version = Column(String(64), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    settled_at = Column(DateTime, nullable=True)
