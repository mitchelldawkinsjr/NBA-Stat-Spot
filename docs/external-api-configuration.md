# External API Configuration

This document describes how to configure external API integrations (API-Sports.io and ESPN) with rate limiting and caching.

## Environment Variables

### API-Sports.io Basketball Configuration

API-Sports.io Basketball API can be accessed in two ways:

**Option 1: Direct API Key (Recommended)**
1. Sign up for an account at https://api-sports.io
2. Subscribe to the Basketball API
3. Get your API key from your dashboard

**Option 2: Via RapidAPI**
1. Sign up for a RapidAPI account at https://rapidapi.com
2. Subscribe to the API-Sports.io Basketball API
3. Get your API key from the RapidAPI dashboard
4. Set `API_NBA_USE_RAPIDAPI=true` environment variable

**Required:**
- `API_NBA_KEY` - Your API-Sports.io API key (direct or RapidAPI)

**Optional (with defaults):**
- `API_NBA_USE_RAPIDAPI` - Set to "true" if using RapidAPI (default: "false")
- `API_NBA_RATE_LIMIT_PER_MINUTE` - Requests per minute limit (default: 10)
- `API_NBA_RATE_LIMIT_PER_DAY` - Requests per day limit (default: 100 for free tier, 500+ for paid)

### ESPN Configuration

ESPN API is free and doesn't require an API key, but rate limits should be respected.

**Optional (with defaults):**
- `ESPN_RATE_LIMIT_PER_MINUTE` - Requests per minute limit (default: 100)
- `ESPN_RATE_LIMIT_PER_HOUR` - Requests per hour limit (default: 1000)

## Setting Environment Variables

### Local Development

Create a `.env` file in the project root:

```bash
# API-Sports.io (direct API key)
API_NBA_KEY=your-api-sports-key-here
API_NBA_USE_RAPIDAPI=false

# OR if using RapidAPI
# API_NBA_KEY=your-rapidapi-key-here
# API_NBA_USE_RAPIDAPI=true

# Optional rate limit overrides
API_NBA_RATE_LIMIT_PER_MINUTE=10
API_NBA_RATE_LIMIT_PER_DAY=100
ESPN_RATE_LIMIT_PER_MINUTE=100
ESPN_RATE_LIMIT_PER_HOUR=1000
```

### Fly.io Deployment

Set secrets using flyctl:

```bash
# Set API-Sports.io key (direct API key)
fly secrets set API_NBA_KEY="your-api-sports-key-here"
fly secrets set API_NBA_USE_RAPIDAPI="false"

# OR if using RapidAPI
# fly secrets set API_NBA_KEY="your-rapidapi-key-here"
# fly secrets set API_NBA_USE_RAPIDAPI="true"

# Optional: Override rate limits
fly secrets set API_NBA_RATE_LIMIT_PER_MINUTE="10"
fly secrets set API_NBA_RATE_LIMIT_PER_DAY="100"
fly secrets set ESPN_RATE_LIMIT_PER_MINUTE="100"
fly secrets set ESPN_RATE_LIMIT_PER_HOUR="1000"
```

View current secrets:
```bash
fly secrets list
```

## Rate Limiting

The system automatically tracks and enforces rate limits for all external API calls:

- **API-Sports.io**: 10 requests/minute, 100 requests/day (free tier), higher limits for paid tiers
- **ESPN**: 100 requests/minute, 1000 requests/hour (conservative limits)

Rate limits are tracked using:
- Redis (if `REDIS_URL` is set) - shared across all instances
- In-memory storage (fallback) - per-instance tracking

## Caching Strategy

All external API responses are cached to minimize API calls:

- **Live data** (scoreboard, play-by-play): 30 seconds TTL
- **Game summaries**: 5 minutes TTL
- **Static data** (teams, standings): 1 hour TTL
- **News/Transactions**: 15 minutes TTL

## Monitoring

Check rate limit status via admin endpoint:

```bash
GET /api/v1/admin/rate-limits
```

Returns current usage and limits for all providers.

## Fallback Strategy

The live game service uses a fallback chain:

1. **API-Sports.io** (primary) - Most reliable, requires API key
2. **ESPN** (fallback) - Free, no API key needed
3. **nba_api library** (final fallback) - Uses NBA.com directly

If API-Sports.io is unavailable or rate limited, the system automatically falls back to ESPN, then to nba_api.

## API-Sports.io Endpoints

The service uses the following API-Sports.io endpoints:
- Base URL: `https://v1.basketball.api-sports.io`
- Live games: `/games?live=all&league=12` (12 is NBA league ID)
- Game details: `/games?id={game_id}`
- Player stats: `/players/statistics?player={player_id}&league=12&season={season}`
- Team stats: `/teams/statistics?team={team_id}&league=12&season={season}`
- Team roster: `/players?team={team_id}&league=12`

