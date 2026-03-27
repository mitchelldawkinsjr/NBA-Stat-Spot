#!/usr/bin/env bash
# Pull a fresh prod PostgreSQL snapshot into local dev PostgreSQL.
# Run after: docker-compose -f docker-compose.dev.yml up -d
set -euo pipefail

DUMP_FILE="/tmp/nba_props_prod_$(date +%Y%m%d_%H%M%S).sql"
LOCAL_PG_CONTAINER="nba-stat-spot-postgres-dev"
PROD_PG_CONTAINER="nba-stat-spot-postgres"
PG_USER="nba_props_user"
PG_DB="nba_props"

dump_cmd="docker exec ${PROD_PG_CONTAINER} pg_dump -U ${PG_USER} --no-owner --no-privileges ${PG_DB}"

echo "Dumping prod database snapshot..."
if command -v vps >/dev/null 2>&1; then
  vps ssh -- "${dump_cmd}" > "${DUMP_FILE}"
else
  ssh -o ConnectTimeout=15 -o BatchMode=yes vps "${dump_cmd}" > "${DUMP_FILE}"
fi

echo "Waiting for local postgres..."
until docker exec "${LOCAL_PG_CONTAINER}" pg_isready -U "${PG_USER}" -q; do
  sleep 1
done

echo "Dropping and recreating local database..."
docker exec "${LOCAL_PG_CONTAINER}" psql -U "${PG_USER}" postgres \
  -c "DROP DATABASE IF EXISTS ${PG_DB};" \
  -c "CREATE DATABASE ${PG_DB};"

echo "Restoring snapshot to local postgres..."
docker exec -i "${LOCAL_PG_CONTAINER}" psql -U "${PG_USER}" "${PG_DB}" < "${DUMP_FILE}"

echo "Done. Local DB is now a copy of prod."
echo "Snapshot file: ${DUMP_FILE}"
