from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/admin", tags=["admin_v1"])

@router.post("/sync/players")
def sync_players():
    return {"status": "queued"}

@router.post("/sync/stats")
def sync_stats():
    return {"status": "queued"}

@router.post("/generate-props")
def generate_props(date: str | None = None):
    return {"status": "ok"}

@router.get("/health")
def health():
    return {"status": "ok"}
