"""
PlayerGameLogCache — persisted copy of fetch_player_game_log results.

Used as a Redis fallback so rank computations and player-detail pages never
need to hit the external NBA/ESPN APIs when Redis is cold (e.g. after a
container restart or cache clear).

Unique key: (player_id, game_id) — upsert-safe.
Index: (player_id, season) — primary read path.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint, Index
from sqlalchemy.sql import func
from ..database import Base


class PlayerGameLogCache(Base):
    __tablename__ = "player_game_log_cache"
    __table_args__ = (
        UniqueConstraint("player_id", "game_id", name="uq_pglc_player_game"),
        Index("idx_pglc_player_season", "player_id", "season"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, nullable=False, index=True)
    season = Column(String(10), nullable=False)
    game_id = Column(String(32), nullable=False)
    game_date = Column(String(16), nullable=False)
    matchup = Column(String(32), nullable=False, default="")
    pts = Column(Float, nullable=False, default=0.0)
    reb = Column(Float, nullable=False, default=0.0)
    ast = Column(Float, nullable=False, default=0.0)
    tpm = Column(Float, nullable=False, default=0.0)
    minutes = Column(Float, nullable=False, default=0.0)
    fga = Column(Float, nullable=False, default=0.0)
    fta = Column(Float, nullable=False, default=0.0)
    tov = Column(Float, nullable=False, default=0.0)
    oreb = Column(Float, nullable=False, default=0.0)
    stl = Column(Float, nullable=False, default=0.0)
    blk = Column(Float, nullable=False, default=0.0)
    fetched_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            "game_id": self.game_id,
            "game_date": self.game_date,
            "matchup": self.matchup,
            "pts": self.pts,
            "reb": self.reb,
            "ast": self.ast,
            "tpm": self.tpm,
            "minutes": self.minutes,
            "fga": self.fga,
            "fta": self.fta,
            "tov": self.tov,
            "oreb": self.oreb,
            "stl": self.stl,
            "blk": self.blk,
        }
