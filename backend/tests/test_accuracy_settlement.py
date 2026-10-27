from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.prediction_accuracy import PickOfTheDayRecord, PropPredictionRecord
from app.services import accuracy_tracking_service as ats


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_pick_of_day_settles_with_date_offset(monkeypatch):
    db = _session()
    db.add(
        PickOfTheDayRecord(
            record_date=date(2026, 1, 10),
            player_id=1,
            player_name="Test Player",
            stat_type="PTS",
            line_value=20.5,
            suggestion="over",
            confidence=80.0,
        )
    )
    db.commit()

    monkeypatch.setattr(ats, "_get_db", lambda: db)
    monkeypatch.setattr(
        ats.NBADataService,
        "fetch_player_game_log",
        lambda player_id, season: [{"game_date": "2026-01-11", "pts": 25}],
    )

    out = ats.settle_pick_of_the_day(date(2026, 1, 10), season="2025-26")
    assert out["settled"] is True

    row = db.query(PickOfTheDayRecord).first()
    assert row.actual_value == 25
    assert row.hit is True


def test_top_picks_settle_with_date_offset(monkeypatch):
    db = _session()
    db.add(
        PropPredictionRecord(
            record_date=date(2026, 1, 10),
            player_id=2,
            player_name="Top Pick Player",
            stat_type="REB",
            line_value=8.5,
            direction="over",
            confidence=70.0,
            predicted_value=9.0,
        )
    )
    db.commit()

    monkeypatch.setattr(ats, "_get_db", lambda: db)
    monkeypatch.setattr(
        ats.NBADataService,
        "fetch_player_game_log",
        lambda player_id, season: [{"GAME_DATE": "2026-01-09", "reb": 11}],
    )

    out = ats.settle_top_picks_for_date(date(2026, 1, 10), season="2025-26")
    assert out["settled"] == 1
    assert out["not_found"] == 0

    row = db.query(PropPredictionRecord).first()
    assert row.actual_value == 11


def test_settle_all_updates_accuracy_history_components(monkeypatch):
    db = _session()
    db.add(
        PickOfTheDayRecord(
            record_date=date(2026, 1, 10),
            player_id=3,
            player_name="History Player",
            stat_type="PTS",
            line_value=19.5,
            suggestion="over",
            confidence=75.0,
        )
    )
    db.add(
        PropPredictionRecord(
            record_date=date(2026, 1, 10),
            player_id=4,
            player_name="History Top",
            stat_type="AST",
            line_value=5.5,
            direction="over",
            confidence=68.0,
            predicted_value=6.0,
        )
    )
    db.commit()

    monkeypatch.setattr(ats, "_get_db", lambda: db)
    monkeypatch.setattr(
        ats,
        "settle_game_predictions",
        lambda target_date: {"settled": 0, "not_found": 0, "errors": []},
    )
    monkeypatch.setattr(
        ats.NBADataService,
        "fetch_player_game_log",
        lambda player_id, season: [{"game_date": "2026-01-10", "pts": 22, "ast": 7}],
    )

    out = ats.settle_all_for_date(date(2026, 1, 10), season="2025-26")
    assert out["pick_of_the_day"]["settled"] is True
    assert out["top_picks"]["settled"] == 1

    hist = ats.get_accuracy_history(from_date=date(2026, 1, 10), to_date=date(2026, 1, 10))
    assert hist["pick_of_the_day"]["settled"] == 1
    assert hist["top_picks"]["overall"]["settled"] == 1


def test_settle_open_predictions_processes_backlog_dates(monkeypatch):
    db = _session()
    db.add(
        PickOfTheDayRecord(
            record_date=date(2026, 1, 9),
            player_id=7,
            player_name="Backlog Player",
            stat_type="PTS",
            line_value=21.5,
            suggestion="over",
            confidence=73.0,
        )
    )
    db.add(
        PickOfTheDayRecord(
            record_date=date(2026, 1, 10),
            player_id=8,
            player_name="Backlog Player 2",
            stat_type="PTS",
            line_value=19.5,
            suggestion="over",
            confidence=76.0,
        )
    )
    db.commit()

    monkeypatch.setattr(ats, "_get_db", lambda: db)
    monkeypatch.setattr(
        ats,
        "settle_all_for_date",
        lambda d, season=None, stats_provider=None: {
            "date": d.isoformat(),
            "pick_of_the_day": {"settled": True},
        },
    )

    out = ats.settle_open_predictions(date(2026, 1, 10), season="2025-26")
    assert out["count_dates"] == 2
    assert out["dates_processed"] == ["2026-01-09", "2026-01-10"]


class _SeasonLogs:
    """Returns a game only for the season the pick was actually played in."""

    def __init__(self):
        self.seasons = []

    def fetch_player_game_log(self, player_id, season):
        self.seasons.append(season)
        if season == "2025-26":
            return [{"game_date": "JAN 10, 2026", "pts": 0, "reb": 4, "ast": 2}]
        return [{"game_date": "OCT 22, 2026", "pts": 30}]


def test_pick_settles_against_its_own_season_not_current(monkeypatch):
    db = _session()
    db.add(
        PickOfTheDayRecord(
            record_date=date(2026, 1, 10),
            player_id=11,
            player_name="Last Season Player",
            stat_type="PTS",
            line_value=12.5,
            suggestion="under",
            confidence=71.0,
        )
    )
    db.commit()

    logs = _SeasonLogs()
    monkeypatch.setattr(ats, "_get_db", lambda: db)

    out = ats.settle_pick_of_the_day(
        date(2026, 1, 10), season="2026-27", stats_provider=logs
    )
    assert out["settled"] is True
    assert out["actual_value"] == 0
    assert out["hit"] is True
    assert "2025-26" in logs.seasons
    assert logs.seasons[0] == "2025-26"

    row = db.query(PickOfTheDayRecord).first()
    assert row.actual_value == 0
    assert row.hit is True


def test_pick_uses_live_log_when_stored_log_omits_the_game(monkeypatch):
    db = _session()
    db.add(
        PickOfTheDayRecord(
            record_date=date(2026, 1, 10),
            player_id=15,
            player_name="Missing Box Player",
            stat_type="PTS",
            line_value=18.5,
            suggestion="over",
            confidence=74.0,
        )
    )
    db.commit()

    class _PartialDb:
        def fetch_player_game_log(self, player_id, season):
            return [{"game_date": "2026-01-01", "pts": 10}]

    monkeypatch.setattr(ats, "_get_db", lambda: db)
    monkeypatch.setattr(
        ats.NBADataService,
        "fetch_player_game_log",
        lambda player_id, season: [{"game_date": "JAN 10, 2026", "pts": 24}],
    )

    out = ats.settle_pick_of_the_day(
        date(2026, 1, 10), season="2026-27", stats_provider=_PartialDb()
    )
    assert out["settled"] is True
    assert out["actual_value"] == 24
    assert out["hit"] is True


def test_nba_month_date_matches_record_date():
    row, reason = ats._find_game_log_row_for_record_date(
        [{"game_date": "OCT 26, 2025", "pts": 18}],
        date(2025, 10, 26),
    )
    assert reason == "exact_date_match"
    assert row["pts"] == 18
