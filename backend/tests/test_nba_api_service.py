"""
Tests for NBA API Service
"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.nba_api_service import NBADataService


class TestNBADataService:
    """Test suite for NBADataService"""
    
    def test_search_players_basic(self):
        """Test basic player search functionality"""
        with patch.object(NBADataService, 'fetch_all_players_including_rookies') as mock_fetch:
            mock_fetch.return_value = [
                {"id": 2544, "full_name": "LeBron James", "team_id": 1610612747},
                {"id": 201939, "full_name": "Stephen Curry", "team_id": 1610612744},
                {"id": 203507, "full_name": "Giannis Antetokounmpo", "team_id": 1610612749},
            ]
            
            results = NBADataService.search_players("lebron")
            
            assert len(results) == 1
            assert results[0]["id"] == 2544
            assert results[0]["name"] == "LeBron James"
            assert results[0]["team"] == 1610612747
    
    def test_search_players_case_insensitive(self):
        """Test that search is case insensitive"""
        with patch.object(NBADataService, 'fetch_all_players_including_rookies') as mock_fetch:
            mock_fetch.return_value = [
                {"id": 2544, "full_name": "LeBron James", "team_id": 1610612747},
            ]
            
            results = NBADataService.search_players("LEBRON")
            
            assert len(results) == 1
            assert results[0]["id"] == 2544
    
    def test_search_players_limit(self):
        """Test that search results are limited to 20"""
        with patch.object(NBADataService, 'fetch_all_players_including_rookies') as mock_fetch:
            # Create 25 mock players
            mock_fetch.return_value = [
                {"id": i, "full_name": f"Player {i}", "team_id": 1610612747}
                for i in range(25)
            ]
            
            results = NBADataService.search_players("Player")
            
            assert len(results) == 20
    
    def test_search_players_no_results(self):
        """Test search with no matching results"""
        with patch.object(NBADataService, 'fetch_all_players_including_rookies') as mock_fetch:
            mock_fetch.return_value = [
                {"id": 2544, "full_name": "LeBron James", "team_id": 1610612747},
            ]
            
            results = NBADataService.search_players("nonexistent")
            
            assert len(results) == 0
    
    def test_fetch_all_teams(self):
        """Test fetching all teams"""
        with patch('app.services.nba_api_service.static_teams') as mock_teams:
            mock_teams.get_teams.return_value = [
                {"id": 1610612747, "full_name": "Los Angeles Lakers"},
                {"id": 1610612744, "full_name": "Golden State Warriors"},
            ]
            
            teams = NBADataService.fetch_all_teams()
            
            assert len(teams) == 2
            assert teams[0]["full_name"] == "Los Angeles Lakers"
    
    def test_fetch_all_teams_no_module(self):
        """Test fetching teams when module is not available"""
        with patch('app.services.nba_api_service.static_teams', None):
            teams = NBADataService.fetch_all_teams()
            assert teams == []

