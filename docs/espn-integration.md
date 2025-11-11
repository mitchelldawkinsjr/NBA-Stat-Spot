# ESPN Data Integration

**Purpose**: Documentation for the ESPN API integration that enhances predictions with real-time data.

**Use when**:
- Understanding how ESPN data improves predictions
- Configuring ESPN API access
- Troubleshooting ESPN data issues
- Extending ESPN integration features

---

## Overview

The NBA Stat Spot application integrates with ESPN's unofficial API endpoints to enhance prop bet predictions with real-time contextual data. This integration provides:

1. **Real Injury Status** - Live injury reports instead of placeholders
2. **Team Standings** - Conference rankings and playoff race context
3. **News & Transactions** - Sentiment analysis and transaction impact
4. **Live Game Context** - Real-time pace and game situation for in-game props
5. **Enhanced Matchups** - Actual head-to-head history using ESPN schedules

---

## Architecture

### Services

#### ESPN Mapping Service (`espn_mapping_service.py`)
Maps between NBA API identifiers and ESPN identifiers:
- NBA team IDs → ESPN team slugs (e.g., 1610612747 → "lal")
- NBA player IDs → ESPN player IDs (using fuzzy name matching)
- Caches mappings to reduce API calls

#### Context Collector (`context_collector.py`)
Enhanced to use ESPN data:
- `get_injury_status()` - Fetches real injury data from ESPN
- `get_team_performance()` - Uses ESPN standings for team context
- `get_matchup_history()` - Uses ESPN schedules for H2H analysis

#### Team Standings Service (`team_standings_service.py`)
Extracts team context from ESPN standings:
- Conference and division rankings
- Recent form (last 10 games win %)
- Playoff race pressure score
- Home/away records

#### News Context Service (`news_context_service.py`)
Extracts news and transaction context:
- Player/team news sentiment analysis
- Recent transaction detection
- Team momentum scoring

#### Live Game Context Service (`live_game_context_service.py`)
Extracts real-time game features:
- Current pace from play-by-play
- Player foul counts
- Game situation (close/blowout)
- Projected minutes remaining

---

## Feature Engineering Enhancements

### New Features Added

**Injury Features**:
- `injury_status_encoded`: 0.0-1.0 (probable=0.9, questionable=0.5, doubtful=0.2, out=0.0)
- `days_since_injury`: Days since injury occurred

**Standings Features**:
- `team_conference_rank`: Conference rank (1-15)
- `opponent_conference_rank`: Opponent conference rank
- `team_recent_form`: Last 10 games win percentage
- `playoff_race_pressure`: 0-1 score for playoff race pressure

**News Features**:
- `has_recent_news`: Boolean flag
- `news_sentiment`: -1 to 1 sentiment score
- `has_recent_transaction`: Boolean flag for recent trades/signings

**Live Game Features** (for in-game props):
- `live_pace`: Current points per 48 minutes
- `live_shooting_efficiency`: Current shooting percentage
- `foul_trouble_score`: 0-1 based on player fouls
- `projected_minutes_remaining`: Estimated minutes left
- `game_flow_score`: 0-1 (close vs blowout)

---

## API Endpoints

### ESPN Router (`/api/v1/espn`)

All ESPN endpoints are rate-limited (30 requests/minute) and cached appropriately:

- `GET /api/v1/espn/scoreboard` - Get today's games
- `GET /api/v1/espn/games/{game_id}/summary` - Game box score
- `GET /api/v1/espn/games/{game_id}/playbyplay` - Play-by-play data
- `GET /api/v1/espn/games/{game_id}/gamecast` - Advanced game data
- `GET /api/v1/espn/teams` - All NBA teams
- `GET /api/v1/espn/teams/{team_id}` - Team information
- `GET /api/v1/espn/teams/{team_id}/roster` - Team roster
- `GET /api/v1/espn/teams/{team_id}/schedule` - Team schedule
- `GET /api/v1/espn/players/{player_id}` - Player information
- `GET /api/v1/espn/standings` - League standings
- `GET /api/v1/espn/news` - NBA news feed
- `GET /api/v1/espn/injuries` - Injury reports
- `GET /api/v1/espn/transactions` - Recent transactions

---

## Caching Strategy

ESPN data is cached with appropriate TTLs:
- **Injuries**: 15 minutes (live data)
- **News**: 15 minutes (frequently updated)
- **Standings**: 1 hour (changes daily)
- **Team Info**: 1 hour (static data)
- **Live Game Data**: 30 seconds (real-time)

---

## Error Handling

All ESPN integrations include graceful fallbacks:
- If ESPN API fails, falls back to NBA API data
- Missing ESPN data doesn't break predictions
- Errors are logged but don't interrupt service
- Cached data used when API unavailable

---

## Database Schema

### PlayerContext Model Updates

New fields added to `player_contexts` table:
- `espn_team_slug`: ESPN team identifier
- `espn_player_id`: ESPN player identifier
- `injury_date`: Date of injury
- `team_conference_rank`: Conference ranking
- `opponent_conference_rank`: Opponent conference ranking
- `team_recent_form`: Recent win percentage
- `playoff_race_pressure`: Playoff pressure score
- `news_sentiment`: News sentiment score
- `has_recent_transaction`: Transaction flag

**Migration**: Run Alembic migration `XXXX_add_espn_context_fields.py` to add these columns.

---

## Configuration

No additional configuration required. ESPN API endpoints are public (unofficial) and don't require API keys.

Rate limiting is handled automatically via `external_api_rate_limiter.py`.

---

## Usage Examples

### Getting Injury Status
```python
from app.services.context_collector import ContextCollector
from datetime import date

injury_info = ContextCollector.get_injury_status(
    player_id=203076,  # LeBron James
    game_date=date.today()
)
# Returns: {
#     "is_injured": False,
#     "injury_status": None,
#     "injury_description": None,
#     "injury_date": None
# }
```

### Getting Team Standings Context
```python
from app.services.team_standings_service import get_team_standings_service

standings_service = get_team_standings_service()
context = standings_service.get_team_standings_context(team_id=1610612747)
# Returns conference rank, recent form, playoff pressure, etc.
```

### Getting News Context
```python
from app.services.news_context_service import get_news_context_service

news_service = get_news_context_service()
player_news = news_service.get_player_news_context(player_id=203076, days=7)
# Returns news sentiment, recent news count, etc.
```

---

## Troubleshooting

### ESPN Data Not Available
- Check ESPN API endpoint availability
- Verify network connectivity
- Check rate limit status
- Review error logs for specific failures

### Mapping Issues
- Player/team not found: Check name matching logic
- Verify ESPN team slugs are correct
- Review mapping service cache

### Performance Issues
- Check cache hit rates
- Review rate limiting configuration
- Monitor API response times

---

## Future Enhancements

Potential improvements:
- Advanced gamecast metrics (shot charts, advanced stats)
- Historical injury pattern analysis
- Team chemistry scoring from news
- Real-time betting line integration
- Player usage rate from live data

