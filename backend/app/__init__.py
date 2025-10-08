from .api.players import router as players_router
from .api.teams import router as teams_router
from .api.schedule import router as schedule_router
from .api.props import router as props_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="NBA Stat Spot API", version="1.0")

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
