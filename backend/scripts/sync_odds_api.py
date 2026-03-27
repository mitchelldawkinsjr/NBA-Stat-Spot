#!/usr/bin/env python3
"""CLI: sync NBA odds from The Odds API into prop_bet_lines.

Usage (from backend/):
  THE_ODDS_API_KEY=... DATABASE_URL=... python scripts/sync_odds_api.py

Or rely on .env in app root.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal
from app.services.odds_service import sync_nba_odds


def main():
    db = SessionLocal()
    try:
        out = sync_nba_odds(db)
        print(out)
        if not out.get("ok"):
            sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
