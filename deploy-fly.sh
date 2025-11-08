#!/bin/bash
# Fly.io Deployment Script
# Run this script to deploy the backend to Fly.io

set -e

FLYCTL="/Users/mitchelldawkins/.fly/bin/flyctl"

echo "🚀 Starting Fly.io deployment..."

# Check if flyctl is available
if [ ! -f "$FLYCTL" ]; then
    echo "❌ Fly CLI not found. Installing..."
    curl -L https://fly.io/install.sh | sh
    FLYCTL="$HOME/.fly/bin/flyctl"
fi

# Add to PATH for this session
export PATH="$HOME/.fly/bin:$PATH"

# Check if logged in
echo "🔐 Checking authentication..."
if ! $FLYCTL auth whoami &>/dev/null; then
    echo "⚠️  Not logged in. Please run: $FLYCTL auth login"
    echo "   This will open your browser to authenticate."
    exit 1
fi

echo "✅ Authenticated as: $($FLYCTL auth whoami)"

# Check if app exists
APP_NAME="nba-stat-spot-ai"
echo "📦 Checking app: $APP_NAME"

if $FLYCTL apps list | grep -q "$APP_NAME"; then
    echo "✅ App exists: $APP_NAME"
else
    echo "⚠️  App does not exist. Creating..."
    $FLYCTL apps create "$APP_NAME" --org personal
fi

# Set secrets
echo "🔑 Setting environment variables..."
$FLYCTL secrets set -a "$APP_NAME" \
    CORS_ORIGINS="https://mitchelldawkinsjr.github.io,https://mitchelldawkinsjr.github.io/NBA-Stat-Spot,http://localhost:5173" \
    DATABASE_URL="sqlite:///./nba_props.db"

# Deploy
echo "🚀 Deploying to Fly.io..."
$FLYCTL deploy -a "$APP_NAME"

echo "✅ Deployment complete!"
echo "🌐 Your app should be available at: https://$APP_NAME.fly.dev"
echo "🧪 Test it: curl https://$APP_NAME.fly.dev/healthz"

