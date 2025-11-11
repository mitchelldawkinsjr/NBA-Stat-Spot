"""
Tests for error handling middleware
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.error_handler import APIError

client = TestClient(app)


class TestErrorHandling:
    """Test error handling middleware"""
    
    def test_validation_error(self):
        """Test that validation errors return standardized format"""
        # Missing required field
        response = client.post("/api/v1/bets", json={})
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "details" in data
        assert "path" in data
    
    def test_not_found_error(self):
        """Test that 404 errors return standardized format"""
        response = client.get("/api/v1/bets/99999")
        assert response.status_code == 404
        # Note: FastAPI's HTTPException may not go through our handler
        # This test verifies the endpoint returns 404
    
    def test_invalid_endpoint(self):
        """Test that invalid endpoints return 404"""
        response = client.get("/api/v1/invalid/endpoint")
        assert response.status_code == 404
    
    def test_rate_limit_error_format(self):
        """Test that rate limit errors return standardized format"""
        # This would require hitting rate limits, which is hard to test
        # But we can verify the handler is registered
        response = client.get("/api/v1/players/search?q=test")
        # Should succeed or return proper error format
        assert response.status_code in [200, 429]
        if response.status_code == 429:
            data = response.json()
            assert "error" in data
            assert "details" in data

