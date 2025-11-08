from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from .models import user_bets, user_parlays, player_context, market_context, ai_features, app_settings  # Import models so tables are created
from .routers.props_v1 import router as props_v1_router
from .routers.players_v1 import router as players_v1_router
from .routers.teams_v1 import router as teams_v1_router
from .routers.games_v1 import router as games_v1_router
from .routers.admin_v1 import router as admin_v1_router
from .routers.bets_v1 import router as bets_v1_router
from .routers.parlays_v1 import router as parlays_v1_router

# Legacy API routers - deprecated, use /api/v1/* routes instead
# Keeping for backward compatibility but should be removed in future version
from .api.players import router as players_router
from .api.teams import router as teams_router
from .api.schedule import router as schedule_router
from .api.props import router as props_router

app = FastAPI(title="NBA Stat Spot API", version="1.0")
Base.metadata.create_all(bind=engine)

# CORS configuration - open in development, restricted in production
import os

# Check if we're in development mode
# Fly.io sets FLY_APP_NAME automatically, so if it's not set, we're likely in local dev
is_fly_io = os.getenv("FLY_APP_NAME") is not None
env_mode = os.getenv("ENV", os.getenv("ENVIRONMENT", "")).lower()

# If on Fly.io, always use production mode unless explicitly set to dev
# Otherwise, default to development for local dev
if is_fly_io:
    is_development = env_mode in ["development", "dev", "local"]
else:
    # Local dev - default to development unless explicitly set to production
    is_development = env_mode not in ["production", "prod"]

if is_development:
    # In development, allow all origins for easy local testing
    allowed_origins = ["*"]
    import structlog
    logger = structlog.get_logger()
    logger.info("CORS: Allowing all origins (development mode)")
else:
    # In production, use configured origins or default to GitHub Pages
    cors_origins_env = os.getenv("CORS_ORIGINS", "")
    if cors_origins_env:
        allowed_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
    else:
        # Default to GitHub Pages if no CORS_ORIGINS is set
        allowed_origins = ["https://mitchelldawkinsjr.github.io"]
    
    # Always ensure GitHub Pages URLs are included (both root and with repo path)
    github_pages_urls = [
        "https://mitchelldawkinsjr.github.io",
        "https://mitchelldawkinsjr.github.io/NBA-Stat-Spot"
    ]
    for url in github_pages_urls:
        if url not in allowed_origins:
            allowed_origins.append(url)
    
    if not allowed_origins:
        # Fallback to all origins if somehow empty (shouldn't happen)
        allowed_origins = ["*"]
        import structlog
        logger = structlog.get_logger()
        logger.warning("CORS: No origins configured, allowing all (fallback)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# Legacy routes - deprecated, use /api/v1/* instead
app.include_router(players_router)
app.include_router(teams_router)
app.include_router(schedule_router)
app.include_router(props_router)
# Modern v1 routes
app.include_router(props_v1_router)
app.include_router(players_v1_router)
app.include_router(teams_v1_router)
app.include_router(games_v1_router)
app.include_router(admin_v1_router)
app.include_router(bets_v1_router)
app.include_router(parlays_v1_router)
