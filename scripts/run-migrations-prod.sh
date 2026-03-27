#!/usr/bin/env bash
# Run Alembic migrations on production (VPS).
# Usage: from repo root on the server (e.g. /opt/nba-stat-spot):
#   ./scripts/run-migrations-prod.sh
# Or with docker-compose:
#   docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
set -e
cd "$(dirname "$0")/.."
if command -v docker-compose &>/dev/null; then
  docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head || \
  docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
elif command -v docker &>/dev/null; then
  docker exec nba-stat-spot-backend alembic upgrade head
else
  echo "Need docker or docker-compose to run migrations on prod."
  exit 1
fi
