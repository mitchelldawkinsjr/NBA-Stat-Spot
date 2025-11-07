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

from .api.players import router as players_router
from .api.teams import router as teams_router
from .api.schedule import router as schedule_router
from .api.props import router as props_router

app = FastAPI(title="NBA Stat Spot API", version="1.0")
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

app.include_router(players_router)
app.include_router(teams_router)
app.include_router(schedule_router)
app.include_router(props_router)
app.include_router(props_v1_router)
app.include_router(players_v1_router)
app.include_router(teams_v1_router)
app.include_router(games_v1_router)
app.include_router(admin_v1_router)
app.include_router(bets_v1_router)
app.include_router(parlays_v1_router)
