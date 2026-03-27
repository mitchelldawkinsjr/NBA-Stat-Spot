"""
Scheduled odds sync — import `run_odds_sync` from cron or a worker.

Cron example (every 15 minutes; adjust for Odds API quota):
  */15 * * * * cd /path/to/backend && THE_ODDS_API_KEY=... python -c "from app.tasks.odds_updater import run_odds_sync; print(run_odds_sync())"

Or POST /api/v1/admin/refresh/odds-sync (admin) after deployment.
"""
from ..database import SessionLocal
from ..services.odds_service import sync_nba_odds


def run_odds_sync() -> dict:
    db = SessionLocal()
    try:
        return sync_nba_odds(db)
    finally:
        db.close()
