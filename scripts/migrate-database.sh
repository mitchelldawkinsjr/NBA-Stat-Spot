#!/bin/bash
# Database migration script for NBA-Stat-Spot
# Migrates from SQLite (if needed) to PostgreSQL and runs Alembic migrations

set -e

echo "=== NBA-Stat-Spot Database Migration ==="

# Check if running inside Docker container or on host
if [ -f /.dockerenv ]; then
    echo "Running inside Docker container"
    WORK_DIR="/app"
else
    echo "Running on host - using docker-compose"
    WORK_DIR="/opt/360ws/clients/docker-app/nba-stat-spot"
    
    if [ ! -d "$WORK_DIR" ]; then
        echo "ERROR: Application directory not found: $WORK_DIR"
        exit 1
    fi
    
    cd "$WORK_DIR"
    
    # Check if containers are running
    if ! docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        echo "Starting containers..."
        docker-compose -f docker-compose.prod.yml up -d postgres
        echo "Waiting for PostgreSQL to be ready..."
        sleep 5
    fi
fi

echo "Running Alembic migrations..."

if [ -f /.dockerenv ]; then
    # Inside container
    cd /app
    alembic upgrade head
else
    # On host, use docker-compose exec
    docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head || \
    docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
fi

echo "✓ Database migrations completed"

# Optional: Migrate data from SQLite if it exists
if [ -z "$SKIP_SQLITE_MIGRATION" ] && [ -f "$WORK_DIR/backend/nba_props.db" ]; then
    echo ""
    echo "SQLite database found. To migrate data from SQLite to PostgreSQL:"
    echo "1. Export data from SQLite"
    echo "2. Import into PostgreSQL"
    echo "3. This is a manual process - see docs/mitch-cloud-deployment.md for details"
    echo ""
    echo "To skip this message, set SKIP_SQLITE_MIGRATION=1"
fi

echo ""
echo "=== Migration Complete ==="
echo ""
echo "Database is ready. Verify with:"
echo "  docker-compose -f docker-compose.prod.yml exec backend python -c \"from app.database import engine; print('Connected:', engine.connect())\""
