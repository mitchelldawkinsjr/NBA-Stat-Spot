"""Precomputed opponent-analysis rows (analytics agent output)."""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    Text,
)
from sqlalchemy.sql import func

from ..database import Base


class PlayerOpponentAnalysis(Base):
    __tablename__ = "player_opponent_analysis"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "opponent_team_id",
            "season",
            name="uq_player_opponent_analysis",
        ),
        Index("idx_poa_player_season", "player_id", "season"),
        Index("idx_poa_game_date", "game_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    season = Column(String(10), nullable=False, index=True)
    opponent_team_id = Column(Integer, nullable=False, index=True)
    opponent_team_abbr = Column(String(8), nullable=True)
    game_date = Column(Date, nullable=True)
    is_home_game = Column(Boolean, nullable=True)

    h2h_avg_pts = Column(Float, nullable=True)
    h2h_avg_reb = Column(Float, nullable=True)
    h2h_avg_ast = Column(Float, nullable=True)
    h2h_games_played = Column(Integer, nullable=True, default=0)

    def_rank_pts = Column(Integer, nullable=True)
    def_rank_reb = Column(Integer, nullable=True)
    def_rank_ast = Column(Integer, nullable=True)
    def_rank_3pm = Column(Integer, nullable=True)

    off_rank_pts = Column(Integer, nullable=True)
    off_rank_reb = Column(Integer, nullable=True)
    off_rank_ast = Column(Integer, nullable=True)
    off_rank_3pm = Column(Integer, nullable=True)

    position = Column(String(8), nullable=True)
    pos_def_rank_pts = Column(Integer, nullable=True)
    pos_def_rank_reb = Column(Integer, nullable=True)
    pos_def_rank_ast = Column(Integer, nullable=True)
    pos_def_rank_3pm = Column(Integer, nullable=True)

    matchup_adv_pts = Column(Float, nullable=True)
    matchup_adv_reb = Column(Float, nullable=True)
    matchup_adv_ast = Column(Float, nullable=True)
    matchup_adv_3pm = Column(Float, nullable=True)

    opponent_win_rate = Column(Float, nullable=True)
    opponent_conference_rank = Column(Integer, nullable=True)
    team_win_rate = Column(Float, nullable=True)
    team_conference_rank = Column(Integer, nullable=True)
    team_recent_form = Column(Float, nullable=True)

    rest_days = Column(Integer, nullable=True)
    is_injured = Column(Boolean, nullable=True)
    injury_status = Column(String(32), nullable=True)
    injury_description = Column(Text, nullable=True)

    formula_version = Column(String(32), nullable=False, default="v1-stats-calculator")
    computed_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
