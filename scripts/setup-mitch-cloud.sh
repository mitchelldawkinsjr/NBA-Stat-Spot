#!/bin/bash
# Setup script for NBA-Stat-Spot on mitch-cloud VPS
# This script prepares the server environment following mitch-cloud playbook standards

set -e

echo "=== NBA-Stat-Spot mitch-cloud Setup ==="

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root or with sudo"
    exit 1
fi

# Verify Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed. Please install Docker first."
    echo "See: https://docs.docker.com/engine/install/"
    exit 1
fi

# Verify Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "ERROR: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✓ Docker and Docker Compose are installed"

# Create directory structure per playbook Section 4
echo "Creating directory structure..."

# Main application directory
mkdir -p /opt/360ws/clients/docker-app/nba-stat-spot

# Data directories for persistence
mkdir -p /data/databases/nba-stat-spot
mkdir -p /data/nba-stat-spot/logs

# Set proper ownership (adjust user as needed)
DEPLOY_USER="${SUDO_USER:-$USER}"
if [ -n "$DEPLOY_USER" ]; then
    chown -R $DEPLOY_USER:$DEPLOY_USER /opt/360ws/clients/docker-app/nba-stat-spot
    chown -R $DEPLOY_USER:$DEPLOY_USER /data/databases/nba-stat-spot
    chown -R $DEPLOY_USER:$DEPLOY_USER /data/nba-stat-spot
    echo "✓ Set ownership to $DEPLOY_USER"
fi

# Set proper permissions
chmod 755 /opt/360ws/clients/docker-app/nba-stat-spot
chmod 755 /data/databases/nba-stat-spot
chmod 755 /data/nba-stat-spot

echo "✓ Directory structure created"

# Ensure 360ws-network exists
echo "Checking 360ws-network..."
if ! docker network inspect 360ws-network &> /dev/null; then
    echo "Creating 360ws-network..."
    docker network create 360ws-network
    echo "✓ Created 360ws-network"
else
    echo "✓ 360ws-network already exists"
fi

# Create .env file template if it doesn't exist
ENV_FILE="/opt/360ws/clients/docker-app/nba-stat-spot/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Creating .env template..."
    cat > "$ENV_FILE" << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://nba_props_user:nba_props_password@postgres:5432/nba_props

# Environment
ENV=production
PORT=8007
# Ollama host (if using remote/local Ollama for LLM)
OLLAMA_HOST=http://localhost:11434

# CORS Configuration (comma-separated origins)
# Example: CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_ORIGINS=

# NBA API Configuration (optional)
API_NBA_KEY=
API_NBA_USE_RAPIDAPI=false
API_NBA_RATE_LIMIT_PER_MINUTE=10
API_NBA_RATE_LIMIT_PER_DAY=100

# ESPN API Rate Limits (optional overrides)
ESPN_RATE_LIMIT_PER_MINUTE=100
ESPN_RATE_LIMIT_PER_HOUR=1000
EOF
    if [ -n "$DEPLOY_USER" ]; then
        chown $DEPLOY_USER:$DEPLOY_USER "$ENV_FILE"
    fi
    chmod 600 "$ENV_FILE"
    echo "✓ Created .env template at $ENV_FILE"
    echo "⚠️  Please edit $ENV_FILE and set your configuration values"
else
    echo "✓ .env file already exists"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit $ENV_FILE and configure your environment variables"
echo "2. Clone or copy the NBA-Stat-Spot repository to /opt/360ws/clients/docker-app/nba-stat-spot"
echo "3. Run the deployment workflow or manually deploy with:"
echo "   cd /opt/360ws/clients/docker-app/nba-stat-spot"
echo "   docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo "For more information, see: docs/mitch-cloud-deployment.md"
