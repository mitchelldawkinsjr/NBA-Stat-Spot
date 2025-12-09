#!/bin/bash
# Validation script for mitch-cloud deployment configuration
# This script validates all deployment files and configuration

set -e

echo "=== NBA-Stat-Spot Deployment Validation ==="
echo ""

ERRORS=0
WARNINGS=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 exists"
        return 0
    else
        echo -e "${RED}✗${NC} $1 is missing"
        ((ERRORS++))
        return 1
    fi
}

check_file_content() {
    if grep -q "$2" "$1" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $1 contains: $2"
        return 0
    else
        echo -e "${RED}✗${NC} $1 missing: $2"
        ((ERRORS++))
        return 1
    fi
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

echo "1. Checking required files..."
check_file "docker-compose.prod.yml"
check_file ".github/workflows/deploy-mitch-cloud.yml"
check_file "Dockerfile.backend"
check_file "scripts/setup-mitch-cloud.sh"
check_file "scripts/migrate-database.sh"
check_file ".env.example"
check_file "docs/mitch-cloud-deployment.md"
echo ""

echo "2. Validating docker-compose.prod.yml..."
if check_file "docker-compose.prod.yml"; then
    check_file_content "docker-compose.prod.yml" "360ws-network"
    check_file_content "docker-compose.prod.yml" "com.360ws.app=nba-stat-spot"
    check_file_content "docker-compose.prod.yml" "postgres"
    check_file_content "docker-compose.prod.yml" "/data/databases/nba-stat-spot"
    check_file_content "docker-compose.prod.yml" "healthcheck"
fi
echo ""

echo "3. Validating Dockerfile.backend..."
if check_file "Dockerfile.backend"; then
    check_file_content "Dockerfile.backend" "supercronic"
    check_file_content "Dockerfile.backend" "crontab"
    check_file_content "Dockerfile.backend" "uvicorn"
fi
echo ""

echo "4. Validating deployment workflow..."
if check_file ".github/workflows/deploy-mitch-cloud.yml"; then
    check_file_content ".github/workflows/deploy-mitch-cloud.yml" "VPS_HOST"
    check_file_content ".github/workflows/deploy-mitch-cloud.yml" "VPS_SSH_KEY"
    check_file_content ".github/workflows/deploy-mitch-cloud.yml" "healthz"
    check_file_content ".github/workflows/deploy-mitch-cloud.yml" "alembic upgrade"
    check_file_content ".github/workflows/deploy-mitch-cloud.yml" "360ws-network"
fi
echo ""

echo "5. Validating backend configuration..."
if check_file "backend/app/core/config.py"; then
    if grep -q "FLY_APP_NAME" "backend/app/core/config.py"; then
        warn "backend/app/core/config.py still contains FLY_APP_NAME (should be removed)"
    else
        echo -e "${GREEN}✓${NC} Fly.io detection removed from config.py"
    fi
    check_file_content "backend/app/core/config.py" "ENV"
    check_file_content "backend/app/core/config.py" "CORS_ORIGINS"
fi
echo ""

echo "6. Validating scripts..."
if check_file "scripts/setup-mitch-cloud.sh"; then
    if [ -x "scripts/setup-mitch-cloud.sh" ]; then
        echo -e "${GREEN}✓${NC} setup-mitch-cloud.sh is executable"
    else
        warn "setup-mitch-cloud.sh is not executable (run: chmod +x scripts/setup-mitch-cloud.sh)"
    fi
fi

if check_file "scripts/migrate-database.sh"; then
    if [ -x "scripts/migrate-database.sh" ]; then
        echo -e "${GREEN}✓${NC} migrate-database.sh is executable"
    else
        warn "migrate-database.sh is not executable (run: chmod +x scripts/migrate-database.sh)"
    fi
fi
echo ""

echo "7. Checking for deprecated Fly.io references..."
if grep -q "nba-stat-spot-ai.fly.dev" ".github/workflows/deploy-pages.yml" 2>/dev/null; then
    warn "deploy-pages.yml still references Fly.io URL"
else
    echo -e "${GREEN}✓${NC} deploy-pages.yml updated to mitch-cloud URL"
fi

if ! grep -q "if: false" ".github/workflows/deploy-fly.yml" 2>/dev/null; then
    warn "deploy-fly.yml not disabled (should have 'if: false')"
else
    echo -e "${GREEN}✓${NC} deploy-fly.yml is disabled"
fi
echo ""

echo "8. Checking Alembic configuration..."
if [ -d "backend/alembic" ]; then
    echo -e "${GREEN}✓${NC} Alembic directory exists"
    if [ -f "backend/alembic.ini" ] || [ -f "backend/alembic/env.py" ]; then
        echo -e "${GREEN}✓${NC} Alembic configuration found"
    else
        warn "Alembic configuration may be missing (check backend/alembic.ini or backend/alembic/env.py)"
    fi
else
    warn "Alembic directory not found"
fi
echo ""

echo "=== Validation Summary ==="
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ Validation passed with $WARNINGS warning(s)${NC}"
    exit 0
else
    echo -e "${RED}✗ Validation failed with $ERRORS error(s) and $WARNINGS warning(s)${NC}"
    exit 1
fi
