"""
Tests for Bets V1 Router
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from datetime import date, datetime

client = TestClient(app)


class TestBetsV1Router:
    """Test bets v1 router"""
    
    def test_list_bets_empty(self):
        """Test listing bets when none exist"""
        response = client.get("/api/v1/bets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_bets_with_filters(self):
        """Test listing bets with filters"""
        response = client.get("/api/v1/bets?result=pending&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_bet(self):
        """Test creating a bet"""
        bet_data = {
            "player_id": 2544,
            "player_name": "LeBron James",
            "prop_type": "PTS",
            "line_value": 25.5,
            "direction": "over",
            "game_date": "2025-01-15",
            "system_confidence": 75.0,
            "system_fair_line": 26.0,
            "system_suggestion": "over"
        }
        response = client.post("/api/v1/bets", json=bet_data)
        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 2544
        assert data["prop_type"] == "PTS"
        assert data["result"] == "pending"
    
    def test_create_bet_invalid_date(self):
        """Test creating a bet with invalid date format"""
        bet_data = {
            "player_id": 2544,
            "player_name": "LeBron James",
            "prop_type": "PTS",
            "line_value": 25.5,
            "direction": "over",
            "game_date": "invalid-date"
        }
        response = client.post("/api/v1/bets", json=bet_data)
        assert response.status_code == 400
    
    def test_get_bet_stats(self):
        """Test getting bet statistics"""
        response = client.get("/api/v1/bets/stats")
        assert response.status_code == 200
        data = response.json()
        assert "overall" in data
        assert "system_accuracy" in data
        assert "by_prop_type" in data
        assert "by_confidence" in data
        assert "pending" in data
    
    def test_update_bet(self):
        """Test updating a bet"""
        # First create a bet
        bet_data = {
            "player_id": 2544,
            "player_name": "LeBron James",
            "prop_type": "PTS",
            "line_value": 25.5,
            "direction": "over",
            "game_date": "2025-01-15"
        }
        create_response = client.post("/api/v1/bets", json=bet_data)
        assert create_response.status_code == 200
        bet_id = create_response.json()["id"]
        
        # Update the bet
        update_data = {
            "result": "won",
            "actual_value": 28.0,
            "payout": 100.0
        }
        response = client.patch(f"/api/v1/bets/{bet_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "won"
        assert data["actual_value"] == 28.0
    
    def test_update_bet_invalid_result(self):
        """Test updating a bet with invalid result"""
        # First create a bet
        bet_data = {
            "player_id": 2544,
            "player_name": "LeBron James",
            "prop_type": "PTS",
            "line_value": 25.5,
            "direction": "over",
            "game_date": "2025-01-15"
        }
        create_response = client.post("/api/v1/bets", json=bet_data)
        bet_id = create_response.json()["id"]
        
        # Try to update with invalid result
        update_data = {"result": "invalid"}
        response = client.patch(f"/api/v1/bets/{bet_id}", json=update_data)
        assert response.status_code == 400
    
    def test_get_bet_not_found(self):
        """Test getting a bet that doesn't exist"""
        response = client.get("/api/v1/bets/99999")
        assert response.status_code == 404
    
    def test_delete_bet(self):
        """Test deleting a bet"""
        # First create a bet
        bet_data = {
            "player_id": 2544,
            "player_name": "LeBron James",
            "prop_type": "PTS",
            "line_value": 25.5,
            "direction": "over",
            "game_date": "2025-01-15"
        }
        create_response = client.post("/api/v1/bets", json=bet_data)
        bet_id = create_response.json()["id"]
        
        # Delete the bet
        response = client.delete(f"/api/v1/bets/{bet_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
        
        # Verify it's deleted
        get_response = client.get(f"/api/v1/bets/{bet_id}")
        assert get_response.status_code == 404

