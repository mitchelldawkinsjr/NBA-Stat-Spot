#!/usr/bin/env bash
# SSH into VPS and verify NBA-Stat-Spot is running.
# Uses "ssh vps" (expects Host vps in ~/.ssh/config).
#
# Usage:
#   ./scripts/ssh-vps-check.sh
#
# Options:
#   --fix    If app is not running, restart the stack on the VPS

set -e

# Use SSH host alias "vps" (from ~/.ssh/config); override with VPS_HOST if set
if [ -n "${VPS_HOST}" ]; then
  SSH_TARGET="${VPS_USER:-root}@${VPS_HOST}"
else
  SSH_TARGET="vps"
fi

FIX_MODE=false
for arg in "$@"; do
  case "$arg" in
    --fix) FIX_MODE=true ;;
  esac
done

SSH_OPTS=(-o ConnectTimeout=10 -o BatchMode=yes)
if [ -n "${SSH_KEY}" ]; then
  SSH_OPTS+=(-i "${SSH_KEY}")
fi

echo "Connecting to ${SSH_TARGET}..."
echo ""

# Run the status check on the VPS (pipe script via stdin)
ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "bash -s" < "$(dirname "$0")/check-vps-status.sh" || true

# If --fix, restart the stack on the VPS
if [ "$FIX_MODE" = true ]; then
  echo ""
  echo "Restarting app on VPS..."
  ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" 'set -e
    cd /opt/nba-stat-spot
    if command -v docker-compose >/dev/null 2>&1; then
      docker-compose -f docker-compose.prod.yml up -d
      sleep 5
      docker-compose -f docker-compose.prod.yml ps
    else
      docker compose -f docker-compose.prod.yml up -d
      sleep 5
      docker compose -f docker-compose.prod.yml ps
    fi'
  echo ""
  echo "Re-running status check..."
  ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "bash -s" < "$(dirname "$0")/check-vps-status.sh" || true
fi
