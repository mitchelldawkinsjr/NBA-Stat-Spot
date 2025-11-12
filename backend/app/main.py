from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from .database import Base, engine
from .models import user_bets, user_parlays, player_context, market_context, ai_features, app_settings  # Import models so tables are created
from .services.cache_service import CacheEntry  # Import cache model so table is created
from .routers.props_v1 import router as props_v1_router
from .routers.players_v1 import router as players_v1_router
from .routers.teams_v1 import router as teams_v1_router
from .routers.games_v1 import router as games_v1_router
from .routers.admin_v1 import router as admin_v1_router
from .routers.bets_v1 import router as bets_v1_router
from .routers.parlays_v1 import router as parlays_v1_router
from .routers import over_under_v1
from .routers import espn_v1
from .routers import games_enhanced_v1


app = FastAPI(
    title="NBA Stat Spot API",
    version="1.0.0",
    description="""
    ## NBA Stat Spot API - Comprehensive Player Prop Bet Analysis Platform
    
    A powerful REST API for analyzing NBA player prop bets with AI-enhanced predictions, 
    real-time game data, and comprehensive statistical analysis.
    
    ### Key Features
    
    - **Player Prop Analysis**: Get AI-powered suggestions for player prop bets (points, rebounds, assists, 3PM, PRA)
    - **Real-time Game Data**: Access live scores, game summaries, and play-by-play data via ESPN integration
    - **Statistical Analysis**: Historical performance tracking, hit rate calculations, and trend analysis
    - **Bet Tracking**: Track your bets and system accuracy over time
    - **Parlay Builder**: Create and manage multi-leg parlay bets
    - **Team & Player Data**: Comprehensive NBA team and player information
    
    ### Rate Limiting
    
    Most endpoints are rate-limited to ensure fair usage:
    - Player/Team endpoints: 60 requests/minute
    - Prop analysis endpoints: 30 requests/minute
    - ESPN endpoints: 30 requests/minute
    - Admin endpoints: Varies by operation
    
    ### Authentication
    
    Currently, the API does not require authentication. Rate limiting is applied per IP address.
    
    ### Data Sources
    
    - **NBA Data**: Official NBA statistics via nba_api
    - **ESPN Data**: Real-time game data, injuries, standings, and news
    - **AI/ML Models**: Custom machine learning models for prop predictions
    
    ### Getting Started
    
    1. Start with the `/api/v1/props/daily` endpoint to see today's top prop suggestions
    2. Use `/api/v1/players/search` to find players
    3. Use `/api/v1/props/player` to get detailed prop analysis for a specific player
    4. Track your bets using the `/api/v1/bets` endpoints
    
    ### Support
    
    For issues or questions, please refer to the project documentation or open an issue on GitHub.
    """,
    contact={
        "name": "NBA Stat Spot",
        "url": "https://github.com/mitchelldawkinsjr/NBA-Stat-Spot",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {
            "name": "props_v1",
            "description": "Player prop bet analysis and suggestions. Get AI-powered recommendations for player prop bets with confidence scores, hit rates, and detailed rationales.",
        },
        {
            "name": "players_v1",
            "description": "Player information, statistics, and search. Access player profiles, game logs, trends, and stat leaders.",
        },
        {
            "name": "teams_v1",
            "description": "Team information and rosters. Get team details, player rosters, and team-specific data.",
        },
        {
            "name": "games_v1",
            "description": "Game schedules and basic game information. Get today's games, upcoming schedules, and game details.",
        },
        {
            "name": "games_enhanced_v1",
            "description": "Enhanced game data with live scores, box scores, and detailed statistics.",
        },
        {
            "name": "espn_v1",
            "description": "ESPN integration endpoints. Access real-time scoreboards, game summaries, play-by-play, team rosters, standings, injuries, and news.",
        },
        {
            "name": "over_under_v1",
            "description": "Over/under game analysis. Analyze game totals with AI-powered predictions and live game tracking.",
        },
        {
            "name": "bets_v1",
            "description": "Bet tracking and management. Record bets, track results, and analyze system accuracy.",
        },
        {
            "name": "parlays_v1",
            "description": "Parlay bet builder and management. Create multi-leg parlays and track their performance.",
        },
        {
            "name": "admin_v1",
            "description": "Administrative endpoints for data synchronization, cache management, and system configuration. Requires appropriate permissions.",
        },
    ],
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Local development server",
        },
        {
            "url": "https://nba-stat-spot-ai.fly.dev",
            "description": "Production server (Fly.io)",
        },
    ],
)
Base.metadata.create_all(bind=engine)

# Error handling
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from .core.error_handler import error_handler, APIError

app.add_exception_handler(APIError, error_handler)
app.add_exception_handler(RequestValidationError, error_handler)
app.add_exception_handler(SQLAlchemyError, error_handler)
app.add_exception_handler(Exception, error_handler)

# Rate limiting
from slowapi.errors import RateLimitExceeded
from .core.rate_limiter import limiter, rate_limit_handler

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# CORS configuration
from .core.config import get_cors_origins
import structlog

logger = structlog.get_logger()
allowed_origins = get_cors_origins()

if allowed_origins == ["*"]:
    logger.info("CORS: Allowing all origins (development mode)")
elif not allowed_origins:
    logger.warning("CORS: No origins configured - API may be inaccessible. Set CORS_ORIGINS environment variable.")
    # Fallback to all origins if empty (shouldn't happen in production)
    allowed_origins = ["*"]
else:
    logger.info("CORS: Allowing configured origins", origins=allowed_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

@app.get(
    "/healthz",
    tags=["health"],
    summary="Health check endpoint",
    description="Returns the health status of the API. Use this to verify the API is running and responsive.",
    response_description="API health status",
)
def healthz():
    """
    Health check endpoint for monitoring API availability.
    
    Returns:
        dict: Status object with "ok" if the API is healthy
    """
    return {"status": "ok"}

# Modern v1 routes
app.include_router(props_v1_router)
app.include_router(players_v1_router)
app.include_router(teams_v1_router)
app.include_router(games_v1_router)
app.include_router(admin_v1_router)
app.include_router(bets_v1_router)
app.include_router(parlays_v1_router)
app.include_router(over_under_v1.router)
app.include_router(espn_v1.router)
app.include_router(games_enhanced_v1.router)
