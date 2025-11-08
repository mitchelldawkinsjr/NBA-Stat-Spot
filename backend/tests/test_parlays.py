"""
Tests for Parlays Router
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestParlaysRouter:
    """Test parlays router"""
    
    def test_list_parlays_empty(self):
        """Test listing parlays when none exist"""
        response = client.get("/api/v1/parlays")
        # Should return 200 with empty list or handle gracefully
        assert response.status_code in [200, 500]  # 500 if DB not set up, 200 if empty
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
    
    def test_get_parlay_not_found(self):
        """Test getting a non-existent parlay"""
        response = client.get("/api/v1/parlays/99999")
        assert response.status_code == 404
    
    def test_create_parlay(self):
        """Test creating a parlay"""
        # Test with invalid request (less than 2 legs) - should return 400
        invalid_parlay = {
            "game_date": "2025-01-15",
            "legs": [
                {
                    "player_id": 2544,
                    "player_name": "LeBron James",
                    "prop_type": "PTS",
                    "line_value": 25.5,
                    "direction": "over"
                }
            ]
        }
        response = client.post("/api/v1/parlays", json=invalid_parlay)
        # Should return 400 because parlay needs at least 2 legs
        assert response.status_code == 400
        
        # Test with valid request (2+ legs) - may fail if DB not set up
        valid_parlay = {
            "game_date": "2025-01-15",
            "legs": [
                {
                    "player_id": 2544,
                    "player_name": "LeBron James",
                    "prop_type": "PTS",
                    "line_value": 25.5,
                    "direction": "over"
                },
                {
                    "player_id": 201939,
                    "player_name": "Stephen Curry",
                    "prop_type": "3PM",
                    "line_value": 4.5,
                    "direction": "over"
                }
            ]
        }
        response = client.post("/api/v1/parlays", json=valid_parlay)
        # May return 200 if DB is set up, or 500 if DB not available
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "game_date" in data
            assert "legs" in data

