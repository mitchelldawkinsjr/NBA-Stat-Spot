from fastapi import APIRouter
from typing import Dict

router = APIRouter(prefix="/api/schedule", tags=["schedule"])

@router.get("/upcoming")
def upcoming(hours: int = 24) -> Dict:
    return {"games": []}
