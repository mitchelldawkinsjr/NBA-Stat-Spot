#!/bin/bash
# Set OLLAMA_HOST (and optional OLLAMA_MODEL) for NBA Stat Spot backend on the VPS.
# Run this on the VPS after SSH, from the app directory or with APP_DIR set.
#
# Usage:
#   cd /opt/360ws/clients/docker-app/nba-stat-spot && sudo -E bash scripts/set-ollama-env-vps.sh
#   # Or with custom Ollama URL (if not using default llm-runtime hostname):
#   OLLAMA_HOST=http://your-ollama-host:11434 bash scripts/set-ollama-env-vps.sh
#
# Default OLLAMA_HOST: http://ollama:11434 (Docker service name on 360ws-network).
# If your Ollama container is named llm-runtime, set: OLLAMA_HOST=http://llm-runtime:11434

set -e

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$APP_DIR"

OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2}"
OLLAMA_TIMEOUT="${OLLAMA_TIMEOUT:-90}"

ENV_FILE="${APP_DIR}/.env"

echo "=== Set Ollama env for NBA Stat Spot ==="
echo "App dir: $APP_DIR"
echo "OLLAMA_HOST=$OLLAMA_HOST"
echo "OLLAMA_MODEL=$OLLAMA_MODEL"
echo "OLLAMA_TIMEOUT=$OLLAMA_TIMEOUT"

# Remove existing OLLAMA_* lines if present (idempotent)
if [ -f "$ENV_FILE" ]; then
  sed -i.bak "/^OLLAMA_HOST=/d;/^OLLAMA_MODEL=/d;/^OLLAMA_TIMEOUT=/d" "$ENV_FILE" 2>/dev/null || true
  rm -f "${ENV_FILE}.bak"
fi

# Append new values
touch "$ENV_FILE"
echo "" >> "$ENV_FILE"
echo "# Ollama LLM (VPS / llm-runtime)" >> "$ENV_FILE"
echo "OLLAMA_HOST=$OLLAMA_HOST" >> "$ENV_FILE"
echo "OLLAMA_MODEL=$OLLAMA_MODEL" >> "$ENV_FILE"
echo "OLLAMA_TIMEOUT=$OLLAMA_TIMEOUT" >> "$ENV_FILE"

echo "✓ Updated $ENV_FILE"

# Restart backend so it picks up env
if docker compose -f docker-compose.prod.yml ps -q backend 2>/dev/null | head -1 | grep -q .; then
  echo "Restarting backend container..."
  docker compose -f docker-compose.prod.yml up -d backend
  echo "✓ Backend restarted"
else
  echo "Backend container not running. Start stack with: docker compose -f docker-compose.prod.yml up -d"
fi
