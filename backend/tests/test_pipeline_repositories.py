"""Pipeline repository upsert idempotency."""
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.pipeline.repositories import games_repo, player_stats_repo


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_upsert_game_idempotent():
    db = _session()
    d = date(2026, 3, 15)
    payload = {
        "game_id": "0022500123",
        "game_date": d,
        "season": "2025-26",
        "home_team_abbr": "LAL",
        "away_team_abbr": "BOS",
        "home_score": 110,
        "away_score": 105,
        "status": "FINAL",
        "source": "test",
    }
    games_repo.upsert_game(db, payload)
    games_repo.upsert_game(db, {**payload, "home_score": 112})
    db.commit()
    from app.models.games import Game

    row = db.query(Game).filter_by(game_id="0022500123").first()
    assert row is not None
    assert row.home_score == 112


def test_upsert_player_stat_idempotent():
    db = _session()
    d = date(2026, 3, 15)
    games_repo.upsert_game(
        db,
        {
            "game_id": "g1",
            "game_date": d,
            "season": "2025-26",
            "home_team_abbr": "LAL",
            "away_team_abbr": "BOS",
            "status": "FINAL",
        },
    )
    player_stats_repo.upsert_player_game_stat(
        db,
        player_id=2544,
        game_id="g1",
        game_date=d,
        season="2025-26",
        stats={"pts": 25, "reb": 8, "ast": 10},
    )
    player_stats_repo.upsert_player_game_stat(
        db,
        player_id=2544,
        game_id="g1",
        game_date=d,
        season="2025-26",
        stats={"pts": 30, "reb": 8, "ast": 10},
    )
    db.commit()
    from app.models.player_game_stats import PlayerGameStat

    row = db.query(PlayerGameStat).filter_by(player_id=2544, game_id="g1").first()
    assert row.points == 30
