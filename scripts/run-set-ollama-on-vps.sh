#!/bin/bash
# Run set-ollama-env-vps.sh on the VPS via SSH.
# Set VPS_HOST and VPS_USER (and optionally OLLAMA_HOST) then run this from your machine.
#
# Example:
#   export VPS_HOST=your-vps-ip-or-domain
#   export VPS_USER=root
#   export OLLAMA_HOST=http://llm-runtime:11434   # optional; default http://ollama:11434
#   bash scripts/run-set-ollama-on-vps.sh

set -e

if [ -z "$VPS_HOST" ] || [ -z "$VPS_USER" ]; then
  echo "Set VPS_HOST and VPS_USER (and optionally OLLAMA_HOST, OLLAMA_MODEL) then run this script."
  echo "Example: VPS_HOST=1.2.3.4 VPS_USER=root bash scripts/run-set-ollama-on-vps.sh"
  exit 1
fi

APP_DIR="/opt/360ws/clients/docker-app/nba-stat-spot"
# Only pass vars that are set (so script defaults apply otherwise)
ENV_EXPORTS=""
[ -n "$OLLAMA_HOST" ] && ENV_EXPORTS="$ENV_EXPORTS OLLAMA_HOST=$OLLAMA_HOST"
[ -n "$OLLAMA_MODEL" ] && ENV_EXPORTS="$ENV_EXPORTS OLLAMA_MODEL=$OLLAMA_MODEL"
[ -n "$OLLAMA_TIMEOUT" ] && ENV_EXPORTS="$ENV_EXPORTS OLLAMA_TIMEOUT=$OLLAMA_TIMEOUT"

echo "Running set-ollama-env-vps.sh on $VPS_USER@$VPS_HOST..."
ssh "$VPS_USER@$VPS_HOST" "cd $APP_DIR && $ENV_EXPORTS bash scripts/set-ollama-env-vps.sh"
