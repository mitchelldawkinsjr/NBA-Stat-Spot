"""
Tests for Parlays Router
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, engine, Base
from app.models.user_parlays import UserParlay, UserParlayLeg
from datetime import date, datetime

client = TestClient(app)


@pytest.fixture
def db_session():
    """Create a test database session"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_parlay(db_session):
    """Create a sample parlay for testing"""
    parlay = UserParlay(
        name="Test Parlay",
        game_date=date.today(),
        total_amount=100.0,
        total_odds="+450",
        total_payout=550.0,
        system_confidence=75.0,
        leg_count=2,
        result="pending"
    )
    db_session.add(parlay)
    db_session.flush()
    
    leg1 = UserParlayLeg(
        parlay_id=parlay.id,
        player_id=2544,
        player_name="LeBron James",
        prop_type="PTS",
        line_value=25.5,
        direction="over",
        system_confidence=80.0,
        system_fair_line=26.0,
        system_suggestion="over",
        system_hit_rate=75.0,
        result="pending"
    )
    leg2 = UserParlayLeg(
        parlay_id=parlay.id,
        player_id=201939,
        player_name="Stephen Curry",
        prop_type="3PM",
        line_value=4.5,
        direction="over",
        system_confidence=70.0,
        system_fair_line=5.0,
        system_suggestion="over",
        system_hit_rate=65.0,
        result="pending"
    )
    db_session.add(leg1)
    db_session.add(leg2)
    db_session.commit()
    db_session.refresh(parlay)
    
    return parlay


class TestParlaysRouter:
    """Test parlays router"""
    
    def test_list_parlays_empty(self):
        """Test listing parlays when none exist"""
        response = client.get("/api/v1/parlays")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_parlay(self):
        """Test creating a parlay"""
        parlay_data = {
            "name": "Test Parlay",
            "game_date": date.today().isoformat(),
            "total_amount": 100.0,
            "total_odds": "+450",
            "total_payout": 550.0,
            "notes": "Test notes",
            "legs": [
                {
                    "player_id": 2544,
                    "player_name": "LeBron James",
                    "prop_type": "PTS",
                    "line_value": 25.5,
                    "direction": "over",
                    "system_confidence": 80.0,
                    "system_fair_line": 26.0,
                    "system_suggestion": "over",
                    "system_hit_rate": 75.0
                }
            ]
        }
        response = client.post("/api/v1/parlays", json=parlay_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Parlay"
        assert len(data["legs"]) == 1
    
    def test_get_parlay_not_found(self):
        """Test getting a non-existent parlay"""
        response = client.get("/api/v1/parlays/99999")
        assert response.status_code == 404
    
    def test_list_parlays_with_filter(self):
        """Test listing parlays with result filter"""
        response = client.get("/api/v1/parlays?result=pending")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

