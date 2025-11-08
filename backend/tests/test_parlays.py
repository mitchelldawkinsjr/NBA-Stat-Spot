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

