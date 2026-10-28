"""Top Picks served from stored evaluations must still be written to accuracy history."""


class _DB:
    def close(self):
        return None


class _Reader:
    @staticmethod
    def count_prop_evaluations(db, game_date):
        return 1

    @staticmethod
    def list_prop_evaluations(db, game_date, min_confidence=None, limit=12):
        return [
            {
                "playerId": 7,
                "playerName": "Stored Pick",
                "type": "PTS",
                "marketLine": 18.5,
                "suggestion": "over",
                "confidence": 71.0,
            }
        ]


def test_precomputed_top_picks_are_recorded(monkeypatch):
    from app.services.best_picks_service import BestPicksService

    recorded = []
    monkeypatch.setattr("app.database.SessionLocal", lambda: _DB())
    monkeypatch.setattr("app.services.aggregate_stats_reader.AggregateStatsReader", _Reader)
    monkeypatch.setattr(
        "app.services.best_picks_service.record_prop_predictions",
        lambda target, picks: recorded.append((target.isoformat(), picks)) or len(picks),
    )

    out = BestPicksService.get_top_picks(date="2026-10-27", season="2026-27")

    assert out["source"] == "player_prop_evaluations"
    assert out["returned"] == 1
    assert recorded[0][0] == "2026-10-27"
    assert recorded[0][1][0]["playerId"] == 7
    assert recorded[0][1][0]["type"] == "PTS"
