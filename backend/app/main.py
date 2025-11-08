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

# CORS configuration - restrict origins in production
import os
cors_origins_env = os.getenv("CORS_ORIGINS", "*")
allowed_origins = cors_origins_env.split(",") if cors_origins_env else ["*"]

# Always allow GitHub Pages frontend
github_pages_url = "https://mitchelldawkinsjr.github.io"
if "*" not in allowed_origins and github_pages_url not in allowed_origins:
    allowed_origins.append(github_pages_url)

if allowed_origins == ["*"] or "*" in allowed_origins:
    # In production, you should set CORS_ORIGINS to specific domains
    import structlog
    logger = structlog.get_logger()
    logger.warning("CORS allows all origins - consider restricting in production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
