"""Players who appeared in a game (from box score ingest)."""
from sqlalchemy import Column, String, Integer, UniqueConstraint, Index
from ..database import Base


class GameParticipant(Base):
    __tablename__ = "game_participants"
    __table_args__ = (
        UniqueConstraint("game_id", "player_id", name="uq_game_participant"),
        Index("idx_game_participants_game", "game_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String(32), nullable=False)
    player_id = Column(Integer, nullable=False, index=True)
