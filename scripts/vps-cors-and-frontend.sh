#!/usr/bin/env bash
# Run ON THE VPS: set CORS (Option A) and ensure same-origin frontend (Option B).
# Option A: Ensure .env has ENV=production and CORS_ORIGINS for GitHub Pages.
# Option B: Rebuild frontend container (same-origin build) and restart stack.
#
# Usage on VPS: bash scripts/vps-cors-and-frontend.sh
# Or from local: ssh vps 'bash -s' < scripts/vps-cors-and-frontend.sh

set -e

# App dir: deploy workflow uses this path; fallback to setup script path
if [ -d "/opt/360ws/clients/docker-app/nba-stat-spot" ]; then
  APP_DIR="/opt/360ws/clients/docker-app/nba-stat-spot"
elif [ -d "/opt/nba-stat-spot" ]; then
  APP_DIR="/opt/nba-stat-spot"
else
  echo "App directory not found. Tried /opt/360ws/clients/docker-app/nba-stat-spot and /opt/nba-stat-spot"
  exit 1
fi

cd "$APP_DIR"
echo "Using app dir: $APP_DIR"

# --- Option A: CORS and ENV in .env ---
CORS_VALUE="https://mitchelldawkinsjr.github.io,https://nba-stat-spot.360web.cloud"
if [ ! -f .env ]; then
  echo "Creating .env with ENV=production and CORS_ORIGINS..."
  cat > .env << EOF
ENV=production
CORS_ORIGINS=$CORS_VALUE
EOF
else
  if grep -q "^CORS_ORIGINS=" .env 2>/dev/null; then
    sed -i.bak "s|^CORS_ORIGINS=.*|CORS_ORIGINS=$CORS_VALUE|" .env
    echo "Updated CORS_ORIGINS in .env"
  else
    echo "CORS_ORIGINS=$CORS_VALUE" >> .env
    echo "Appended CORS_ORIGINS to .env"
  fi
  if ! grep -q "^ENV=production" .env 2>/dev/null; then
    if grep -q "^ENV=" .env 2>/dev/null; then
      sed -i.bak "s|^ENV=.*|ENV=production|" .env
    else
      echo "ENV=production" >> .env
    fi
    echo "Set ENV=production in .env"
  fi
fi

# --- Option B: Rebuild frontend (same-origin) and restart ---
if command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  COMPOSE="docker compose"
fi

if $COMPOSE -f docker-compose.prod.yml config --services 2>/dev/null | grep -q "^frontend$"; then
  echo "Rebuilding frontend (same-origin) and restarting stack..."
  $COMPOSE -f docker-compose.prod.yml build --no-cache frontend
else
  echo "No frontend service in docker-compose; restarting stack to apply CORS..."
fi
$COMPOSE -f docker-compose.prod.yml up -d

echo "Waiting for backend..."
sleep 8
if curl -sf http://localhost:8007/healthz >/dev/null; then
  echo "Backend healthy."
else
  echo "Backend not ready yet; check: $COMPOSE -f docker-compose.prod.yml logs -f backend"
fi
echo "Done. CORS and same-origin frontend are configured."
