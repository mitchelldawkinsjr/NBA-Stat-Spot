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


def test_upsert_player_stat_keeps_defensive_stats_when_feed_omits_them():
    from app.models.player_game_stats import PlayerGameStat

    db = _session()
    d = date(2026, 3, 15)
    kwargs = dict(player_id=2544, game_id="g1", game_date=d, season="2025-26")
    player_stats_repo.upsert_player_game_stat(
        db, **kwargs, stats={"pts": 25, "stl": 3, "blk": 2, "tov": 4}
    )
    player_stats_repo.upsert_player_game_stat(db, **kwargs, stats={"pts": 26})
    row = db.query(PlayerGameStat).filter_by(player_id=2544, game_id="g1").first()
    assert (row.points, row.steals, row.blocks, row.turnovers) == (26, 3, 2, 4)


def _log_row(game_id, game_date, pts, matchup="LAL vs. BOS"):
    return {"game_id": game_id, "game_date": game_date, "matchup": matchup, "pts": pts, "reb": 5, "ast": 5}


def test_merge_game_into_log_cache_keeps_other_games():
    from app.models.player_game_log_cache import PlayerGameLogCache

    db = _session()
    player_stats_repo.sync_player_game_log_cache(
        db,
        player_id=1,
        season="2025-26",
        logs=[_log_row("a", "2026-03-01", 10), _log_row("b", "2026-03-03", 12)],
    )
    player_stats_repo.merge_game_into_log_cache(
        db, player_id=1, season="2025-26", row=_log_row("c", "2026-03-05", 30, "LAL @ MIA")
    )
    player_stats_repo.merge_game_into_log_cache(
        db, player_id=1, season="2025-26", row=_log_row("b", "2026-03-03", 14)
    )
    rows = {r.game_id: r for r in db.query(PlayerGameLogCache).filter_by(player_id=1).all()}
    assert sorted(rows) == ["a", "b", "c"]
    assert rows["a"].matchup == "LAL vs. BOS"
    assert rows["b"].pts == 14
    assert rows["c"].pts == 30


def test_parse_boxscore_players_reads_each_player_and_defensive_stats(monkeypatch):
    from app.pipeline.jobs import ingest_boxscores

    monkeypatch.setattr(
        ingest_boxscores,
        "match_espn_athlete",
        lambda athlete, team_abbr, index: int(athlete["id"]),
    )
    keys = ["minutes", "points", "rebounds", "assists", "steals", "blocks", "turnovers",
            "threePointFieldGoalsMade-threePointFieldGoalsAttempted"]
    summary = {
        "boxscore": {
            "players": [
                {
                    "team": {"abbreviation": "LAL"},
                    "statistics": [{
                        "keys": keys,
                        "athletes": [
                            {"athlete": {"id": "1"}, "stats": ["34", "28", "7", "9", "2", "1", "3", "4-9"]},
                            {"athlete": {"id": "2"}, "stats": ["30", "11", "12", "1", "0", "3", "1", "0-1"]},
                        ],
                    }],
                }
            ]
        }
    }
    players = {p["player_id"]: p for p in ingest_boxscores._parse_boxscore_players(summary, {})}
    assert players[1]["pts"] == 28 and players[2]["pts"] == 11
    assert (players[1]["stl"], players[1]["blk"], players[1]["tov"], players[1]["tpm"]) == (2, 1, 3, 4)

    row = ingest_boxscores.log_cache_row(
        players[1], game_id="g1", game_date=date(2026, 3, 5), home_abbr="BOS", away_abbr="LAL"
    )
    assert row["matchup"] == "LAL @ BOS"
