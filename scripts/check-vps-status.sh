#!/bin/bash
# VPS Status Check Script
# Run this on your VPS to verify NBA-Stat-Spot is running correctly

set -e

echo "=== NBA-Stat-Spot VPS Status Check ==="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

APP_DIR="/opt/nba-stat-spot"

# Check if app directory exists
if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}✗${NC} App directory not found: $APP_DIR"
    echo "   Run: sudo bash scripts/setup-mitch-cloud.sh"
    exit 1
else
    echo -e "${GREEN}✓${NC} App directory exists: $APP_DIR"
fi

cd "$APP_DIR"

# Check Docker Compose file
if [ ! -f "docker-compose.prod.yml" ]; then
    echo -e "${RED}✗${NC} docker-compose.prod.yml not found"
    exit 1
else
    echo -e "${GREEN}✓${NC} docker-compose.prod.yml found"
fi

# Check containers
echo ""
echo "Checking containers..."
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "Container Status:"
BACKEND_STATUS=$(docker-compose -f docker-compose.prod.yml ps backend | grep -q "Up" && echo "running" || echo "stopped")
POSTGRES_STATUS=$(docker-compose -f docker-compose.prod.yml ps postgres | grep -q "Up" && echo "running" || echo "stopped")
REDIS_STATUS=$(docker-compose -f docker-compose.prod.yml ps redis | grep -q "Up" && echo "running" || echo "stopped")

if [ "$BACKEND_STATUS" = "running" ]; then
    echo -e "${GREEN}✓${NC} Backend container: running"
else
    echo -e "${RED}✗${NC} Backend container: stopped"
fi

if [ "$POSTGRES_STATUS" = "running" ]; then
    echo -e "${GREEN}✓${NC} PostgreSQL container: running"
else
    echo -e "${RED}✗${NC} PostgreSQL container: stopped"
fi

if [ "$REDIS_STATUS" = "running" ]; then
    echo -e "${GREEN}✓${NC} Redis container: running"
else
    echo -e "${RED}✗${NC} Redis container: stopped"
fi

# Health checks
echo ""
echo "Health Checks:"

# Backend health
if curl -f http://localhost:8007/healthz > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend health endpoint: OK"
    curl -s http://localhost:8007/healthz | head -c 100
    echo ""
else
    echo -e "${RED}✗${NC} Backend health endpoint: FAILED"
fi

# PostgreSQL connection
if docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U nba_props_user -d nba_props > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} PostgreSQL: accessible"
else
    echo -e "${RED}✗${NC} PostgreSQL: not accessible"
fi

# Redis connection
if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Redis: accessible"
else
    echo -e "${RED}✗${NC} Redis: not accessible"
fi

# Check network
echo ""
echo "Network Check:"
if docker network inspect 360ws-network > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} 360ws-network exists"
    CONTAINERS_ON_NETWORK=$(docker network inspect 360ws-network --format '{{range .Containers}}{{.Name}} {{end}}' | grep -c "nba-stat-spot" || echo "0")
    if [ "$CONTAINERS_ON_NETWORK" -ge 3 ]; then
        echo -e "${GREEN}✓${NC} All containers on network"
    else
        echo -e "${YELLOW}⚠${NC} Some containers may not be on network"
    fi
else
    echo -e "${RED}✗${NC} 360ws-network not found"
fi

# Check volumes
echo ""
echo "Volume Check:"
if [ -d "/data/databases/nba-stat-spot" ]; then
    echo -e "${GREEN}✓${NC} Database volume exists"
else
    echo -e "${YELLOW}⚠${NC} Database volume not found"
fi

if [ -d "/data/nba-stat-spot/logs" ]; then
    echo -e "${GREEN}✓${NC} Logs volume exists"
else
    echo -e "${YELLOW}⚠${NC} Logs volume not found"
fi

if [ -d "/data/nba-stat-spot/redis" ]; then
    echo -e "${GREEN}✓${NC} Redis volume exists"
else
    echo -e "${YELLOW}⚠${NC} Redis volume not found"
fi

# Check .env file
echo ""
echo "Configuration Check:"
if [ -f "$APP_DIR/.env" ]; then
    echo -e "${GREEN}✓${NC} .env file exists"
    if grep -q "CORS_ORIGINS" "$APP_DIR/.env"; then
        CORS_SET=$(grep "CORS_ORIGINS" "$APP_DIR/.env" | grep -v "^#" | grep -v "^$" | cut -d'=' -f2)
        if [ -n "$CORS_SET" ]; then
            echo -e "${GREEN}✓${NC} CORS_ORIGINS is configured"
        else
            echo -e "${YELLOW}⚠${NC} CORS_ORIGINS is empty (may cause CORS errors)"
        fi
    fi
else
    echo -e "${YELLOW}⚠${NC} .env file not found (using defaults from docker-compose)"
fi

# Recent logs
echo ""
echo "Recent Backend Logs (last 5 lines):"
docker-compose -f docker-compose.prod.yml logs --tail=5 backend 2>/dev/null || echo "No logs available"

echo ""
echo "=== Status Check Complete ==="
