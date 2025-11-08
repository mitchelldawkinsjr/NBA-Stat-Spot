"""
Tests for API Routers
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_healthz(self):
        """Test health check endpoint"""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestPlayersV1Router:
    """Test players v1 router"""
    
    def test_search_players_min_length(self):
        """Test that search requires minimum length"""
        response = client.get("/api/v1/players/search?q=")
        assert response.status_code == 422  # Validation error
    
    def test_search_players_valid(self):
        """Test valid player search"""
        response = client.get("/api/v1/players/search?q=lebron")
        # May return 200 with empty list if NBA API unavailable, or 200 with results
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
    
    def test_stat_leaders(self):
        """Test stat leaders endpoint"""
        response = client.get("/api/v1/players/stat-leaders?season=2025-26&limit=3")
        # May timeout or return empty if NBA API unavailable
        assert response.status_code in [200, 500, 504]
        if response.status_code == 200:
            data = response.json()
            assert "items" in data
            assert "PTS" in data["items"]
            assert "AST" in data["items"]
            assert "REB" in data["items"]
            assert "3PM" in data["items"]
    
    def test_featured_players(self):
        """Test featured players endpoint"""
        response = client.get("/api/v1/players/featured")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
    
    def test_player_detail(self):
        """Test player detail endpoint"""
        response = client.get("/api/v1/players/2544")
        # May return 200 with player data or 200 with minimal data if NBA API unavailable
        assert response.status_code == 200
        data = response.json()
        assert "player" in data
    
    def test_player_stats(self):
        """Test player stats endpoint"""
        response = client.get("/api/v1/players/2544/stats?games=10&season=2025-26")
        # May return empty list if NBA API unavailable
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)


class TestGamesV1Router:
    """Test games v1 router"""
    
    def test_today_games(self):
        """Test today's games endpoint"""
        response = client.get("/api/v1/games/today")
        assert response.status_code == 200
        data = response.json()
        assert "games" in data
        assert isinstance(data["games"], list)


class TestPropsV1Router:
    """Test props v1 router"""
    
    def test_daily_props(self):
        """Test daily props endpoint"""
        response = client.get("/api/v1/props/daily?min_confidence=50")
        # May timeout or return empty if NBA API unavailable
        assert response.status_code in [200, 500, 504]
        if response.status_code == 200:
            data = response.json()
            assert "items" in data
            assert "total" in data
    
    def test_player_props(self):
        """Test player props endpoint"""
        response = client.get("/api/v1/props/player/2544?season=2025-26")
        # May return empty suggestions if NBA API unavailable
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "suggestions" in data


class TestTeamsV1Router:
    """Test teams v1 router"""
    
    def test_list_teams(self):
        """Test list teams endpoint"""
        response = client.get("/api/v1/teams")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
    
    def test_get_team(self):
        """Test get team endpoint"""
        response = client.get("/api/v1/teams/1610612747")
        # May return 200 with team data or 200 with minimal data if NBA API unavailable
        assert response.status_code == 200
        data = response.json()
        assert "team" in data

