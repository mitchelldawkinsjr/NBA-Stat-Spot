from app.services.context_collector import ContextCollector
from app.services import context_collector as cc


class _DummyCache:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ttl=0):
        self.store[key] = value


class _DummyEspn:
    def get_team_schedule(self, slug):
        # Return list shape (not dict) to ensure parser supports both.
        return [
            {
                "competitions": [
                    {
                        "status": {"type": {"name": "STATUS_FINAL"}},
                        "competitors": [
                            {"team": {"abbreviation": "LAL"}, "score": "110"},
                            {"team": {"abbreviation": "BOS"}, "score": "105"},
                        ],
                    }
                ]
            },
            {
                "competitions": [
                    {
                        "status": {"type": {"name": "STATUS_FINAL"}},
                        "competitors": [
                            {"team": {"abbreviation": "LAL"}, "score": "120"},
                            {"team": {"abbreviation": "MIA"}, "score": "118"},
                        ],
                    }
                ]
            },
        ]


def test_get_team_ppg_from_player_logs_handles_schedule_list(monkeypatch):
    cache = _DummyCache()
    monkeypatch.setattr(cc, "get_cache_service", lambda: cache)
    monkeypatch.setattr(
        cc.NBADataService,
        "fetch_all_teams",
        lambda: [{"id": 1610612747, "abbreviation": "LAL"}],
    )

    monkeypatch.setattr(cc, "get_espn_service", lambda: _DummyEspn(), raising=False)
    # Function imports from module each call; patch target module function.
    import app.services.espn_api_service as espn_api_service
    monkeypatch.setattr(espn_api_service, "get_espn_service", lambda: _DummyEspn())

    out = ContextCollector._get_team_ppg_from_player_logs("2025-26")
    assert 1610612747 in out
    assert round(out[1610612747], 1) == 115.0

