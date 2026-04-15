from app.services.game_prediction_service import _normalize_team_abbr, _get_team_key_players
from app.services import game_prediction_service as gps


class _DummyCache:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ttl=0):
        self.store[key] = value


def test_normalize_team_abbr_aliases():
    assert _normalize_team_abbr("GS") == "GSW"
    assert _normalize_team_abbr("NO") == "NOP"
    assert _normalize_team_abbr("NY") == "NYK"
    assert _normalize_team_abbr("SAS") == "SAS"


def test_team_key_players_uses_minutes_field(monkeypatch):
    cache = _DummyCache()
    monkeypatch.setattr(gps, "get_cache_service", lambda: cache)

    monkeypatch.setattr(
        gps.NBADataService,
        "fetch_all_players_including_rookies",
        lambda: [
            {"id": 1, "full_name": "Player One", "team_id": 100, "position": "G"},
            {"id": 2, "full_name": "Player Two", "team_id": 200, "position": "F"},
        ],
    )
    monkeypatch.setattr(
        gps.NBADataService,
        "fetch_player_game_log",
        lambda player_id, season: [
            {"minutes": "30:30", "pts": 20, "reb": 5, "ast": 7},
            {"minutes": "32:00", "pts": 18, "reb": 4, "ast": 6},
            {"minutes": "28:15", "pts": 22, "reb": 6, "ast": 5},
        ]
        if player_id == 1
        else [],
    )

    rows = _get_team_key_players(team_id=100, season="2025-26", limit=5)
    assert len(rows) == 1
    assert rows[0]["id"] == 1
    assert (rows[0]["avg_min"] or 0) > 12
    assert rows[0]["season_pts"] is not None

