# Backend Tests

This directory contains the test suite for the NBA Stat Spot backend.

## Running Tests

### Run all tests
```bash
cd backend
pytest tests/ -v
```

### Run with coverage
```bash
pytest tests/ -v --cov=app --cov-report=html --cov-report=term
```

### Run specific test file
```bash
pytest tests/test_routers.py -v
```

### Run specific test
```bash
pytest tests/test_routers.py::TestHealthEndpoint::test_healthz -v
```

## Test Structure

- `test_api_endpoints.py` - Basic health check tests
- `test_nba_api_service.py` - Tests for NBA API service
- `test_routers.py` - Tests for API routers (players, games, props, teams)
- `test_parlays.py` - Tests for parlay functionality

## Coverage

Coverage reports are generated automatically in GitHub Actions and uploaded as artifacts.

To view coverage locally:
1. Run tests with coverage: `pytest tests/ --cov=app --cov-report=html`
2. Open `htmlcov/index.html` in your browser
